"""Shared logging for service-layer operation boundaries."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from time import monotonic
from typing import ParamSpec, TypeVar, cast


P = ParamSpec("P")
R = TypeVar("R")
_OPERATION_DEPTH: ContextVar[int] = ContextVar("service_operation_depth", default=0)


def _operation_name(function: Callable[..., object]) -> str:
    module = function.__module__.removeprefix("services.")
    return f"{module}.{function.__qualname__}"


def _log_failure(
    logger: logging.Logger,
    operation: str,
    started_at: float,
    error: Exception,
) -> None:
    duration_ms = round((monotonic() - started_at) * 1000, 2)
    expected = error.__class__.__module__.startswith("services.")
    logger.log(
        logging.WARNING if expected else logging.ERROR,
        "서비스 작업 실패: operation=%s duration_ms=%.2f error_type=%s",
        operation,
        duration_ms,
        type(error).__name__,
    )


def _log_completion(
    logger: logging.Logger,
    operation: str,
    started_at: float,
    result: object,
    *,
    nested: bool,
) -> None:
    business_error = isinstance(result, dict) and result.get("status") == "error"
    if nested:
        level = logging.DEBUG
    else:
        level = logging.WARNING if business_error else logging.INFO
    logger.log(
        level,
        "서비스 작업 업무 오류: operation=%s duration_ms=%.2f"
        if business_error
        else "서비스 작업 완료: operation=%s duration_ms=%.2f",
        operation,
        (monotonic() - started_at) * 1000,
    )


def logged_service_operation(function: Callable[P, R]) -> Callable[P, R]:
    """Log a service boundary without serializing arguments or return values.

    The outer operation is logged at INFO. Nested service calls stay available at
    DEBUG so a single request does not flood normal application logs.
    """

    logger = logging.getLogger("uvicorn.error").getChild(function.__module__)
    operation = _operation_name(function)

    if inspect.iscoroutinefunction(function):

        @wraps(function)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
            started_at = monotonic()
            depth = _OPERATION_DEPTH.get()
            token = _OPERATION_DEPTH.set(depth + 1)
            logger.log(
                logging.INFO if depth == 0 else logging.DEBUG,
                "서비스 작업 시작: operation=%s",
                operation,
            )
            try:
                result = await function(*args, **kwargs)
            except Exception as error:
                if depth == 0:
                    _log_failure(logger, operation, started_at, error)
                else:
                    logger.debug(
                        "중첩 서비스 작업 실패: operation=%s error_type=%s",
                        operation,
                        type(error).__name__,
                    )
                raise
            finally:
                _OPERATION_DEPTH.reset(token)
            _log_completion(logger, operation, started_at, result, nested=depth > 0)
            return result

        return cast(Callable[P, R], async_wrapper)

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        started_at = monotonic()
        depth = _OPERATION_DEPTH.get()
        token = _OPERATION_DEPTH.set(depth + 1)
        logger.log(
            logging.INFO if depth == 0 else logging.DEBUG,
            "서비스 작업 시작: operation=%s",
            operation,
        )
        try:
            result = function(*args, **kwargs)
        except Exception as error:
            if depth == 0:
                _log_failure(logger, operation, started_at, error)
            else:
                logger.debug(
                    "중첩 서비스 작업 실패: operation=%s error_type=%s",
                    operation,
                    type(error).__name__,
                )
            raise
        finally:
            _OPERATION_DEPTH.reset(token)
        _log_completion(logger, operation, started_at, result, nested=depth > 0)
        return result

    return cast(Callable[P, R], wrapper)
