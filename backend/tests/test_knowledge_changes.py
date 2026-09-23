"""구조화 지식 변경 요청: 초안 → 제출 → 승인 → YAML 반영.

임시 `KNOWLEDGE_DIR` 만 쓰며 번들 YAML 은 수정하지 않는다.
"""

import json
import logging
from textwrap import dedent

import pytest
import yaml
from fastapi.testclient import TestClient

from core import config
from main import app
from services.knowledge import catalog as knowledge_service, writer as knowledge_writer
from services.knowledge.guides import guide
from services.knowledge.catalog import KnowledgeStore, get_store, reset_store

WIP = """
    table: wip
    description: 초기 재공
    grain: [dataset, lot]
    columns:
      - {name: dataset, type: varchar, desc: 구분}
      - {name: lot, type: varchar, desc: Lot ID}
      - {name: part, type: varchar, desc: Part ID, ref: part.part}
    joins:
      - {to: part, on: [dataset, part], kind: many-to-one}
    query_rules: [dataset 을 반드시 제한한다]
    visualization_hints: [bar 차트가 적합하다]
    sample_queries:
      - question: Lot 수는?
        sql: SELECT COUNT(*) FROM wip
    active: true
    status: verified
    owner: 관리팀
    source: 테스트
"""
PART = """
    table: part
    description: 제품
    grain: [dataset, part]
    columns:
      - {name: dataset, type: varchar}
      - {name: part, type: varchar}
    query_rules: [dataset 을 반드시 제한한다]
    visualization_hints: [표가 적합하다]
    status: verified
"""
KPI = """
    kpi_id: initial_wip
    name: 초기 WIP
    definition: 초기 재공 수
    formula: COUNT(lot)
    sources: [wip]
    grain: [dataset]
    baseline: 없음
    shortfall_rule: 없음
    sql_template: SELECT COUNT(*) FROM wip
    status: verified
"""
GLOSSARY = """
    - term: WIP
      definition: 재공
      status: verified
    - term: Lot
      definition: 생산 단위
      status: verified
"""


def _write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8")


@pytest.fixture
def knowledge(tmp_path, monkeypatch):
    root = tmp_path / "knowledge"
    _write(root, "catalog/tables/wip.yaml", WIP)
    _write(root, "catalog/tables/part.yaml", PART)
    _write(root, "kpi/initial_wip.yaml", KPI)
    _write(root, "glossary.yaml", GLOSSARY)
    monkeypatch.setattr(knowledge_service, "KNOWLEDGE_DIR", root)
    monkeypatch.setattr(config, "KNOWLEDGE_DB_PATH", tmp_path / "knowledge.sqlite3")
    monkeypatch.setattr(config, "KNOWLEDGE_ALLOW_SELF_APPROVAL", False)
    monkeypatch.setattr(config, "KNOWLEDGE_MANAGEMENT_ENABLED", True)
    reset_store()
    yield root
    reset_store()


@pytest.fixture
def client(knowledge):
    return TestClient(app)


USER = {"X-User-Id": "user"}
OTHER = {"X-User-Id": "other"}
ADMIN = {"X-User-Id": "admin"}


@pytest.fixture(autouse=True)
def principals(monkeypatch):
    monkeypatch.setattr(config, "KNOWLEDGE_PRINCIPALS", {
        "user": {"name": "사용자", "permissions": ["knowledge:write"]},
        "other": {"name": "다른 사용자", "permissions": ["knowledge:write"]},
        "admin": {"name": "관리자", "permissions": ["knowledge:write", "knowledge:approve"]},
        "viewer": {"name": "조회자", "permissions": []},
    })
    monkeypatch.setattr(config, "KNOWLEDGE_DEFAULT_PRINCIPAL", "user")


def source(client, kind, key):
    response = client.get(f"/api/knowledge/source/{kind}/{key}")
    assert response.status_code == 200
    return response.json()


def create(client, kind, key, mutate, headers=USER):
    data = source(client, kind, key)["data"]
    mutate(data)
    response = client.post("/api/knowledge/changes", json={"kind": kind, "key": key, "data": data}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def act(client, change, action, headers, note="확인"):
    return client.post(
        f"/api/knowledge/changes/{change['id']}/{action}",
        json={"expected_revision": change["revision"], "note": note},
        headers=headers,
    )


def submitted(client, kind="table", key="wip", description="수정한 설명"):
    change = create(client, kind, key, lambda d: d.update(description=description) if "description" in d else d.update(definition=description))
    response = act(client, change, "submit", USER)
    assert response.status_code == 200, response.text
    return response.json()


# ---- principal ----


def test_me_reports_principal_and_stub_users(client):
    body = client.get("/api/me").json()
    assert body["id"] == "user" and body["mode"] == "stub"
    assert body["permissions"] == ["knowledge:write"] and body["knowledge_management"] is True
    assert body["allow_self_approval"] is False
    assert {u["id"] for u in body["stub_users"]} == {"user", "other", "admin", "viewer"}
    assert "knowledge:approve" in client.get("/api/me", headers=ADMIN).json()["permissions"]


def test_unknown_user_is_rejected(client):
    assert client.get("/api/me", headers={"X-User-Id": "ghost"}).status_code == 403


def test_permissions_are_enforced(client):
    data = source(client, "table", "wip")["data"]
    body = {"kind": "table", "key": "wip", "data": data}
    assert client.post("/api/knowledge/changes", json=body, headers={"X-User-Id": "viewer"}).status_code == 403
    change = submitted(client)
    assert act(client, change, "approve", USER).status_code == 403
    assert act(client, change, "reject", USER).status_code == 403


def test_management_switch_blocks_writes_but_not_reads(client, monkeypatch):
    monkeypatch.setattr(config, "KNOWLEDGE_MANAGEMENT_ENABLED", False)
    data = source(client, "table", "wip")["data"]
    response = client.post("/api/knowledge/changes", json={"kind": "table", "key": "wip", "data": data}, headers=USER)
    assert response.status_code == 403
    assert client.get("/api/knowledge/changes").status_code == 200
    assert client.get("/api/me").json()["knowledge_management"] is False


# ---- 전체 흐름 ----


def test_approval_writes_yaml_and_applies_to_runtime(client, knowledge):
    change = submitted(client, description="승인 후 설명")
    assert change["state"] == "submitted"
    assert get_store().describe_table("wip")["description"] == "초기 재공"  # 승인 전에는 그대로

    approved = act(client, change, "approve", ADMIN)
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["state"] == "approved"
    assert [h["action"] for h in body["history"]] == ["approve", "submit", "create"]

    written = yaml.safe_load((knowledge / "catalog/tables/wip.yaml").read_text(encoding="utf-8"))
    assert written["description"] == "승인 후 설명" and written["status"] == "verified"
    assert str(written["updated"]) != "None"
    assert get_store().describe_table("wip")["description"] == "승인 후 설명"
    assert "wip" in get_store().table_names()


def test_author_cannot_smuggle_verified_status(client):
    yaml_text = dedent("""
        table: orders
        description: 주문
        grain: [order_id]
        columns:
          - {name: order_id, type: varchar}
        query_rules: [기간 조건을 건다]
        visualization_hints: [표]
        status: verified
    """)
    response = client.post("/api/knowledge/changes", json={"kind": "table", "yaml": yaml_text}, headers=USER)
    assert response.status_code == 201
    assert yaml.safe_load(response.json()["yaml"])["status"] == "draft"


def test_new_item_creates_file_and_appears_in_store(client, knowledge):
    yaml_text = dedent("""
        table: orders
        description: 주문
        grain: [order_id]
        columns:
          - {name: order_id, type: varchar}
        query_rules: [기간 조건을 건다]
        visualization_hints: [표]
    """)
    created = client.post("/api/knowledge/changes", json={"kind": "table", "yaml": yaml_text}, headers=USER).json()
    assert created["is_new"] is True
    change = act(client, created, "submit", USER).json()
    assert act(client, change, "approve", ADMIN).status_code == 200
    assert (knowledge / "catalog/tables/orders.yaml").is_file()
    assert "orders" in get_store().tables and get_store().tables["orders"].status == "verified"


def test_creating_an_existing_key_as_new_is_rejected(client):
    data = source(client, "table", "wip")["data"]
    response = client.post("/api/knowledge/changes", json={"kind": "table", "data": data}, headers=USER)
    assert response.status_code == 409


def test_only_one_open_change_per_item(client):
    create(client, "table", "wip", lambda d: d.update(description="가"))
    data = source(client, "table", "wip")["data"]
    response = client.post("/api/knowledge/changes", json={"kind": "table", "key": "wip", "data": data}, headers=OTHER)
    assert response.status_code == 409


def test_entries_show_pending_change_and_scenarios(client, knowledge):
    change = create(client, "table", "wip", lambda d: d.update(description="가"))
    rows = client.get("/api/knowledge/entries").json()
    wip = next(row for row in rows if row["type"] == "table" and row["id"] == "wip")
    assert wip["pending_change"] == {"id": change["id"], "state": "draft"}
    _write(knowledge, "scenarios/s1.yaml", """
        scenario_id: s1
        name: 시나리오
        description: 설명
        dataset: D
        question: 질문
        steps: []
        expected: {}
    """)
    reset_store()
    assert any(row["type"] == "scenario" and row["id"] == "s1" for row in client.get("/api/knowledge/entries").json())


# ---- 권한·동시성 규칙 ----


def test_only_author_can_edit_submit_and_withdraw(client):
    change = create(client, "table", "wip", lambda d: d.update(description="가"))
    data = source(client, "table", "wip")["data"]
    update = client.put(f"/api/knowledge/changes/{change['id']}",
                        json={"expected_revision": change["revision"], "data": data}, headers=OTHER)
    assert update.status_code == 403
    assert act(client, change, "submit", OTHER).status_code == 403
    assert act(client, change, "withdraw", OTHER).status_code == 403


def test_stale_revision_conflicts(client):
    change = create(client, "table", "wip", lambda d: d.update(description="가"))
    data = source(client, "table", "wip")["data"]
    data["description"] = "나"
    first = client.put(f"/api/knowledge/changes/{change['id']}",
                       json={"expected_revision": change["revision"], "data": data}, headers=USER)
    assert first.status_code == 200
    stale = client.put(f"/api/knowledge/changes/{change['id']}",
                       json={"expected_revision": change["revision"], "data": data}, headers=USER)
    assert stale.status_code == 409


def test_self_approval_is_blocked_by_default_and_allowed_by_setting(client, monkeypatch):
    monkeypatch.setitem(config.KNOWLEDGE_PRINCIPALS, "solo", {"name": "혼자", "permissions": ["knowledge:write", "knowledge:approve"]})
    solo = {"X-User-Id": "solo"}
    change = create(client, "table", "wip", lambda d: d.update(description="가"), headers=solo)
    change = act(client, change, "submit", solo).json()
    assert act(client, change, "approve", solo).status_code == 403

    monkeypatch.setattr(config, "KNOWLEDGE_ALLOW_SELF_APPROVAL", True)
    body = act(client, change, "approve", solo).json()
    assert body["state"] == "approved" and body["history"][0]["self_approved"] is True


def test_approve_and_reject_require_a_note(client):
    change = submitted(client)
    assert act(client, change, "approve", ADMIN, note="").status_code == 422
    assert act(client, change, "reject", ADMIN, note="").status_code == 422


def test_reject_then_revise_resubmit_and_withdraw(client):
    change = submitted(client)
    rejected = act(client, change, "reject", ADMIN, note="근거 부족").json()
    assert rejected["state"] == "rejected"
    data = source(client, "table", "wip")["data"]
    data["description"] = "보완한 설명"
    revised = client.put(f"/api/knowledge/changes/{rejected['id']}",
                         json={"expected_revision": rejected["revision"], "data": data}, headers=USER).json()
    assert revised["state"] == "draft"
    resubmitted = act(client, revised, "submit", USER).json()
    assert resubmitted["state"] == "submitted"
    withdrawn = act(client, resubmitted, "withdraw", USER).json()
    assert withdrawn["state"] == "withdrawn"
    assert act(client, withdrawn, "approve", ADMIN).status_code == 409


# ---- 검증·정합성 ----


def test_validate_reports_field_paths(client):
    response = client.post("/api/knowledge/validate", json={"kind": "table", "yaml": "table: x\nfoo: 1\n"}, headers=USER).json()
    paths = {error["path"] for error in response["errors"]}
    assert response["ok"] is False and response["parsed"] is True and {"foo", "description", "columns"} <= paths
    broken = client.post("/api/knowledge/validate", json={"kind": "table", "yaml": "table: [\n"}, headers=USER).json()
    assert broken["ok"] is False and broken["parsed"] is False and broken["errors"][0]["line"] is not None


def test_validate_returns_yaml_for_an_incomplete_form(client):
    response = client.post("/api/knowledge/validate", json={"kind": "table", "data": {"table": "x"}}, headers=USER).json()
    assert response["ok"] is False and response["parsed"] is True
    assert yaml.safe_load(response["yaml"]) == {"table": "x"}


def test_unparseable_yaml_cannot_be_saved(client):
    response = client.post("/api/knowledge/changes", json={"kind": "table", "yaml": "table: [\n"}, headers=USER)
    assert response.status_code == 422


def test_invalid_draft_can_be_saved_but_not_submitted(client):
    change = create(client, "table", "wip", lambda d: d.update(description=""))
    response = act(client, change, "submit", USER)
    assert response.status_code == 422 and "설명" in response.json()["detail"]


def test_integrity_gate_blocks_new_broken_references(client):
    yaml_text = dedent("""
        kpi_id: bad_kpi
        name: 잘못된 KPI
        definition: 정의
        formula: 산식
        sources: [missing_table]
        grain: [dataset]
        baseline: 없음
        shortfall_rule: 없음
        sql_template: SELECT 1 FROM missing_table
    """)
    created = client.post("/api/knowledge/changes", json={"kind": "kpi", "yaml": yaml_text}, headers=USER).json()
    response = act(client, created, "submit", USER)
    assert response.status_code == 422 and "missing_table" in response.json()["detail"]


def test_preexisting_integrity_problems_do_not_block_unrelated_changes(client, knowledge):
    _write(knowledge, "kpi/legacy.yaml", KPI.replace("initial_wip", "legacy").replace("[wip]", "[gone]").replace("FROM wip", "FROM gone"))
    reset_store()
    change = submitted(client, description="관련 없는 수정")
    assert act(client, change, "approve", ADMIN).status_code == 200


def test_deactivation_removes_item_from_runtime(client):
    change = create(client, "table", "part", lambda d: d.update(active=False))
    change = act(client, change, "submit", USER).json()
    assert act(client, change, "approve", ADMIN).status_code == 200
    assert "part" not in get_store().table_names()
    assert get_store().describe_table("part")["status"] == "error"


# ---- 파일 반영 안전성 ----


@pytest.mark.parametrize("key", ["../evil", "a/b", ".hidden", "a b", ""])
def test_unsafe_keys_are_rejected(client, knowledge, key):
    yaml_text = f"kpi_id: {json.dumps(key)}\nname: n\ndefinition: d\nformula: f\nsources: [wip]\ngrain: [x]\nbaseline: b\nshortfall_rule: s\nsql_template: SELECT 1 FROM wip\n"
    response = client.post("/api/knowledge/changes", json={"kind": "kpi", "yaml": yaml_text}, headers=USER)
    assert response.status_code == 422
    assert "YAML 문법" not in response.json()["detail"]  # 키 검증에서 막혀야 한다
    assert not list(knowledge.parent.glob("evil*"))


def test_existing_file_with_different_name_is_overwritten_in_place(client, knowledge):
    (knowledge / "catalog/tables/part.yaml").rename(knowledge / "catalog/tables/legacy_part_file.yaml")
    reset_store()
    change = submitted(client, key="part", description="이름이 다른 파일")
    assert act(client, change, "approve", ADMIN).status_code == 200
    assert not (knowledge / "catalog/tables/part.yaml").exists()
    text = (knowledge / "catalog/tables/legacy_part_file.yaml").read_text(encoding="utf-8")
    assert "이름이 다른 파일" in text


def test_glossary_entry_is_replaced_without_touching_others(client, knowledge):
    change = create(client, "glossary", "WIP", lambda d: d.update(definition="새 정의"))
    change = act(client, change, "submit", USER).json()
    assert act(client, change, "approve", ADMIN).status_code == 200
    entries = yaml.safe_load((knowledge / "glossary.yaml").read_text(encoding="utf-8"))
    by_term = {entry["term"]: entry for entry in entries}
    assert by_term["WIP"]["definition"] == "새 정의" and by_term["Lot"]["definition"] == "생산 단위"

    created = client.post("/api/knowledge/changes", json={"kind": "glossary", "data": {"term": "Route", "definition": "경로"}}, headers=USER).json()
    created = act(client, created, "submit", USER).json()
    assert act(client, created, "approve", ADMIN).status_code == 200
    assert [entry["term"] for entry in yaml.safe_load((knowledge / "glossary.yaml").read_text(encoding="utf-8"))] == ["WIP", "Lot", "Route"]


def test_join_on_key_round_trips(client, knowledge):
    change = submitted(client, description="조인 유지")
    assert act(client, change, "approve", ADMIN).status_code == 200
    reloaded = KnowledgeStore.load(knowledge)
    assert reloaded.tables["wip"].joins[0].on == ["dataset", "part"]


def test_stale_base_blocks_approval_and_keeps_file(client, knowledge):
    change = submitted(client, description="내 수정")
    path = knowledge / "catalog/tables/wip.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("초기 재공", "다른 경로로 바뀐 설명"), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    response = act(client, change, "approve", ADMIN)
    assert response.status_code == 409
    assert path.read_text(encoding="utf-8") == before


def test_reload_failure_restores_file_and_keeps_request_submitted(client, knowledge, monkeypatch):
    change = submitted(client, description="반영 실패")
    path = knowledge / "catalog/tables/wip.yaml"
    before = path.read_text(encoding="utf-8")
    real_get_store = knowledge_service.get_store
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("reload failed")
        return real_get_store()

    monkeypatch.setattr(knowledge_writer.ks, "get_store", flaky)
    response = act(client, change, "approve", ADMIN)
    assert response.status_code == 503 and str(knowledge) not in response.text
    assert path.read_text(encoding="utf-8") == before
    assert client.get(f"/api/knowledge/changes/{change['id']}").json()["state"] == "submitted"


def test_new_file_is_removed_when_reload_fails(client, knowledge, monkeypatch):
    yaml_text = "table: fresh\ndescription: d\ngrain: [a]\ncolumns:\n  - {name: a, type: varchar}\nquery_rules: [r]\nvisualization_hints: [v]\n"
    created = client.post("/api/knowledge/changes", json={"kind": "table", "yaml": yaml_text}, headers=USER).json()
    created = act(client, created, "submit", USER).json()
    real = knowledge_service.get_store
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("boom")
        return real()

    monkeypatch.setattr(knowledge_writer.ks, "get_store", flaky)
    assert act(client, created, "approve", ADMIN).status_code == 503
    assert not (knowledge / "catalog/tables/fresh.yaml").exists()


# ---- 가이드·직렬화·로깅 ----


@pytest.mark.parametrize("kind", ["table", "kpi", "recipe", "simulation", "glossary", "scenario"])
def test_guide_lists_key_first_and_meta_last(kind):
    fields = guide(kind)["fields"]
    names = [field["name"] for field in fields]
    assert names[0] == guide(kind)["key_field"]
    assert names[-5:] == ["active", "status", "owner", "updated", "source"]
    assert all(field["label"] for field in fields)
    lists = {f["name"]: f["item_widget"] for f in fields if f["widget"] == "string_list"}
    assert set(lists.values()) <= {"string", "text"}
    assert {field["name"] for field in fields if field["readonly"]} == {"status", "updated"}


def test_guide_endpoint_and_template(client):
    body = client.get("/api/knowledge/guides/table").json()
    assert body["key_field"] == "table" and body["template"]["active"] is True
    assert client.get("/api/knowledge/guides/unknown").status_code == 422


def test_normalized_yaml_round_trips_every_bundled_item():
    store = KnowledgeStore.load(config.DEFAULT_KNOWLEDGE_DIR)
    for kind, spec in knowledge_service.KIND_SPECS.items():
        items = store.glossary if kind == "glossary" else list(getattr(store, spec.attribute).values())
        for item in items:
            text = knowledge_writer.normalized_yaml(item)
            assert spec.model.model_validate(yaml.safe_load(text)) == item


def test_source_paths_are_recorded(knowledge):
    store = KnowledgeStore.load(knowledge)
    assert store.source_paths[("table", "wip")] == "catalog/tables/wip.yaml"
    assert store.source_paths[("glossary", "WIP")] == "glossary.yaml"


def test_logs_do_not_contain_knowledge_bodies(client, caplog):
    secret = "로그에_남으면_안되는_설명"
    with caplog.at_level(logging.DEBUG, logger="uvicorn.error"):
        change = submitted(client, description=secret)
        act(client, change, "approve", ADMIN)
    assert secret not in caplog.text
    assert "services.knowledge.changes" in caplog.text
