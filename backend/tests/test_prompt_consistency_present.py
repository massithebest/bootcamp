"""`RESULT_UI_MODE=present` 전용 Agent 지침이 코드·legacy 지침과 어긋나지 않게 한다."""

import re
from pathlib import Path

import pytest

from agent.agent import AGENT_SDK_CWD, AGENT_SDK_PRESENT_CWD
from agent.sdk_tools import planning_tools, tool_names
from agent.system_prompt import SYSTEM_PROMPT
from services.knowledge_service import get_store


PRESENT_DIR = Path(AGENT_SDK_PRESENT_CWD)
LEGACY_DIR = Path(AGENT_SDK_CWD)
CLAUDE_MD = PRESENT_DIR / "CLAUDE.md"
SKILLS = sorted((PRESENT_DIR / ".claude" / "skills").glob("*/SKILL.md"))
SHORT = {name.rsplit("__", 1)[-1] for name in tool_names("present")}
LEGACY_ONLY_TERMS = ("prepare_table", "prepare_visualization", "visualization_id", "large_result")


def test_tool_table_matches_present_mode_tool_names() -> None:
    rows = re.findall(r"^\|\s*`(\w+)`\s*\|", CLAUDE_MD.read_text(encoding="utf-8"), re.M)

    assert set(rows) == SHORT


def test_skill_set_matches_legacy_directory() -> None:
    legacy = sorted((LEGACY_DIR / ".claude" / "skills").glob("*/SKILL.md"))

    assert [p.parent.name for p in SKILLS] == [p.parent.name for p in legacy]


def test_shared_skill_is_identical_to_legacy() -> None:
    """결과 표시와 무관한 Skill은 두 디렉터리에서 같은 내용을 유지한다."""

    name = "kpi-shortfall-analysis"
    assert (PRESENT_DIR / ".claude/skills" / name / "SKILL.md").read_text(encoding="utf-8") == (
        LEGACY_DIR / ".claude/skills" / name / "SKILL.md"
    ).read_text(encoding="utf-8")


def test_skills_table_in_claude_md_matches_directories() -> None:
    listed = set(re.findall(r"^- `([\w-]+)` →", CLAUDE_MD.read_text(encoding="utf-8"), re.M))

    assert listed == {p.parent.name for p in SKILLS}


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_skills_only_reference_present_mode_tools_and_no_schema_copy(skill: Path) -> None:
    body = skill.read_text(encoding="utf-8")

    assert set(re.findall(r"`(\w+)\(", body)) <= SHORT
    for table in get_store().table_names():
        assert table not in body


@pytest.mark.parametrize("path", [CLAUDE_MD, *SKILLS], ids=lambda p: p.name)
def test_no_legacy_only_instructions_remain(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    for term in LEGACY_ONLY_TERMS:
        assert term not in text, f"{path}: {term}"
    assert "simulate_" not in text


def test_present_procedure_is_documented_in_every_presenting_file() -> None:
    for path in (CLAUDE_MD, *(p for p in SKILLS if p.parent.name != "kpi-shortfall-analysis")):
        text = path.read_text(encoding="utf-8")
        assert "present_" in text and "result_id" in text, path
        assert "행·차트 data 배열" in text, path
        assert "present_table" in text and "최대 2회" in text, path
        assert "위·아래·다음 표/차트" in text and "표에는…" in text and "차트에서는…" in text, path
        assert "도입 설명 → present_* 호출 → 결과 해석" in text, path


def test_present_tool_descriptions_forbid_position_words_and_raw_tree() -> None:
    tools = {t.name: t for t in planning_tools(access_scope="scope-a", mode="present")}

    chart = tools["present_chart"].description
    table = tools["present_table"].description
    sql_preview = tools["present_sql_preview"].description
    simulation = tools["present_simulation"].description

    for description in (chart, table, sql_preview, simulation):
        assert "tree" not in description and "$type" not in description and "children" not in description

    assert "위/아래" in chart and "차트에서는" in chart and "result_id" in chart
    assert "위/아래" in table and "표에는" in table and "result_id" in table


def test_system_prompt_still_lists_no_present_mode_tools() -> None:
    for name in SHORT:
        assert name not in SYSTEM_PROMPT
