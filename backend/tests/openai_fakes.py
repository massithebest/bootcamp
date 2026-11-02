"""OpenAI 실행부 테스트용 가짜 게이트웨이.

실제 `AsyncAzureOpenAI` 클라이언트를 mock HTTP transport 에 연결해, 게이트웨이가 돌려줄
Chat Completions 스트리밍(SSE) 응답을 턴마다 재생하고 받은 요청을 기록한다.
"""

import json
from typing import Any

import httpx2
from openai import AsyncAzureOpenAI

from agent import openai_runtime


DEPLOYMENT = "test-deployment"
USAGE = {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}


def _chunk(delta: dict | None = None, finish: str | None = None, usage: dict | None = None) -> dict:
    choices = [] if delta is None else [{"index": 0, "delta": delta, "finish_reason": finish}]
    chunk: dict[str, Any] = {
        "id": "chatcmpl-test", "object": "chat.completion.chunk", "created": 0,
        "model": DEPLOYMENT, "choices": choices,
    }
    if usage:
        chunk["usage"] = usage
    return chunk


def text_turn(*pieces: str) -> list[dict]:
    chunks = [_chunk({"role": "assistant", "content": ""})]
    chunks += [_chunk({"content": piece}) for piece in pieces]
    return chunks + [_chunk({}, "stop"), _chunk(usage=USAGE)]


def tool_turn(name: str, args: dict, call_id: str = "call_1", text: str | None = None) -> list[dict]:
    """Tool 호출 하나로 끝나는 응답. `text`가 있으면 호출 앞에 도입 문장을 보낸다."""

    call = {
        "index": 0, "id": call_id, "type": "function",
        "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
    }
    chunks = [_chunk({"role": "assistant", "content": text or ""})]
    chunks.append(_chunk({"tool_calls": [call]}))
    return chunks + [_chunk({}, "tool_calls"), _chunk(usage=USAGE)]


class FakeGateway:
    """턴마다 준비한 SSE 응답을 순서대로 돌려주고 받은 요청을 기록한다."""

    def __init__(self, *turns: list[dict]) -> None:
        self.turns = list(turns)
        self.requests: list[httpx2.Request] = []
        self.bodies: list[dict] = []

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        self.bodies.append(json.loads(request.content))
        chunks = self.turns.pop(0)
        body = "".join(f"data: {json.dumps(c, ensure_ascii=False)}\n\n" for c in chunks) + "data: [DONE]\n\n"
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body.encode())

    def model(self):
        client = AsyncAzureOpenAI(
            azure_endpoint="https://gateway.test",
            api_key="test-key",
            api_version="2024-12-01-preview",
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(self.handler)),
            max_retries=0,
        )
        return openai_runtime.build_model(client)


def tool_messages(body: dict) -> list[dict]:
    return [m for m in body["messages"] if m.get("role") == "tool"]
