"""Read-only projection of YAML and versioned text knowledge for the UI."""
from services.knowledge_service import get_store
from services.document_store import get_document_store, normalize
from services.service_logging import logged_service_operation


@logged_service_operation
def entries(query: str = "", kind: str | None = None) -> list[dict]:
    store = get_store()
    items = []
    groups = {
        "table": store.tables, "kpi": store.kpis, "recipe": store.recipes,
        "simulation": store.simulations,
        "glossary": {item.term: item for item in store.glossary},
    }
    for category, mapping in groups.items():
        for key, model in mapping.items():
            data = model.model_dump(mode="json")
            items.append({"type": category, "id": key,
                "title": data.get("name", data.get("term", key)),
                "summary": data.get("description", data.get("definition", "")),
                "status": data["status"], "source": data["source"], "owner": data["owner"],
                "updated": str(data["updated"] or ""), "active": data["active"], "archived": False,
                "detail": data})
    for doc in get_document_store().list():
        latest = doc["versions"][0]
        items.append({"type": "document", "id": doc["id"], "title": latest["title"],
            "summary": latest["content"][:200], "status": latest["status"],
            "source": latest["source"], "owner": latest["owner"], "updated": latest["created_at"],
            "active": doc["active_version"] is not None, "archived": doc["archived"],
            "detail": latest})
    needle = normalize(query)
    return [item for item in items if (not kind or item["type"] == kind) and
            (not needle or needle in normalize(str(item)))]
