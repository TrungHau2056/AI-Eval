from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

from src.config import settings

logger = logging.getLogger(__name__)


class NoopObservation:
    id: str = ""
    trace_id: str = ""

    def update(self, **_: Any) -> None:
        return None


def langfuse_enabled() -> bool:
    return bool(settings.langfuse_public_key and settings.langfuse_secret_key)


def capture_io_enabled() -> bool:
    return bool(settings.langfuse_capture_io)


def _ensure_env_for_sdk() -> None:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)


@contextmanager
def langfuse_observation(
    name: str,
    *,
    as_type: str = "span",
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    model: str | None = None,
    trace_id: str | None = None,
    parent_span_id: str | None = None,
) -> Iterator[Any]:
    if not langfuse_enabled():
        yield NoopObservation()
        return

    try:
        _ensure_env_for_sdk()
        from langfuse import get_client

        langfuse = get_client()
        kwargs: dict[str, Any] = {
            "as_type": as_type,
            "name": name,
        }
        if input is not None:
            kwargs["input"] = input
        if metadata:
            kwargs["metadata"] = metadata
        if model:
            kwargs["model"] = model
        trace_context: dict[str, Any] = {}
        if trace_id:
            trace_context["trace_id"] = trace_id
        if parent_span_id:
            trace_context["parent_span_id"] = parent_span_id
        if trace_context:
            kwargs["trace_context"] = trace_context

        observation = langfuse.start_as_current_observation(**kwargs)
    except Exception:
        logger.exception("Langfuse observation failed; continuing without tracing")
        yield NoopObservation()
        return

    with observation as obs:
        yield obs


def flush_langfuse() -> None:
    if not langfuse_enabled():
        return

    try:
        _ensure_env_for_sdk()
        from langfuse import get_client

        get_client().flush()
    except Exception:
        logger.exception("Failed to flush Langfuse events")
