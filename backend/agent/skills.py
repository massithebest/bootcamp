"""런타임 Agent Skill(`agent_sdk/.claude/skills/*/SKILL.md`) 목록과 본문.

Claude 실행부는 SDK 가 Skill 을 직접 읽고, 다른 실행부와 지식 API 는 이 모듈로 읽는다.
호출자 입력을 경로로 바꾸지 않고, 발견한 Skill 이름으로만 찾는다.
"""

import re
from dataclasses import dataclass
from pathlib import Path


#: `agent/agent_sdk/` — CLAUDE.md 와 .claude/skills 가 위치한 Agent 작업 디렉터리.
AGENT_SDK_DIR = (Path(__file__).parent / "agent_sdk").resolve()
SKILLS_DIR = AGENT_SDK_DIR / ".claude" / "skills"

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.S)


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    content: str


def parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key.strip()] = value.strip()
    return fields


def list_skills() -> list[Skill]:
    skills = []
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        skills.append(
            Skill(
                name=meta.get("name", path.parent.name),
                description=meta.get("description", ""),
                content=_FRONTMATTER.sub("", text, count=1).strip(),
            )
        )
    return skills


def get_skill(name: str) -> Skill | None:
    return next((skill for skill in list_skills() if skill.name == name), None)
