"""OpenAI Agents SDK 실행부.

`agent/tool_specs.py` 의 공통 Tool 명세와 Claude 실행부와 같은 런타임 지침
(`system_prompt.py` + `agent_sdk/CLAUDE.md` + Skills)으로 Agent 를 만들고,
사내 게이트웨이의 Chat Completions 를 직접 호출해 한 턴을 스트리밍 실행한다.
`AgentEvent` 변환은 `openai_event_adapter`가 맡는다.

- 트레이싱은 기본값이 외부(OpenAI)로 전송하므로 import 시점과 실행마다 끈다.
- Tool 은 순서대로 하나씩 호출하게 해 화면 순서 규칙을 유지한다.
- `access_scope`는 Tool handler 클로저로만 전달하고 모델 입력에 넣지 않는다.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from agents import (
    Agent,
    AgentsException,
    FunctionTool,
    MaxTurnsExceeded,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    set_tracing_disabled,
)
from agents.result import RunResultStreaming
from openai import APIError, AsyncAzureOpenAI, AsyncOpenAI

from agent import openai_session_store as session_store
from agent.openai_event_adapter import OpenAIEventAdapter
from agent.public_messages import (
    FORK_FALLBACK_MESSAGE,
    INCOMPLETE_RESPONSE_MESSAGE,
    LLM_API_FAILURE_MESSAGE,
    LLM_RESPONSE_TIMEOUT_MESSAGE,
    MAX_TURNS_MESSAGE,
)
from agent.skills import AGENT_SDK_DIR, get_skill, list_skills
from agent.system_prompt import SYSTEM_PROMPT
from agent.tool_events import TOOL_FAILURE_PAYLOAD
from agent.tool_specs import ToolSpec, tool_specs
from api.schemas import AgentEvent
from core import config


set_tracing_disabled(True)

logger = logging.getLogger(__name__)

AGENT_NAME = "production-planning-agent"
LOAD_SKILL_TOOL_NAME = "load_skill"
INSTRUCTIONS_PATH = AGENT_SDK_DIR / "CLAUDE.md"


def _error(message: str) -> str:
    return json.dumps({"status": "error", "message": message}, ensure_ascii=False)


def _parse_arguments(raw: str) -> dict[str, Any] | None:
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return None
    return args if isinstance(args, dict) else None


def build_instructions() -> str:
    """SYSTEM_PROMPT + CLAUDE.md 본문 + Skill 목록. 지침 파일이 없으면 시작 오류."""

    skills = "\n".join(f"- `{skill.name}`: {skill.description}" for skill in list_skills())
    return (
        f"{SYSTEM_PROMPT.strip()}\n\n"
        f"{INSTRUCTIONS_PATH.read_text(encoding='utf-8').strip()}\n\n"
        "## Skill 불러오기\n\n"
        f"업무 절차가 필요한 질의는 답하기 전에 `{LOAD_SKILL_TOOL_NAME}(name)`으로 해당 Skill 본문을 읽고 "
        "그 절차를 따른다. 사용할 수 있는 Skill:\n"
        f"{skills}"
    )


def _function_tool(spec: ToolSpec, access_scope: str | None) -> FunctionTool:
    async def _invoke(_context: Any, raw: str) -> str:
        args = _parse_arguments(raw)
        if args is None:
            return _error("Tool 인자를 JSON 객체로 읽을 수 없습니다.")
        try:
            payload = await spec.handler(args, access_scope)
        except KeyError as exc:
            return _error(f"필수 인자가 없습니다: {exc.args[0]}")
        except Exception as exc:
            # 예외 원문에는 내부 경로·SQL 이 들어갈 수 있어 모델·화면에는 공개 문구만 보낸다.
            logger.error("Tool 실행 실패: tool=%s error_type=%s", spec.name, type(exc).__name__)
            return json.dumps(TOOL_FAILURE_PAYLOAD, ensure_ascii=False)
        return json.dumps(payload, ensure_ascii=False)

    # 선택 필드·자유 객체(params 등)가 있는 schema 는 strict 모드가 거부하므로 끄고,
    # 인자 검증은 지금처럼 present·aggregate 등 서버 쪽에서 한다.
    return FunctionTool(
        name=spec.name,
        description=spec.description,
        params_json_schema=spec.input_schema,
        on_invoke_tool=_invoke,
        strict_json_schema=False,
    )


def _load_skill_tool() -> FunctionTool:
    names = [skill.name for skill in list_skills()]

    async def _invoke(_context: Any, raw: str) -> str:
        args = _parse_arguments(raw) or {}
        skill = get_skill(str(args.get("name", "")))
        if skill is None:
            return _error(f"등록된 Skill이 아닙니다. 사용할 수 있는 Skill: {', '.join(names)}")
        return skill.content

    return FunctionTool(
        name=LOAD_SKILL_TOOL_NAME,
        description="업무 절차 Skill 본문을 읽는다. 답하기 전에 질의에 맞는 Skill 을 한 번 불러 그 절차를 따른다.",
        params_json_schema={
            "type": "object",
            "properties": {"name": {"type": "string", "enum": names}},
            "required": ["name"],
            "additionalProperties": False,
        },
        on_invoke_tool=_invoke,
        strict_json_schema=False,
    )


def build_model(client: AsyncOpenAI | None = None) -> OpenAIChatCompletionsModel:
    """게이트웨이 deployment 로 Chat Completions 모델을 만든다. 설정이 비면 설정 오류."""

    for name in ("AZURE_OPENAI_DEPLOYMENT",) + (
        () if client else ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
    ):
        if not getattr(config, name):
            raise RuntimeError(
                f"OpenAI Agents SDK 실행부에 필요한 환경변수 {name} 이(가) 비어 있습니다. "
                "backend/.env에 값을 설정하세요."
            )
    if client is None:
        client = AsyncAzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
        )
    return OpenAIChatCompletionsModel(model=config.AZURE_OPENAI_DEPLOYMENT, openai_client=client)


def model_settings() -> ModelSettings:
    # temperature·top_p 는 reasoning 계열이 거부할 수 있어 지정하지 않는다. max_tokens 대신
    # max_completion_tokens 를 써야 하는 것도 같은 이유다(프록시와 같은 상한 설정 사용).
    cap = config.AZURE_OPENAI_MAX_TOKENS
    return ModelSettings(
        parallel_tool_calls=False,
        include_usage=True,
        extra_args={"max_completion_tokens": cap} if cap else None,
    )


def build_agent(access_scope: str | None, model: OpenAIChatCompletionsModel) -> Agent:
    return Agent(
        name=AGENT_NAME,
        instructions=build_instructions(),
        model=model,
        model_settings=model_settings(),
        tools=[*(_function_tool(spec, access_scope) for spec in tool_specs()), _load_skill_tool()],
    )


def run_streamed(
    input_items: str | list[Any],
    *,
    access_scope: str | None,
    model: OpenAIChatCompletionsModel | None = None,
) -> RunResultStreaming:
    """한 턴을 스트리밍 실행한다. `input_items`는 새 메시지 또는 이전 기록 + 새 메시지."""

    agent = build_agent(access_scope, model or build_model())
    return Runner.run_streamed(
        agent,
        input_items,
        max_turns=config.AGENT_MAX_TURNS,
        run_config=RunConfig(tracing_disabled=True),
    )


def _resolve_history(
    conversation_id: str | None, fork_from_turn_id: str | None
) -> tuple[list[Any], AgentEvent | None]:
    """이번 턴 앞에 붙일 기록과, 분기 지점을 찾지 못했을 때의 경고 이벤트."""

    if fork_from_turn_id is None:
        return session_store.latest_history(conversation_id), None
    if fork_from_turn_id == "":
        return [], None
    history = session_store.turn_history(fork_from_turn_id)
    if history is None:
        return [], AgentEvent(type="error", content=FORK_FALLBACK_MESSAGE)
    return history, None


def _failure_message(exc: Exception) -> str | None:
    """실행 실패를 공개 문구로 바꾼다. 처리하지 않는 예외는 None(라우트의 일반 오류로)."""

    if isinstance(exc, MaxTurnsExceeded):
        logger.warning("Agent 최대 모델 호출 수 초과: max_turns=%s", config.AGENT_MAX_TURNS)
        return MAX_TURNS_MESSAGE
    if isinstance(exc, APIError):
        logger.error(
            "LLM API 호출 실패: error_type=%s status=%s",
            type(exc).__name__, getattr(exc, "status_code", None),
        )
        return LLM_API_FAILURE_MESSAGE
    if isinstance(exc, AgentsException):
        logger.error("Agent 실행 실패: error_type=%s", type(exc).__name__)
        return INCOMPLETE_RESPONSE_MESSAGE
    return None


async def run_openai_agent(
    message: str,
    conversation_id: str | None = None,
    fork_from_turn_id: str | None = None,
    access_scope: str | None = None,
    *,
    model: OpenAIChatCompletionsModel | None = None,
) -> AsyncIterator[AgentEvent]:
    """`agent.run_agent`의 OpenAI 실행부. 같은 인자와 `AgentEvent` 계약을 따른다.

    `fork_from_turn_id`가 None 이면 대화의 최신 기록에 이어 쓰고, 빈 문자열이면 처음부터,
    알 수 없는 값이면 경고 `error` 후 처음부터 실행한다. 성공한 턴만 기록·분기 지점으로 남긴다.

    `LLM_RESPONSE_TIMEOUT_SECONDS` 동안 다음 스트림 이벤트가 없거나, 최대 호출 수 초과·게이트웨이
    오류·모델 응답 오류가 나면 공개 문구로 `error` → `done`(turn_id 없음)으로 끝낸다. 완료 전에
    끝나면(오류·클라이언트 연결 종료 포함) 실행 중인 SDK 작업을 취소한다. 그 밖의 예외는 라우트가
    공개 `error` → `done`으로 바꾼다.
    """

    turn_id = str(uuid.uuid4())
    history, warning = _resolve_history(conversation_id, fork_from_turn_id)
    if warning is not None:
        yield warning

    adapter = OpenAIEventAdapter()
    result = run_streamed(
        [*history, {"role": "user", "content": message}], access_scope=access_scope, model=model
    )
    raw_events = result.stream_events()
    completed = False
    try:
        while True:
            try:
                raw_event = await asyncio.wait_for(
                    anext(raw_events), timeout=config.LLM_RESPONSE_TIMEOUT_SECONDS
                )
            except StopAsyncIteration:
                break
            for event in adapter.convert(raw_event):
                yield event
        completed = True
    except asyncio.TimeoutError:
        logger.warning("LLM 응답 대기 시간 초과: timeout=%ss", config.LLM_RESPONSE_TIMEOUT_SECONDS)
        failure = LLM_RESPONSE_TIMEOUT_MESSAGE
    except Exception as exc:
        failure = _failure_message(exc)
        if failure is None:
            raise
    finally:
        if not completed:
            result.cancel()

    if not completed:
        yield AgentEvent(type="error", content=failure)
        yield AgentEvent(type="done")
        return

    session_store.record_turn(conversation_id, turn_id, result.to_input_list())
    done_data: dict[str, object] = {"turn_id": turn_id}
    if adapter.suggestions:
        done_data["suggestions"] = adapter.suggestions
    yield AgentEvent(type="done", data=done_data)
