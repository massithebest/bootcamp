"""OpenAI Agents SDK 실행부.

`agent/tool_specs.py` 의 공통 Tool 명세와 Claude 실행부와 같은 런타임 지침
(`system_prompt.py` + `agent_sdk/CLAUDE.md` + Skills)으로 Agent 를 만들고,
사내 게이트웨이의 Chat Completions 를 직접 호출해 한 턴을 스트리밍 실행한다.
이벤트 변환·대화 기록은 이 모듈이 아니라 어댑터·기록 계층이 맡는다.

- 트레이싱은 기본값이 외부(OpenAI)로 전송하므로 import 시점과 실행마다 끈다.
- Tool 은 순서대로 하나씩 호출하게 해 화면 순서 규칙을 유지한다.
- `access_scope`는 Tool handler 클로저로만 전달하고 모델 입력에 넣지 않는다.
"""

import json
from typing import Any

from agents import (
    Agent,
    FunctionTool,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    set_tracing_disabled,
)
from agents.result import RunResultStreaming
from openai import AsyncAzureOpenAI, AsyncOpenAI

from agent.skills import AGENT_SDK_DIR, get_skill, list_skills
from agent.system_prompt import SYSTEM_PROMPT
from agent.tool_specs import ToolSpec, tool_specs
from core import config


set_tracing_disabled(True)

AGENT_NAME = "production-planning-agent"
LOAD_SKILL_TOOL_NAME = "load_skill"
#: 화면 Tool 사용 기록에 내보내지 않는 Tool(Skill 로딩·후속질문).
HIDDEN_TOOL_NAMES = frozenset(
    {LOAD_SKILL_TOOL_NAME} | {spec.name for spec in tool_specs() if not spec.visible}
)
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
