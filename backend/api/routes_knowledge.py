"""읽기 전용 지식 조회 API. (설계 §7)

프론트 context-inspector 가 쓴다. 편집은 제공하지 않는다 — 개발 초기에는
git 으로 지식을 축적하기로 했다.
"""

import re
from pathlib import Path

from fastapi import APIRouter

from agent.agent import AGENT_SDK_CWD
from services.knowledge_service import get_store


router = APIRouter(prefix="/knowledge", tags=["knowledge"])

SKILLS_DIR = Path(AGENT_SDK_CWD) / ".claude" / "skills"

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.S)


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key.strip()] = value.strip()
    return fields


@router.get("/skills")
async def list_skills() -> list[dict]:
    """에이전트가 선택할 수 있는 Skill 목록."""

    skills = []
    for skill_path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        frontmatter = _parse_frontmatter(skill_path.read_text(encoding="utf-8"))
        skills.append(
            {
                "name": frontmatter.get("name", skill_path.parent.name),
                "description": frontmatter.get("description", ""),
                "status": "active",
            }
        )
    return skills


@router.get("/catalog")
async def list_catalog() -> list[dict]:
    """테이블 카탈로그 요약 목록."""

    return get_store().list_tables()


@router.get("/kpis")
async def list_kpis() -> list[dict]:
    """KPI 목록."""

    return get_store().list_kpis()
