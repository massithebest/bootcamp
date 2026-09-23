"""구조화 지식의 YAML 정규화 직렬화.

변경 요청의 초안·diff·승인 반영이 모두 같은 형식을 쓰도록 모델을 한 가지 모양으로
직렬화한다. 기본값은 생략하고, 관리 메타(active/status/owner/updated/source)는 항상
끝에 둔다. 주석과 flow 스타일은 보존되지 않는다.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import yaml
from pydantic import BaseModel

META_FIELDS = ("active", "status", "owner", "updated", "source")


class _Dumper(yaml.SafeDumper):
    """리스트를 들여쓰고 여러 줄 문자열(SQL 등)을 literal 블록으로 쓴다."""

    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


def _represent_str(dumper: yaml.SafeDumper, value: str):
    if "\n" in value and not any(line != line.rstrip() for line in value.split("\n")):
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_Dumper.add_representer(str, _represent_str)


def model_to_data(model: BaseModel) -> dict[str, Any]:
    """모델을 JSON 호환 dict 로 바꾼다. 기본값은 생략하고 관리 메타를 끝에 둔다."""

    body = model.model_dump(mode="json", exclude_defaults=True)
    full = model.model_dump(mode="json")
    meta: dict[str, Any] = {
        "active": full["active"],
        "status": full["status"],
        "owner": full["owner"],
    }
    if full["updated"]:
        meta["updated"] = full["updated"]
    meta["source"] = full["source"]
    return {**{key: value for key, value in body.items() if key not in META_FIELDS}, **meta}


def dump_yaml(data: dict[str, Any] | list[dict[str, Any]]) -> str:
    """`model_to_data` 결과(또는 그 목록)를 YAML 문자열로 쓴다."""

    def prepare(item: Any) -> Any:
        if isinstance(item, dict):
            prepared = {key: prepare(value) for key, value in item.items()}
            updated = prepared.get("updated")
            if isinstance(updated, str):
                try:
                    prepared["updated"] = date.fromisoformat(updated)
                except ValueError:
                    pass
            return prepared
        if isinstance(item, list):
            return [prepare(value) for value in item]
        return item

    return yaml.dump(
        prepare(data),
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10_000,
    )


def parse_yaml_mapping(text: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """YAML 문자열을 mapping 으로 읽는다. 실패하면 `[{path, line, message}]`를 돌려준다."""

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        problem = getattr(exc, "problem", None) or "YAML 문법 오류"
        return None, [
            {"path": "", "line": mark.line + 1 if mark else None, "message": f"YAML 문법 오류: {problem}"}
        ]
    if not isinstance(raw, dict):
        return None, [{"path": "", "line": None, "message": "최상위는 key: value 형태여야 합니다."}]
    return raw, []
