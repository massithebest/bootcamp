"""프롬프트 3계층과 코드 사이의 드리프트를 막는다. (설계 §2 경계 규칙)

과거 CLAUDE.md 가 삭제된 `simulate_*` 도구를 계속 안내하던 문제가 있었다.
채널마다 담을 내용이 정해져 있으므로(SYSTEM_PROMPT=원칙, CLAUDE.md=인덱스,
Skill=절차) 그 경계도 함께 검사한다.
"""

import re
from pathlib import Path

import pytest

from agent.agent import AGENT_SDK_CWD
from agent.sdk_tools import TOOL_NAMES
from agent.system_prompt import SYSTEM_PROMPT
from services.knowledge_service import get_store


SKILLS_DIR = Path(AGENT_SDK_CWD) / ".claude" / "skills"
CLAUDE_MD = Path(AGENT_SDK_CWD) / "CLAUDE.md"

EXPECTED_SKILLS = {"kpi-shortfall-analysis", "sql-analysis", "simulation"}

SHORT_TOOL_NAMES = {name.rsplit("__", 1)[-1] for name in TOOL_NAMES}


def _skill_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


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
    actual = {path.parent.name for path in _skill_files()}

    assert actual == EXPECTED_SKILLS
    assert listed == actual


def test_skill_directories_exist() -> None:
    assert {path.parent.name for path in _skill_files()} == EXPECTED_SKILLS


@pytest.mark.parametrize("skill_path", _skill_files(), ids=lambda p: p.parent.name)
def test_skill_description_marks_agent_only(skill_path: Path) -> None:
    """개발자가 이 저장소에서 Claude Code 를 열면 이 Skill 들도 보인다 (설계 §6)."""

    description = _frontmatter(skill_path.read_text(encoding="utf-8"))["description"]

    assert description.startswith("생산계획 Agent 전용.")


@pytest.mark.parametrize("skill_path", _skill_files(), ids=lambda p: p.parent.name)
def test_skill_name_matches_directory(skill_path: Path) -> None:
    assert _frontmatter(skill_path.read_text(encoding="utf-8"))["name"] == skill_path.parent.name


@pytest.mark.parametrize("skill_path", _skill_files(), ids=lambda p: p.parent.name)
def test_skill_does_not_copy_schema(skill_path: Path) -> None:
    """Skill 은 절차만 담는다. 테이블명을 복사하면 카탈로그와 어긋난다."""

    body = skill_path.read_text(encoding="utf-8")

    for table in get_store().table_names():
        assert table not in body, f"{skill_path.parent.name} 에 테이블명이 복사돼 있다: {table}"


@pytest.mark.parametrize("skill_path", _skill_files(), ids=lambda p: p.parent.name)
def test_skill_mentions_only_existing_tools(skill_path: Path) -> None:
    body = skill_path.read_text(encoding="utf-8")
    referenced = set(re.findall(r"`(\w+)\(", body))
    known = SHORT_TOOL_NAMES | {"run_simulation"}

    assert referenced <= known, f"존재하지 않는 도구를 안내한다: {referenced - known}"


def test_no_deleted_simulate_tools_remain() -> None:
    """삭제된 `simulate_*` 도구 안내가 되살아나지 않게 한다."""

    for path in [CLAUDE_MD, *_skill_files()]:
        assert "simulate_" not in path.read_text(encoding="utf-8"), path


def test_chart_procedure_requires_validated_visualization_marker() -> None:
    claude_text = CLAUDE_MD.read_text(encoding="utf-8")
    sql_skill = (SKILLS_DIR / "sql-analysis" / "SKILL.md").read_text(encoding="utf-8")
    simulation_skill = (SKILLS_DIR / "simulation" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for text in (claude_text, sql_skill, simulation_skill):
        assert "prepare_visualization" in text
        assert "visualization_id" in text
        assert "최대 2회" in text
    assert "result_id +" not in claude_text
