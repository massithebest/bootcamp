import asyncio
import logging

import pytest

from services.service_logging import logged_service_operation


def test_sync_service_operation_logs_start_and_completion_without_arguments(caplog):
    @logged_service_operation
    def operation(secret: str) -> str:
        return "ok"

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        assert operation("do-not-log") == "ok"

    messages = [record.getMessage() for record in caplog.records]
    assert any("서비스 작업 시작" in message for message in messages)
    assert any("서비스 작업 완료" in message for message in messages)
    assert all("do-not-log" not in message for message in messages)


def test_nested_service_operation_is_not_duplicated_at_info(caplog):
    @logged_service_operation
    def inner() -> None:
        return None

    @logged_service_operation
    def outer() -> None:
        inner()

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        outer()

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 2
    assert all("outer" in message for message in messages)
    assert all("inner" not in message for message in messages)


def test_error_result_is_logged_as_business_warning(caplog):
    @logged_service_operation
    def operation() -> dict:
        return {"status": "error", "message": "do-not-log"}

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        operation()

    warning = next(record for record in caplog.records if record.levelno == logging.WARNING)
    assert "서비스 작업 업무 오류" in warning.getMessage()
    assert "do-not-log" not in warning.getMessage()


def test_async_service_operation_logs_unexpected_failure_without_arguments(caplog):
    @logged_service_operation
    async def operation(secret: str) -> None:
        raise RuntimeError("internal detail")

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        with pytest.raises(RuntimeError, match="internal detail"):
            asyncio.run(operation("do-not-log"))

    messages = [record.getMessage() for record in caplog.records]
    failure = next(message for message in messages if "서비스 작업 실패" in message)
    assert "error_type=RuntimeError" in failure
    assert "internal detail" not in failure
    assert "do-not-log" not in failure
