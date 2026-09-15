# Backend Guidelines

## Closed-Network Requirement

The backend is ultimately deployed in a closed network without public internet access. Before changing dependencies, provider integrations, environment configuration, or deployment steps, read and follow the [closed-network setup and migration guide](docs/CLOSED_NETWORK_SETUP.md). Keep offline installation, internal endpoint substitution, and secret-handling requirements compatible with that guide.

## Architecture References

The implemented domain-knowledge architecture is documented in [the repository-level domain knowledge guide](../docs/domain-knowledge.md). Chart response v1 is documented in [the chart visualization guide](../docs/chart-visualization.md). `../docs/result-store.md` and chart v2 sections describe future work; do not present them as implemented behavior.

## Architecture & Directory Layout

The backend is a Python 3.11 FastAPI service. `main.py` creates the app; `api/routes_chat.py` streams chat events over SSE, `api/routes_knowledge.py` exposes read-only knowledge summaries, and `api/schemas.py` owns Pydantic API contracts. Agent orchestration belongs in `agent/`, SDK event translation in `agent/event_adapter.py`, conversation/session anchors in `agent/session_store.py`, tool input boundaries in `tools/`, configuration in `core/`, and external I/O in `services/`.

Structured domain knowledge under `knowledge/` is the source of truth for catalogs, joins, KPIs, recipes, simulations, glossary terms, and seed scenarios. Load and validate it through `services/knowledge_service.py`; the runtime agent accesses it only through the registered knowledge tools. `scripts/seed_sample_db.py` builds the untracked `data/sample.sqlite` used by mock SQL and simulation services. Query results are persisted by `services/result_store.py` and exposed through result summary/page tools; never expose internal parquet paths in tool payloads.

`services/chart_inference.py` implements the current v1 deterministic bar/line chart inference. Mock SQL and simulation services may attach an optional `chart` payload derived directly from returned rows. Keep chart inference independent of the LLM and keep unsupported shapes table-only.

Preserve these flows: route/controller -> agent -> SDK tool -> tool -> service -> database/external provider, and route/controller -> knowledge service for read-only inspector APIs. Do not put SQL, provider configuration, chart inference, or business logic in routes. This project has no separate repository/ORM layer; add one beneath `services/` if persistence grows complex. Keep mock and real service function signatures and result shapes identical. The real SQL, RAG, and simulation implementations remain closed-network migration stubs; do not remove the mock implementations.

## Development & Tooling Commands

Run commands from `backend/`:

```bash
conda env create -f environment.yml
conda activate production-planning
pip install -r requirements-dev.txt
cp .env.example .env
python -m scripts.seed_sample_db
PLANNING_AGENT_FAKE=1 uvicorn main:app --reload --port 8000
python -m pytest -q
python -m pytest -m e2e
```

The e2e suite requires working CLI/provider credentials. No migration, linter, formatter, or coverage command is currently configured; do not claim one in changes. Add its configuration and documentation before making it required.

## Coding & API Design Standards

Follow PEP 8, use explicit type hints, small async route handlers, and Pydantic models at API boundaries. Keep SDK-specific event translation in `agent/event_adapter.py`. Use appropriate HTTP status codes and FastAPI's `{"detail": ...}` error shape for non-streaming failures. Streaming failures must emit the stable `AgentEvent` shape (`error`, then `done`) without exception details. Coordinate event-contract changes with the frontend.

The stable event types are `text`, `status`, `tool_call`, `tool_result`, `error`, and `done`. A successful `done` event carries `data.turn_id`. `ChatRequest.fork_from_turn_id` lets frontend edit/reload actions fork a prior SDK transcript: `session_store.py` maps the public turn ID to the SDK session and last resumable assistant/user message UUID. Never use a `ResultMessage` UUID as `resume_session_at`. Preserve the distinction between an omitted fork ID (continue), an empty string (restart), and an unknown ID (emit an error and safely fall back).

`agent/sdk_tools.py::TOOL_NAMES` is the canonical registered-tool list. It currently covers SQL, RAG, simulation discovery/execution, table/KPI lookup, recipe lookup, and stored-result summary/page retrieval. When adding or renaming a tool, update its tool wrapper, runtime instructions, prompt-consistency tests, fake-runner coverage, and frontend tool-result metadata together.

Use catalog table/column names consistently. SQL execution is read-only and must pass `services/sql_guard.py`. Schema changes currently require updating catalog YAML, the seed script, and affected tests together; do not edit generated `data/sample.sqlite` as a migration.

Keep knowledge APIs read-only until the documented authoring workflow is implemented. `/api/knowledge/skills`, `/api/knowledge/catalog`, and `/api/knowledge/kpis` are inspector endpoints, not alternate sources of truth.

## Testing & Verification

Write pytest unit tests for tools, services, guards, knowledge integrity, chart inference, session anchors, and SDK adapters; use `TestClient` for API/SSE and knowledge endpoint integration tests. Prefer `monkeypatch`, the fake runner, and mock services over network calls. Regenerate the sample DB before scenario-dependent checks. Add e2e tests only for behavior that cannot be validated locally. Run the default suite before submitting; new or changed behavior must be covered, with no fixed percentage target currently enforced.

## Environment & Security Considerations

Read environment values only through `core/config.py`; add new keys, without secrets, to `.env.example`. Never commit `.env`, tokens, passwords, or internal URLs. Verify provider/auth tokens server-side, validate all external input with Pydantic and service guards, keep CORS origins explicit, and return sanitized client errors while logging details server-side.
