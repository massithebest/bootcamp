"""Select mock or real service implementations."""

from core.config import SERVICE_MODE


if SERVICE_MODE == "real":
    from services.real import rag_service
    from services.real import simulation_service
    from services.real import sql_service
elif SERVICE_MODE == "mock":
    from services.mock import mock_rag_service as rag_service
    from services.mock import mock_simulation_service as simulation_service
    from services.mock import mock_sql_service as sql_service
else:  # pragma: no cover - core.config validates before this module loads
    raise RuntimeError(f"Unsupported SERVICE_MODE: {SERVICE_MODE!r}")
