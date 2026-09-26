"""구조화 지식의 변경 요청 저장소(초안 → 제출 → 승인/반려)와 이력.

초안·검토·이력은 텍스트 지식과 같은 SQLite(`KNOWLEDGE_DB_PATH`)에 두고,
승인된 내용만 `knowledge_writer` 가 `knowledge/` YAML 로 반영한다.
작성자·승인자는 `Principal` 에서 받으며 인증 체계가 바뀌어도 이 계약은 유지된다.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from pydantic_core import to_jsonable_python

from core import config
from core.principal import Principal
from services.knowledge import writer
from services.knowledge.documents import KnowledgeError
from services.knowledge.models import KIND_SPECS
from services.knowledge.yaml_codec import dump_yaml, parse_yaml_mapping
from services.service_logging import logged_service_operation

logger = logging.getLogger("uvicorn.error").getChild(__name__)

OPEN_STATES = ("draft", "submitted", "rejected")
_ACTIONS = ("submit", "withdraw", "approve", "reject")
_APPLY_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChangeStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    @contextmanager
    def connection(self, *, write: bool = False):
        conn = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS change_requests (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, key TEXT NOT NULL,
                    is_new INTEGER NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
                    base_hash TEXT NOT NULL, payload TEXT NOT NULL,
                    author_id TEXT NOT NULL, author_name TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS change_history (
                    change_id TEXT NOT NULL REFERENCES change_requests(id),
                    revision INTEGER NOT NULL, action TEXT NOT NULL,
                    actor_id TEXT NOT NULL, actor_name TEXT NOT NULL,
                    note TEXT NOT NULL, self_approved INTEGER NOT NULL DEFAULT 0,
                    at TEXT NOT NULL, PRIMARY KEY(change_id, revision)
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

    # -- 조회 --

    @staticmethod
    def _row(conn, change_id: str) -> dict:
        row = conn.execute("SELECT * FROM change_requests WHERE id=?", (change_id,)).fetchone()
        if row is None:
            raise KnowledgeError(404, "변경 요청을 찾을 수 없습니다.")
        return {**dict(row), "is_new": bool(row["is_new"])}

    @staticmethod
    def _history(conn, change_id: str) -> list[dict]:
        rows = conn.execute("SELECT * FROM change_history WHERE change_id=? ORDER BY revision DESC", (change_id,))
        return [{**dict(r), "self_approved": bool(r["self_approved"])} for r in rows]

    @staticmethod
    def _summary(row: dict) -> dict:
        return {
            "id": row["id"], "kind": row["kind"], "key": row["key"], "is_new": row["is_new"],
            "state": row["state"], "revision": row["revision"],
            "author": {"id": row["author_id"], "name": row["author_name"]},
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        }

    @logged_service_operation
    def list(self, *, state: str | None = None, kind: str | None = None, author_id: str | None = None) -> list[dict]:
        clauses, args = [], []
        for column, value in (("state", state), ("kind", kind), ("author_id", author_id)):
            if value:
                clauses.append(f"{column}=?")
                args.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connection() as conn:
            rows = conn.execute(f"SELECT * FROM change_requests {where} ORDER BY updated_at DESC", args)
            return [self._summary({**dict(r), "is_new": bool(r["is_new"])}) for r in rows]

    @logged_service_operation
    def get(self, change_id: str) -> dict:
        with self.connection() as conn:
            row = self._row(conn, change_id)
            history = self._history(conn, change_id)
        base = writer.load_disk_store()
        current = writer.find_item(base, row["kind"], row["key"])
        raw, _ = parse_yaml_mapping(row["payload"])
        return {
            **self._summary(row),
            "yaml": row["payload"],
            "data": to_jsonable_python(raw or {}),
            "current_yaml": writer.normalized_yaml(current) if current else "",
            "history": history,
        }

    @logged_service_operation
    def open_index(self) -> dict[tuple[str, str], dict]:
        marks = ",".join("?" for _ in OPEN_STATES)
        with self.connection() as conn:
            rows = conn.execute(f"SELECT id,kind,key,state FROM change_requests WHERE state IN ({marks})", OPEN_STATES)
            return {(r["kind"], r["key"]): {"id": r["id"], "state": r["state"]} for r in rows}

    # -- 내용 준비 --

    @staticmethod
    def _prepare(kind: str, yaml_text: str | None, data: dict | None,
                 key: str | None, is_new: bool) -> tuple[str, str]:
        """저장할 payload 와 키를 정한다. 검증을 통과한 내용은 정규화하고 아니면 그대로 둔다.

        `key` 는 이미 정해진 식별자다(신규 생성 전에는 None). 식별자는 바꿀 수 없다.
        """

        if kind not in KIND_SPECS:
            raise KnowledgeError(404, "알 수 없는 지식 종류입니다.")
        if (yaml_text is None) == (data is None):
            raise KnowledgeError(422, "yaml 과 data 중 하나만 보내세요.")
        if data is None:
            raw, errors = parse_yaml_mapping(yaml_text)
            if raw is None:
                raise KnowledgeError(422, writer.issues_summary(errors))
        else:
            raw = data
        field = KIND_SPECS[kind].key_field
        item_key = raw.get(field)
        problem = writer.check_key(kind, item_key if isinstance(item_key, str) else "")
        if problem:
            raise KnowledgeError(422, problem)
        if key is not None and key != item_key:
            raise KnowledgeError(422, "저장된 식별자는 바꿀 수 없습니다.")
        result = writer.validate(
            kind, data=raw if data is not None else None, yaml_text=yaml_text,
            key=None if is_new else key,
        )
        if result["ok"] or result["yaml"]:
            payload = result["yaml"]
        else:
            payload = yaml_text if data is None else dump_yaml(raw)
        return payload, item_key

    @staticmethod
    def _add_history(conn, change_id, revision, action, principal: Principal, note="", self_approved=False):
        conn.execute(
            "INSERT INTO change_history VALUES (?,?,?,?,?,?,?,?)",
            (change_id, revision, action, principal.id, principal.name, note, int(self_approved), _now()),
        )

    @staticmethod
    def _require_author(row: dict, principal: Principal) -> None:
        if row["author_id"] != principal.id:
            raise KnowledgeError(403, "작성자만 이 작업을 할 수 있습니다.")

    @staticmethod
    def _check_revision(row: dict, expected_revision: int) -> None:
        if row["revision"] != expected_revision:
            raise KnowledgeError(409, "다른 변경이 저장되었습니다. 최신 내용을 불러온 후 다시 시도하세요.")

    # -- 생성·수정 --

    @logged_service_operation
    def create(self, principal: Principal, kind: str, *, yaml_text: str | None = None,
               data: dict | None = None, key: str | None = None) -> dict:
        payload, item_key = self._prepare(kind, yaml_text, data, key, key is None)
        base = writer.load_disk_store()
        existing = writer.find_item(base, kind, item_key)
        if key is None and existing is not None:
            raise KnowledgeError(409, "이미 있는 지식입니다. 기존 항목에서 수정 요청을 만드세요.")
        if key is not None and existing is None:
            raise KnowledgeError(404, "수정할 기존 지식을 찾을 수 없습니다.")
        with self.connection(write=True) as conn:
            open_row = conn.execute(
                f"SELECT id FROM change_requests WHERE kind=? AND key=? AND state IN ({','.join('?' for _ in OPEN_STATES)})",
                (kind, item_key, *OPEN_STATES),
            ).fetchone()
            if open_row:
                raise KnowledgeError(409, "이 지식에 진행 중인 변경 요청이 있습니다. 먼저 처리하거나 철회하세요.")
            change_id, now = uuid4().hex, _now()
            conn.execute(
                "INSERT INTO change_requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (change_id, kind, item_key, int(existing is None), "draft", 1,
                 writer.content_hash(existing), payload, principal.id, principal.name, now, now),
            )
            self._add_history(conn, change_id, 1, "create", principal)
        return self.get(change_id)

    @logged_service_operation
    def update(self, principal: Principal, change_id: str, expected_revision: int, *,
               yaml_text: str | None = None, data: dict | None = None) -> dict:
        with self.connection(write=True) as conn:
            row = self._row(conn, change_id)
            self._require_author(row, principal)
            self._check_revision(row, expected_revision)
            if row["state"] not in ("draft", "rejected"):
                raise KnowledgeError(409, "초안이나 반려된 요청만 수정할 수 있습니다.")
            payload, _ = self._prepare(row["kind"], yaml_text, data, row["key"], row["is_new"])
            revision = row["revision"] + 1
            conn.execute(
                "UPDATE change_requests SET payload=?, state='draft', revision=?, updated_at=? WHERE id=?",
                (payload, revision, _now(), change_id),
            )
            self._add_history(conn, change_id, revision, "save", principal)
        return self.get(change_id)

    # -- 상태 전이 --

    @logged_service_operation
    def transition(self, principal: Principal, change_id: str, action: str,
                   expected_revision: int, note: str = "") -> dict:
        if action not in _ACTIONS:
            raise KnowledgeError(422, "지원하지 않는 변경입니다.")
        note = note.strip()
        with self.connection(write=True) as conn:
            row = self._row(conn, change_id)
            self._check_revision(row, expected_revision)
            revision = row["revision"] + 1
            self_approved = False

            if action == "withdraw":
                self._require_author(row, principal)
                if row["state"] not in OPEN_STATES:
                    raise KnowledgeError(409, "진행 중인 요청만 철회할 수 있습니다.")
                new_state = "withdrawn"
            elif action == "submit":
                self._require_author(row, principal)
                if row["state"] != "draft":
                    raise KnowledgeError(409, "초안만 제출할 수 있습니다.")
                self._check_base(row)
                result = writer.validate(
                    row["kind"], yaml_text=row["payload"], key=None if row["is_new"] else row["key"]
                )
                if not result["ok"]:
                    raise KnowledgeError(422, writer.issues_summary(result["errors"]))
                conn.execute("UPDATE change_requests SET payload=? WHERE id=?", (result["yaml"], change_id))
                new_state = "submitted"
            elif action == "reject":
                if row["state"] != "submitted":
                    raise KnowledgeError(409, "제출된 요청만 반려할 수 있습니다.")
                if not note:
                    raise KnowledgeError(422, "반려 사유를 입력하세요.")
                new_state = "rejected"
            else:  # approve
                if row["state"] != "submitted":
                    raise KnowledgeError(409, "제출된 요청만 승인할 수 있습니다.")
                if not note:
                    raise KnowledgeError(422, "승인 근거를 입력하세요.")
                self_approved = row["author_id"] == principal.id
                if self_approved and not config.KNOWLEDGE_ALLOW_SELF_APPROVAL:
                    raise KnowledgeError(403, "작성자는 자신의 요청을 승인할 수 없습니다.")
                new_state = "approved"

            conn.execute(
                "UPDATE change_requests SET state=?, revision=?, updated_at=? WHERE id=?",
                (new_state, revision, _now(), change_id),
            )
            self._add_history(conn, change_id, revision, action, principal, note, self_approved)
            if action == "approve":
                # 파일 반영이 실패하면 예외로 이 트랜잭션이 롤백되어 상태는 submitted 로 남는다.
                self._apply(row)
                logger.info("지식 변경 승인 반영: kind=%s self_approved=%s", row["kind"], self_approved)
        return self.get(change_id)

    @staticmethod
    def _check_base(row: dict) -> None:
        base = writer.load_disk_store()
        current = writer.find_item(base, row["kind"], row["key"])
        if writer.content_hash(current) != row["base_hash"]:
            raise KnowledgeError(409, "기준 지식이 그 사이에 변경되었습니다. 최신 내용으로 다시 작성하세요.")

    @staticmethod
    def _apply(row: dict) -> None:
        with _APPLY_LOCK:
            base = writer.load_disk_store()
            current = writer.find_item(base, row["kind"], row["key"])
            if writer.content_hash(current) != row["base_hash"]:
                raise KnowledgeError(409, "기준 지식이 그 사이에 변경되었습니다. 최신 내용으로 다시 작성하세요.")
            result = writer.validate(
                row["kind"], yaml_text=row["payload"], key=None if row["is_new"] else row["key"]
            )
            if not result["ok"]:
                raise KnowledgeError(422, writer.issues_summary(result["errors"]))
            model = writer.approved_model(row["kind"], row["payload"], author_name=row["author_name"])
            writer.apply_item(row["kind"], model, base)


def get_change_store() -> ChangeStore:
    return ChangeStore(config.KNOWLEDGE_DB_PATH)
