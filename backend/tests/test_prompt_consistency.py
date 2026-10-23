"""프롬프트 3계층과 코드 사이의 드리프트를 막는다. (설계 §2 경계 규칙)

과거 CLAUDE.md 가 삭제된 `simulate_*` 도구를 계속 안내하던 문제가 있었다.
채널마다 담을 내용이 정해져 있으므로(SYSTEM_PROMPT=원칙, CLAUDE.md=인덱스,
Skill=절차) 그 경계도 함께 검사한다.
"""

import re
from pathlib import Path

import pytest

from agent.agent import AGENT_SDK_CWD
from agent.sdk_tools import TOOL_NAMES, planning_tools
from agent.system_prompt import SYSTEM_PROMPT
from services.knowledge.catalog import get_store


CLAUDE_MD = Path(AGENT_SDK_CWD) / "CLAUDE.md"
SKILLS = sorted((Path(AGENT_SDK_CWD) / ".claude" / "skills").glob("*/SKILL.md"))

EXPECTED_SKILLS = {"sql-analysis", "simulation"}

SHORT_TOOL_NAMES = {name.rsplit("__", 1)[-1] for name in TOOL_NAMES}

#: 결과 표시가 `present_*` Tool로 통일되기 전에 쓰던 legacy 전용 용어.
#: 되살아나면 지침이 삭제된 legacy mode 를 다시 안내하는 회귀다.
LEGACY_ONLY_TERMS = ("prepare_table", "prepare_visualization", "visualization_id", "large_result")


def _frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    assert match, "SKILL.md 에 frontmatter 가 없다"
    fields = {}
    for line in match.group(1).splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key.strip()] = value.strip()
    return fields


def test_system_prompt_is_short() -> None:
    assert SYSTEM_PROMPT.strip().count("\n") < 30


def test_system_prompt_defines_pt_factory_planning_scope() -> None:
    assert "P&T(Package & Test) Factory Planning" in SYSTEM_PROMPT
    assert "가용 용량 및 공정 제약" in SYSTEM_PROMPT
    assert "실현 가능한 생산계획" in SYSTEM_PROMPT


def test_system_prompt_does_not_list_tools() -> None:
    """도구 목록은 CLAUDE.md 책임이다 — 두 곳에 있으면 드리프트가 생긴다."""

    for name in SHORT_TOOL_NAMES:
        assert name not in SYSTEM_PROMPT, f"SYSTEM_PROMPT 에 도구 이름이 있다: {name}"


def test_claude_md_tool_table_matches_tool_names() -> None:
    rows = re.findall(r"^\|\s*`(\w+)`\s*\|", CLAUDE_MD.read_text(encoding="utf-8"), re.M)

    assert set(rows) == SHORT_TOOL_NAMES


def test_claude_md_lists_actual_skills() -> None:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    listed = set(re.findall(r"^- `([\w-]+)` →", text, re.M))
    actual = {path.parent.name for path in SKILLS}

    assert actual == EXPECTED_SKILLS
    assert listed == actual


def test_skill_directories_exist() -> None:
    assert {path.parent.name for path in SKILLS} == EXPECTED_SKILLS


@pytest.mark.parametrize("skill_path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_description_marks_agent_only(skill_path: Path) -> None:
    """개발자가 이 저장소에서 Claude Code 를 열면 이 Skill 들도 보인다 (설계 §6)."""

    description = _frontmatter(skill_path.read_text(encoding="utf-8"))["description"]

    assert description.startswith("생산계획 Agent 전용.")


@pytest.mark.parametrize("skill_path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_name_matches_directory(skill_path: Path) -> None:
    assert _frontmatter(skill_path.read_text(encoding="utf-8"))["name"] == skill_path.parent.name


@pytest.mark.parametrize("skill_path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_does_not_copy_schema(skill_path: Path) -> None:
    """Skill 은 절차만 담는다. 테이블명을 복사하면 카탈로그와 어긋난다."""

    body = skill_path.read_text(encoding="utf-8")

    for table in get_store().table_names():
        assert table not in body, f"{skill_path.parent.name} 에 테이블명이 복사돼 있다: {table}"


@pytest.mark.parametrize("skill_path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_mentions_only_existing_tools(skill_path: Path) -> None:
    body = skill_path.read_text(encoding="utf-8")
    referenced = set(re.findall(r"`(\w+)\(", body))
    known = SHORT_TOOL_NAMES | {"run_simulation"}

    assert referenced <= known, f"존재하지 않는 도구를 안내한다: {referenced - known}"


@pytest.mark.parametrize("path", [CLAUDE_MD, *SKILLS], ids=lambda p: p.name)
def test_no_legacy_only_instructions_remain(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    for term in LEGACY_ONLY_TERMS:
        assert term not in text, f"{path}: {term}"
    assert "simulate_" not in text


def test_present_procedure_is_documented_in_every_presenting_file() -> None:
    for path in (CLAUDE_MD, *SKILLS):
        text = path.read_text(encoding="utf-8")
        assert "present_" in text and "result_id" in text, path
        assert "행·차트 data 배열" in text, path
        assert "present_table" in text and "최대 2회" in text, path
        assert "위·아래·다음 표/차트" in text and "표에는…" in text and "차트에서는…" in text, path
        assert "도입 설명 → present_* 호출 → 결과 해석" in text, path


def test_present_tool_descriptions_forbid_position_words_and_raw_tree() -> None:
    tools = {t.name: t for t in planning_tools(access_scope="scope-a")}

    chart = tools["present_chart"].description
    table = tools["present_table"].description
    sql_preview = tools["present_sql_preview"].description
    simulation = tools["present_simulation"].description

    for description in (chart, table, sql_preview, simulation):
        assert "tree" not in description and "$type" not in description and "children" not in description

    assert "위/아래" in chart and "차트에서는" in chart and "result_id" in chart
    assert "bar_mode=stacked" in chart and "group_by_column" in chart
    # 여러 지표 비교는 지표마다 차트를 나누지 않고 long 형식 + group_by_column 으로 묶는다.
    assert "long 형식" in chart and "group_by_column=지표 이름 컬럼" in chart
    assert "단위가 다른 지표는 한 차트에 묶지 말고" in chart
    assert "위/아래" in table and "표에는" in table and "result_id" in table
    # result_id 는 Tool 인자 전용이며 답변 본문에 노출하지 않는다.
    assert "답변 본문에 적지 않는다" in tools["execute_sql"].description


def test_claude_md_keeps_internal_ids_out_and_does_not_turn_include_rules_into_filters() -> None:
    text = CLAUDE_MD.read_text(encoding="utf-8")

    assert "내부 식별자를 쓰지 않는다" in text
    assert "recipe_id" in text and "kpi_id" in text and "표시 이름" in text
    assert "제외 필터로 바꾸지 않" in text
    # 포함 규칙과 달리 "요청했을 때만 포함" 같은 기본 제외 조건은 반드시 필터로 적용한다.
    assert "명시적으로 요청했을 때만 포함한다" in text and "반드시" in text


def test_routing_policy_uses_requested_operation_and_evidence() -> None:
    """호칭 표현보다 실행·조회 목적을 우선하는 공통 라우팅 규칙을 유지한다."""

    claude = CLAUDE_MD.read_text(encoding="utf-8")
    sql_skill = next(p for p in SKILLS if p.parent.name == "sql-analysis").read_text(encoding="utf-8")
    simulation_skill = next(p for p in SKILLS if p.parent.name == "simulation").read_text(encoding="utf-8")

    assert '"시뮬레이션을 수행/실행해 줘"' in claude
    assert '"데이터베이스/DB/SQL에서 조회해 줘"' in claude
    assert '"DB에 저장된 시뮬레이션 결과를 조회"' in claude
    assert "방법·위치·의미를 묻는 질문은 문서 검색" in claude
    assert '"알려줘/보여줘"' in claude
    assert "미지원임을 알린다" in claude

    assert '"DB/데이터베이스/SQL에서 조회해 줘"' in sql_skill
    assert '"DB에 저장된 simulation 결과를 조회"' in sql_skill
    assert '"수행/실행해 줘"' in simulation_skill
    assert '"DB에 저장된 simulation 결과를 조회"' in simulation_skill
    assert '직전 성공한 결과의 출처와 범위' in simulation_skill


def test_data_tool_descriptions_distinguish_sql_simulation_and_documents() -> None:
    tools = {t.name: t for t in planning_tools(access_scope="scope-a")}

    assert "DB/데이터베이스/SQL 조회" in tools["execute_sql"].description
    assert "등록 simulation" in tools["run_simulation"].description
    assert "임의의 종류" in tools["run_simulation"].description
    assert "화면 버튼·변경 위치·조회 방법" in tools["search_documents"].description
    assert "실제 저장 수치 조회나 simulation 실행을 대신하지 않는다" in tools["search_documents"].description


def test_rag_final_answers_require_a_source_or_url() -> None:
    claude = CLAUDE_MD.read_text(encoding="utf-8")

    assert "최종 응답" in claude
    assert "`source` 또는 검색 결과가 제공한 URL을 반드시 포함" in claude
    assert "출처와 URL이 모두 없는 검색 결과는 최종 답변의 근거로 사용하지 않는다" in claude
