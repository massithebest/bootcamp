"""Knowledge discovery and internal text management."""

import re
from pathlib import Path

from fastapi import APIRouter, Query
from typing import Literal

from agent.sdk_tools import tool_catalog
from api.schemas import (KnowledgeDocumentInput, KnowledgeDocumentUpdate, KnowledgeActionInput,
    KnowledgeDocumentResponse, KnowledgeVersion, KnowledgeEntryResponse, KnowledgeEntryDetail, KnowledgeToolResponse)
from services.document_store import KnowledgeError, get_document_store
from services.knowledge_browser import entries

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


@router.get("/tools", response_model=list[KnowledgeToolResponse])
async def tools_catalog():
    return await tool_catalog()


@router.get("/skills/{name}")
def skill_detail(name: str):
    # Resolve by discovered identifier; never turn caller input into a path.
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        if meta.get("name", path.parent.name) == name:
            return {"name": name, "description": meta.get("description", ""),
                    "status": "active", "content": _FRONTMATTER.sub("", text, count=1).strip()}
    raise KnowledgeError(404, "Skill을 찾을 수 없습니다.")


@router.get("/entries", response_model=list[KnowledgeEntryResponse])
def knowledge_entries(q: str = Query(default="", max_length=500), type: str | None = None):
    return [{k: v for k, v in item.items() if k != "detail"} for item in entries(q, type)]


@router.get("/entries/{kind}/{entry_id}", response_model=KnowledgeEntryDetail)
def knowledge_entry(kind: str, entry_id: str):
    item = next((row for row in entries(kind=kind) if row["id"] == entry_id), None)
    if item is None:
        raise KnowledgeError(404, "지식을 찾을 수 없습니다.")
    return item


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
def documents():
    return get_document_store().list()


@router.post("/documents", status_code=201, response_model=KnowledgeDocumentResponse)
def create_document(body: KnowledgeDocumentInput):
    return get_document_store().save(body.model_dump())


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentResponse)
def document_detail(document_id: str):
    return get_document_store().get(document_id)


@router.put("/documents/{document_id}", response_model=KnowledgeDocumentResponse)
def update_document(document_id: str, body: KnowledgeDocumentUpdate):
    return get_document_store().save(body.model_dump(exclude={"expected_revision"}), document_id, body.expected_revision)


@router.get("/documents/{document_id}/versions/{version}", response_model=KnowledgeVersion)
def document_version(document_id: str, version: int):
    doc = get_document_store().get(document_id)
    found = next((v for v in doc["versions"] if v["version"] == version), None)
    if found is None:
        raise KnowledgeError(404, "해당 버전을 찾을 수 없습니다.")
    return found


@router.post("/documents/{document_id}/{action}", response_model=KnowledgeDocumentResponse)
def document_action(document_id: str, action: Literal["review", "activate", "deactivate", "archive"], body: KnowledgeActionInput):
    return get_document_store().transition(document_id, action, body.expected_revision,
                                         version=body.version, actor=body.actor, note=body.note)
