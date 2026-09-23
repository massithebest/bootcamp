"""구조화 지식 변경의 검증과 YAML 반영.

`knowledge/` 의 YAML 이 계속 런타임 단일 기준이다. 이 모듈은 제안된 변경을
모델·정합성 규칙으로 검증하고, 승인된 변경만 원자적으로 파일에 쓴 뒤 store 를 다시 읽는다.
변경 요청의 상태·이력은 `knowledge_change_store` 가 소유한다.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from pydantic_core import to_jsonable_python

from services.knowledge import catalog as ks
from services.knowledge.documents import KnowledgeError
from services.knowledge.guides import shape_errors
from services.knowledge.integrity import integrity_issues
from services.knowledge.catalog import GLOSSARY_FILE, KIND_SPECS, KnowledgeStore
from services.knowledge.yaml_codec import dump_yaml, model_to_data, parse_yaml_mapping
from services.service_logging import logged_service_operation

#: 파일명으로 쓰이는 키. 경로 구분자·점·공백을 허용하지 않아 경로 주입을 막는다.
_FILE_KEY = re.compile(r"^\w[\w\-]{0,99}$")
_GLOSSARY_TERM_MAX = 200

_MESSAGES = {
    "missing": "필수 항목입니다.",
    "extra_forbidden": "허용되지 않는 필드입니다.",
    "string_type": "문자열이어야 합니다.",
    "list_type": "목록이어야 합니다.",
    "dict_type": "key: value 형태여야 합니다.",
    "bool_type": "true 또는 false 여야 합니다.",
    "bool_parsing": "true 또는 false 여야 합니다.",
    "int_type": "정수여야 합니다.",
    "int_parsing": "정수여야 합니다.",
    "date_type": "날짜(YYYY-MM-DD)여야 합니다.",
    "date_from_datetime_parsing": "날짜(YYYY-MM-DD)여야 합니다.",
}


def _path(location: tuple) -> str:
    out = ""
    for part in location:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out


def _pydantic_errors(exc: ValidationError) -> list[dict[str, Any]]:
    errors = []
    for error in exc.errors():
        kind = error["type"]
        if kind == "literal_error":
            expected = ", ".join(str(v) for v in (error.get("ctx") or {}).get("expected", "").split(" or "))
            message = f"허용된 값이 아닙니다: {expected}"
        elif kind == "value_error":
            message = str(error["msg"]).removeprefix("Value error, ")
        else:
            message = _MESSAGES.get(kind, str(error["msg"]))
        errors.append({"path": _path(error["loc"]), "line": None, "message": message})
    return errors


def load_disk_store() -> KnowledgeStore:
    """캐시가 아니라 디스크의 현재 YAML 을 새로 읽는다. 기준 충돌 검사의 근거다."""

    try:
        return KnowledgeStore.load(ks.KNOWLEDGE_DIR)
    except (ValueError, OSError) as exc:
        raise KnowledgeError(503, "지식 파일을 읽을 수 없습니다. 관리자에게 문의하세요.") from exc


def find_item(store: KnowledgeStore, kind: str, key: str):
    spec = KIND_SPECS[kind]
    if kind == "glossary":
        return next((entry for entry in store.glossary if entry.term == key), None)
    return getattr(store, spec.attribute).get(key)


def with_item(store: KnowledgeStore, kind: str, model) -> KnowledgeStore:
    """`model` 로 항목 하나를 바꾸거나 추가한 새 저장소. 원본은 바꾸지 않는다."""

    spec = KIND_SPECS[kind]
    key = getattr(model, spec.key_field)

    def merged(target: str, items: list) -> list:
        if target != kind:
            return list(items)
        kept = [item for item in items if getattr(item, spec.key_field) != key]
        return [*kept, model]

    return KnowledgeStore(
        merged("table", list(store.tables.values())),
        merged("kpi", list(store.kpis.values())),
        merged("simulation", list(store.simulations.values())),
        merged("glossary", store.glossary),
        merged("recipe", list(store.recipes.values())),
        merged("scenario", list(store.scenarios.values())),
    )


def normalized_yaml(model) -> str:
    return dump_yaml(model_to_data(model))


def content_hash(model) -> str:
    """기준 충돌 검사용 해시. 파일 서식이 아니라 정규화한 내용을 기준으로 한다."""

    import hashlib

    return "" if model is None else hashlib.sha256(normalized_yaml(model).encode()).hexdigest()


def check_key(kind: str, key: str) -> str | None:
    """키가 파일명·항목 이름으로 안전하지 않으면 사유를 돌려준다."""

    if not isinstance(key, str) or not key.strip():
        return f"{KIND_SPECS[kind].key_field}은(는) 필수입니다."
    if kind == "glossary":
        return None if len(key) <= _GLOSSARY_TERM_MAX else "용어가 너무 깁니다."
    if not _FILE_KEY.match(key):
        return "식별자는 문자·숫자·밑줄·하이픈만 쓸 수 있고 100자 이하여야 합니다."
    return None


def _pin_meta(model, existing) -> None:
    """작성자가 관리 메타를 바꾸지 못하게 기존 값(신규는 draft)으로 되돌린다."""

    model.status = existing.status if existing else "draft"
    model.updated = existing.updated if existing else None


@logged_service_operation
def validate(
    kind: str,
    *,
    yaml_text: str | None = None,
    data: dict[str, Any] | None = None,
    key: str | None = None,
) -> dict[str, Any]:
    """제안 내용을 저장하지 않고 검증한다. 형식·모델·정합성 오류를 한 번에 돌려준다.

    `key` 를 주면 기존 항목 수정으로 보고 키 필드가 바뀌지 않았는지도 확인한다.
    """

    if kind not in KIND_SPECS:
        raise KnowledgeError(404, "알 수 없는 지식 종류입니다.")
    spec = KIND_SPECS[kind]
    result: dict[str, Any] = {
        "ok": False,
        # 폼(data)에서 온 내용은 아직 모델을 통과하지 못해도 원문 탭에 보여줄 YAML 을 돌려준다.
        "yaml": yaml_text if yaml_text is not None else dump_yaml(to_jsonable_python(data or {})),
        "data": data or {},
        "parsed": False,
        "key": key or "",
        "errors": [],
    }

    if data is None:
        raw, errors = parse_yaml_mapping(yaml_text or "")
        if raw is None:
            result["errors"] = errors
            return result
    else:
        raw = data

    result["parsed"] = True
    errors = shape_errors(kind, raw)
    try:
        model = spec.model.model_validate(raw)
    except ValidationError as exc:
        seen = {(e["path"]) for e in errors}
        errors += [e for e in _pydantic_errors(exc) if e["path"] not in seen]
        result["errors"] = errors
        result["data"] = to_jsonable_python(raw)
        return result
    if errors:
        result["errors"] = errors
        result["data"] = to_jsonable_python(raw)
        return result

    item_key = getattr(model, spec.key_field)
    problem = check_key(kind, item_key)
    if problem:
        errors.append({"path": spec.key_field, "line": None, "message": problem})
    elif key is not None and key != item_key:
        errors.append({"path": spec.key_field, "line": None, "message": "저장된 식별자는 바꿀 수 없습니다."})
    if errors:
        result["errors"] = errors
        result["data"] = to_jsonable_python(raw)
        return result

    base = load_disk_store()
    existing = find_item(base, kind, item_key)
    if key is None and existing is not None:
        errors.append({"path": spec.key_field, "line": None, "message": "이미 있는 지식입니다. 기존 항목에서 수정 요청을 만드세요."})
    if key is not None and existing is None:
        errors.append({"path": spec.key_field, "line": None, "message": "수정할 기존 지식을 찾을 수 없습니다."})
    _pin_meta(model, existing)
    new_issues = [i for i in integrity_issues(with_item(base, kind, model)) if i not in set(integrity_issues(base))]
    errors += [{"path": "", "line": None, "message": issue} for issue in new_issues]

    result["ok"] = not errors
    result["errors"] = errors
    result["yaml"] = normalized_yaml(model)
    result["data"] = to_jsonable_python(model_to_data(model))
    result["key"] = item_key
    return result


def issues_summary(errors: list[dict[str, Any]]) -> str:
    first = errors[0]
    where = f"{first['path']}: " if first["path"] else ""
    extra = f" 외 {len(errors) - 1}건" if len(errors) > 1 else ""
    return f"검증에 실패했습니다. {where}{first['message']}{extra}"


# ---- 파일 반영 ----


def _target_path(store: KnowledgeStore, kind: str, key: str) -> Path:
    root = ks.KNOWLEDGE_DIR.resolve()
    spec = KIND_SPECS[kind]
    relative = store.source_paths.get((kind, key))
    if relative is None:
        relative = GLOSSARY_FILE if kind == "glossary" else f"{spec.directory}/{key}.yaml"
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise KnowledgeError(422, "지식 파일 경로가 올바르지 않습니다.")
    return path


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _glossary_text(path: Path, model) -> str:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else []
    items = raw if isinstance(raw, list) else []
    replacement = model_to_data(model)
    index = next((i for i, item in enumerate(items) if isinstance(item, dict) and item.get("term") == model.term), None)
    if index is None:
        items.append(replacement)
    else:
        items[index] = replacement
    return dump_yaml(items)


def approved_model(kind: str, payload: str, *, author_name: str):
    """승인 시점의 메타(verified, 수정일, 담당자)를 채운 모델."""

    raw, errors = parse_yaml_mapping(payload)
    if raw is None:
        raise KnowledgeError(422, issues_summary(errors))
    model = KIND_SPECS[kind].model.model_validate(raw)
    model.status = "verified"
    model.updated = date.today()
    if not model.owner.strip():
        model.owner = author_name
    return model


def apply_item(kind: str, model, base: KnowledgeStore) -> Callable[[], None]:
    """모델을 YAML 로 쓰고 store 를 다시 읽는다. 돌려주는 함수를 호출하면 원상 복구한다."""

    key = getattr(model, KIND_SPECS[kind].key_field)
    path = _target_path(base, kind, key)
    previous = path.read_bytes() if path.exists() else None

    def undo() -> None:
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            _atomic_write(path, previous.decode("utf-8"))
        ks.reset_store()

    try:
        text = _glossary_text(path, model) if kind == "glossary" else normalized_yaml(model)
        _atomic_write(path, text)
        ks.reset_store()
        ks.get_store()
    except Exception:
        try:
            undo()
        finally:
            ks.reset_store()
        raise KnowledgeError(503, "승인한 변경을 반영하지 못했습니다. 지식 파일은 원래대로 유지됩니다.") from None
    return undo
