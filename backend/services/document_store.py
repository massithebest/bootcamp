"""Versioned, local text knowledge. Independent of production SQL and result TTLs."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from uuid import uuid4

from core import config
from services.service_logging import logged_service_operation


class KnowledgeError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def terms(query: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[\w]+", normalize(query))))[:30]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    @contextmanager
    def connection(self, *, write: bool = False):
        conn = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                    active_version INTEGER, archived INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS versions (
                    document_id TEXT NOT NULL REFERENCES documents(id),
                    version INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(document_id, version)
                );
                CREATE TABLE IF NOT EXISTS history (
                    document_id TEXT NOT NULL REFERENCES documents(id),
                    revision INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(document_id, revision)
                );
            """)
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            conn.commit()
        except (sqlite3.Error, OSError) as exc:
            if conn is not None:
                conn.rollback()
            raise KnowledgeError(503, "지식 저장소를 사용할 수 없습니다. 잠시 후 다시 시도하세요.") from exc
        finally:
            if conn is not None:
                conn.close()

    @staticmethod
    def _get(conn, document_id: str) -> dict:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if row is None:
            raise KnowledgeError(404, "지식을 찾을 수 없습니다.")
        return {
            **dict(row), "archived": bool(row["archived"]),
            "versions": [json.loads(r[0]) for r in conn.execute(
                "SELECT payload FROM versions WHERE document_id=? ORDER BY version DESC", (document_id,))],
            "history": [json.loads(r[0]) for r in conn.execute(
                "SELECT payload FROM history WHERE document_id=? ORDER BY revision DESC", (document_id,))],
        }

    @logged_service_operation
    def get(self, document_id: str) -> dict:
        with self.connection() as conn:
            return self._get(conn, document_id)

    @logged_service_operation
    def list(self) -> list[dict]:
        with self.connection() as conn:
            return [self._get(conn, row[0]) for row in conn.execute("SELECT id FROM documents ORDER BY rowid DESC")]

    @staticmethod
    def _history(conn, document_id, revision, action, version, actor, note=""):
        payload = dict(revision=revision, action=action, version=version, actor=actor, note=note, at=now())
        conn.execute("INSERT INTO history VALUES (?,?,?)", (document_id, revision, json.dumps(payload, ensure_ascii=False)))

    @logged_service_operation
    def save(self, fields: dict, document_id: str | None = None, expected_revision: int | None = None) -> dict:
        with self.connection(write=True) as conn:
            if document_id is None:
                document_id = uuid4().hex
                revision, version = 1, 1
                conn.execute("INSERT INTO documents(id,revision) VALUES (?,?)", (document_id, revision))
            else:
                current = self._get(conn, document_id)
                self._check(current, expected_revision)
                revision, version = current["revision"] + 1, current["versions"][0]["version"] + 1
                conn.execute("UPDATE documents SET revision=? WHERE id=?", (revision, document_id))
            payload = {**fields, "version": version, "status": "draft", "created_at": now(),
                       "reviewer": "", "review_note": "", "reviewed_at": None}
            conn.execute("INSERT INTO versions VALUES (?,?,?)", (document_id, version, json.dumps(payload, ensure_ascii=False)))
            self._history(conn, document_id, revision, "save", version, fields["owner"])
            return self._get(conn, document_id)

    @staticmethod
    def _check(document: dict, expected_revision: int | None):
        if document["revision"] != expected_revision:
            raise KnowledgeError(409, "다른 변경이 저장되었습니다. 최신 내용을 불러온 후 다시 시도하세요.")
        if document["archived"]:
            raise KnowledgeError(409, "보관한 지식은 변경할 수 없습니다.")

    @logged_service_operation
    def transition(self, document_id: str, action: str, expected_revision: int, *,
                   version: int | None = None, actor: str = "", note: str = "") -> dict:
        with self.connection(write=True) as conn:
            doc = self._get(conn, document_id)
            self._check(doc, expected_revision)
            if action not in {"review", "activate", "deactivate", "archive"}:
                raise KnowledgeError(422, "지원하지 않는 변경입니다.")
            if action in {"review", "activate"}:
                target = next((v for v in doc["versions"] if v["version"] == version), None)
                if target is None:
                    raise KnowledgeError(404, "해당 버전을 찾을 수 없습니다.")
                if version != doc["versions"][0]["version"]:
                    raise KnowledgeError(409, "최신 버전만 검토하거나 적용할 수 있습니다.")
                if action == "review":
                    if not actor.strip() or not note.strip():
                        raise KnowledgeError(422, "검토자와 검토 근거를 입력하세요.")
                    if target["status"] != "draft":
                        raise KnowledgeError(409, "이미 검토한 버전입니다.")
                    target.update(status="verified", reviewer=actor, review_note=note, reviewed_at=now())
                    conn.execute("UPDATE versions SET payload=? WHERE document_id=? AND version=?",
                                 (json.dumps(target, ensure_ascii=False), document_id, version))
                elif target["status"] != "verified":
                    raise KnowledgeError(409, "검토 완료한 버전만 활성화할 수 있습니다.")
            revision = doc["revision"] + 1
            active = version if action == "activate" else doc["active_version"]
            if action in {"archive", "deactivate"}:
                active = None
            conn.execute("UPDATE documents SET revision=?,active_version=?,archived=? WHERE id=?",
                         (revision, active, action == "archive", document_id))
            self._history(conn, document_id, revision, action, version, actor, note)
            return self._get(conn, document_id)

    @logged_service_operation
    def search(self, query: str) -> dict:
        tokens = terms(query)
        matches = []
        if tokens:
            with self.connection() as conn:
                rows = conn.execute("""SELECT d.id,v.payload FROM documents d JOIN versions v
                    ON v.document_id=d.id AND v.version=d.active_version WHERE d.archived=0""")
                for row in rows:
                    item = json.loads(row["payload"])
                    if item["status"] != "verified":
                        continue
                    title = normalize(item["title"] + " " + " ".join(item["tags"]))
                    body = normalize(item["content"])
                    matched = [t for t in tokens if t in title or t in body]
                    if not matched:
                        continue
                    rank = sum(3 if t in title else 1 for t in matched)
                    offset = max(0, min((body.find(t) for t in matched if t in body), default=0) - 80)
                    excerpt = item["content"][offset:offset + 800]
                    matches.append((rank, {"document_id": row["id"], "version": item["version"],
                        "title": item["title"], "source": item["source"], "snippet": excerpt,
                        "content": excerpt, "verified": True}))
        matches.sort(key=lambda row: (-row[0], row[1]["document_id"]))
        return {"kind": "knowledge", "status": "ok", "query": query,
                "documents": [item for _, item in matches[:10]]}


def get_document_store() -> DocumentStore:
    return DocumentStore(config.KNOWLEDGE_DB_PATH)
