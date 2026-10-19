"""Anthropic Messages API ↔ Azure OpenAI chat completions 변환 프록시.

Claude Code CLI(Agent SDK)는 Anthropic 형식으로만 요청한다. LLM_PROVIDER=azure_openai
에서는 CLI 가 백엔드 `/anthropic` 경로로 요청하고, 이 모듈이 Azure OpenAI 호환
게이트웨이(`/openai/deployments/{deployment}/chat/completions`)로 변환해 전달한다.

- 텍스트·이미지·tool_use·tool_result 를 양방향 변환하고, 스트리밍은 Anthropic SSE
  이벤트(message_start … message_stop)로 다시 만든다.
- thinking·cache_control·metadata 등 대응 개념이 없는 필드는 버린다.
- 요청·응답 본문과 key 는 로그에 남기지 않는다.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core import config
from services.service_logging import logged_service_operation

_STOP_REASONS = {"stop": "end_turn", "tool_calls": "tool_use", "function_call": "tool_use",
                 "length": "max_tokens", "content_filter": "end_turn"}
_TIMEOUT = httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0)


class ProxyError(Exception):
    """게이트웨이 호출 실패. 본문·key 없이 상태 코드와 안전한 메시지만 담는다."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def anthropic_error(message: str, error_type: str = "api_error") -> dict[str, Any]:
    return {"type": "error", "error": {"type": error_type, "message": message}}


def resolve_deployment(model: str | None) -> str:
    """Claude 이름(CLI 기본·보조 모델)은 기본 deployment 로 바꾸고, 그 외 이름은 그대로 쓴다."""

    if model and not model.lower().startswith("claude"):
        return model
    if not config.AZURE_OPENAI_DEPLOYMENT:
        raise ProxyError(500, "AZURE_OPENAI_DEPLOYMENT 가 설정되지 않았습니다.")
    return config.AZURE_OPENAI_DEPLOYMENT


# ---- 요청 변환 ------------------------------------------------------------


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _image_part(block: dict) -> dict | None:
    source = block.get("source") or {}
    if source.get("type") == "base64":
        return {"type": "image_url", "image_url": {"url": f"data:{source.get('media_type')};base64,{source.get('data')}"}}
    if source.get("type") == "url":
        return {"type": "image_url", "image_url": {"url": source.get("url")}}
    return None


def _user_messages(content: Any) -> list[dict]:
    """user 메시지 하나를 tool 메시지(먼저)와 일반 user 메시지로 나눈다."""

    if isinstance(content, str):
        return [{"role": "user", "content": content}]
    tool_messages: list[dict] = []
    parts: list[dict] = []
    for block in content or []:
        kind = block.get("type")
        if kind == "tool_result":
            text = _text_of(block.get("content"))
            if block.get("is_error"):
                text = f"[tool error] {text}"
            tool_messages.append({"role": "tool", "tool_call_id": block.get("tool_use_id"), "content": text or "(empty)"})
        elif kind == "text" and block.get("text"):
            parts.append({"type": "text", "text": block["text"]})
        elif kind == "image":
            image = _image_part(block)
            if image:
                parts.append(image)
    messages = tool_messages
    if parts:
        only_text = all(p["type"] == "text" for p in parts)
        messages.append({"role": "user", "content": "\n".join(p["text"] for p in parts) if only_text else parts})
    return messages


def _assistant_message(content: Any) -> dict | None:
    if isinstance(content, str):
        return {"role": "assistant", "content": content}
    texts: list[str] = []
    calls: list[dict] = []
    for block in content or []:
        kind = block.get("type")
        if kind == "text" and block.get("text"):
            texts.append(block["text"])
        elif kind == "tool_use":
            calls.append({"id": block.get("id"), "type": "function",
                          "function": {"name": block.get("name"), "arguments": json.dumps(block.get("input") or {}, ensure_ascii=False)}})
        # thinking / redacted_thinking 블록은 대응 개념이 없어 버린다.
    if not texts and not calls:
        return None
    message: dict[str, Any] = {"role": "assistant", "content": "\n".join(texts) or None}
    if calls:
        message["tool_calls"] = calls
    return message


def _tool_choice(choice: Any) -> Any:
    if not isinstance(choice, dict):
        return None
    kind = choice.get("type")
    if kind == "any":
        return "required"
    if kind == "tool":
        return {"type": "function", "function": {"name": choice.get("name")}}
    if kind in {"auto", "none"}:
        return kind
    return None


def to_openai_request(body: dict) -> dict[str, Any]:
    """Anthropic Messages 요청을 chat completions 요청 본문으로 바꾼다(deployment 는 URL 에)."""

    messages: list[dict] = []
    system = _text_of(body.get("system"))
    if system:
        messages.append({"role": "system", "content": system})
    for message in body.get("messages") or []:
        if message.get("role") == "user":
            messages.extend(_user_messages(message.get("content")))
        elif message.get("role") == "assistant":
            converted = _assistant_message(message.get("content"))
            if converted:
                messages.append(converted)

    request: dict[str, Any] = {"messages": messages}
    tools = [
        {"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                          "parameters": t.get("input_schema") or {"type": "object", "properties": {}}}}
        for t in body.get("tools") or [] if t.get("name") and "input_schema" in t
    ]
    if tools:
        request["tools"] = tools
        choice = _tool_choice(body.get("tool_choice"))
        if choice is not None:
            request["tool_choice"] = choice
    max_tokens = body.get("max_tokens")
    if max_tokens:
        cap = config.AZURE_OPENAI_MAX_TOKENS
        request["max_completion_tokens"] = min(max_tokens, cap) if cap else max_tokens
    # temperature·top_p·stop 은 reasoning 계열(gpt-5 등)이 거부할 수 있어 전달하지 않는다.
    return request


# ---- 응답 변환 ------------------------------------------------------------


def _usage(usage: dict | None) -> dict[str, int]:
    usage = usage or {}
    return {"input_tokens": int(usage.get("prompt_tokens") or 0), "output_tokens": int(usage.get("completion_tokens") or 0)}


def _parse_arguments(raw: str | None) -> dict:
    try:
        parsed = json.loads(raw or "{}")
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def to_anthropic_message(response: dict, model: str) -> dict[str, Any]:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content: list[dict] = []
    if message.get("content"):
        content.append({"type": "text", "text": message["content"]})
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        content.append({"type": "tool_use", "id": call.get("id") or f"toolu_{uuid.uuid4().hex[:24]}",
                        "name": function.get("name"), "input": _parse_arguments(function.get("arguments"))})
    return {
        "id": f"msg_{response.get('id') or uuid.uuid4().hex}", "type": "message", "role": "assistant",
        "model": model, "content": content,
        "stop_reason": _STOP_REASONS.get(choice.get("finish_reason"), "end_turn"), "stop_sequence": None,
        "usage": _usage(response.get("usage")),
    }


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class StreamTranslator:
    """chat completions 스트림 chunk 를 Anthropic SSE 이벤트 문자열로 바꾼다."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.index = -1
        self.open_kind: str | None = None  # "text" | "tool"
        self.tool_blocks: dict[int, int] = {}  # openai tool index -> anthropic block index
        self.finish_reason: str | None = None
        self.usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
        self.started = False

    def _start(self) -> list[str]:
        if self.started:
            return []
        self.started = True
        message = {"id": f"msg_{uuid.uuid4().hex}", "type": "message", "role": "assistant", "model": self.model,
                   "content": [], "stop_reason": None, "stop_sequence": None,
                   "usage": {"input_tokens": 0, "output_tokens": 0}}
        return [sse("message_start", {"type": "message_start", "message": message})]

    def _close(self) -> list[str]:
        if self.open_kind is None:
            return []
        self.open_kind = None
        return [sse("content_block_stop", {"type": "content_block_stop", "index": self.index})]

    def feed(self, chunk: dict) -> list[str]:
        events = self._start()
        if chunk.get("usage"):
            self.usage = _usage(chunk["usage"])
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            text = delta.get("content")
            if text:
                if self.open_kind != "text":
                    events += self._close()
                    self.index += 1
                    self.open_kind = "text"
                    events.append(sse("content_block_start", {"type": "content_block_start", "index": self.index,
                                                              "content_block": {"type": "text", "text": ""}}))
                events.append(sse("content_block_delta", {"type": "content_block_delta", "index": self.index,
                                                          "delta": {"type": "text_delta", "text": text}}))
            for call in delta.get("tool_calls") or []:
                position = call.get("index", 0)
                function = call.get("function") or {}
                if position not in self.tool_blocks:
                    events += self._close()
                    self.index += 1
                    self.tool_blocks[position] = self.index
                    self.open_kind = "tool"
                    events.append(sse("content_block_start", {
                        "type": "content_block_start", "index": self.index,
                        "content_block": {"type": "tool_use", "id": call.get("id") or f"toolu_{uuid.uuid4().hex[:24]}",
                                          "name": function.get("name"), "input": {}}}))
                if function.get("arguments"):
                    events.append(sse("content_block_delta", {
                        "type": "content_block_delta", "index": self.tool_blocks[position],
                        "delta": {"type": "input_json_delta", "partial_json": function["arguments"]}}))
            if choice.get("finish_reason"):
                self.finish_reason = choice["finish_reason"]
        return events

    def finish(self) -> list[str]:
        events = self._start() + self._close()
        events.append(sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": _STOP_REASONS.get(self.finish_reason, "end_turn"), "stop_sequence": None},
            "usage": {"output_tokens": self.usage["output_tokens"], "input_tokens": self.usage["input_tokens"]}}))
        events.append(sse("message_stop", {"type": "message_stop"}))
        return events


# ---- 게이트웨이 호출 --------------------------------------------------------


def _endpoint(deployment: str) -> str:
    if not config.AZURE_OPENAI_ENDPOINT or not config.AZURE_OPENAI_API_KEY:
        raise ProxyError(500, "AZURE_OPENAI_ENDPOINT 또는 AZURE_OPENAI_API_KEY 가 설정되지 않았습니다.")
    return (f"{config.AZURE_OPENAI_ENDPOINT}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={config.AZURE_OPENAI_API_VERSION}")


def _upstream_message(response: httpx.Response, body: bytes) -> str:
    try:
        detail = json.loads(body).get("error") or {}
        message = detail.get("message") if isinstance(detail, dict) else str(detail)
    except ValueError:
        message = None
    return f"게이트웨이 오류(HTTP {response.status_code}): {(message or '응답 본문 없음')[:300]}"


@logged_service_operation
async def create_message(body: dict) -> dict[str, Any]:
    """비스트리밍 요청을 변환·전달하고 Anthropic 형식 응답을 돌려준다."""

    model = body.get("model") or ""
    deployment = resolve_deployment(model)
    payload = to_openai_request(body)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(_endpoint(deployment), headers={"api-key": config.AZURE_OPENAI_API_KEY}, json=payload)
    if response.status_code != 200:
        raise ProxyError(response.status_code, _upstream_message(response, response.content))
    return to_anthropic_message(response.json(), model)


@logged_service_operation
async def open_message_stream(body: dict) -> AsyncIterator[str]:
    """스트리밍 요청을 열고, 게이트웨이가 수락하면 Anthropic SSE 문자열 iterator 를 돌려준다.

    게이트웨이 오류는 스트림을 시작하기 전에 ProxyError 로 올려 HTTP 오류로 응답하게 한다.
    """

    model = body.get("model") or ""
    deployment = resolve_deployment(model)
    payload = {**to_openai_request(body), "stream": True, "stream_options": {"include_usage": True}}
    url = _endpoint(deployment)
    client = httpx.AsyncClient(timeout=_TIMEOUT)
    request = client.build_request("POST", url, headers={"api-key": config.AZURE_OPENAI_API_KEY}, json=payload)
    response = await client.send(request, stream=True)
    if response.status_code != 200:
        body_bytes = await response.aread()
        await response.aclose()
        await client.aclose()
        raise ProxyError(response.status_code, _upstream_message(response, body_bytes))

    async def events() -> AsyncIterator[str]:
        translator = StreamTranslator(model)
        try:
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                for event in translator.feed(chunk):
                    yield event
            for event in translator.finish():
                yield event
        finally:
            await response.aclose()
            await client.aclose()

    return events()


def estimate_tokens(body: dict) -> int:
    """count_tokens 요청용 근사치(문자 4개당 1토큰). 게이트웨이에 대응 API 가 없다."""

    text = json.dumps(to_openai_request(body), ensure_ascii=False)
    return max(1, len(text) // 4)
