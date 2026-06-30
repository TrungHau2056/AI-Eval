from __future__ import annotations

import json
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

import httpx

from src.config import ENV_FILES, settings

logger = logging.getLogger(__name__)
APIFY_RUN_URL = "https://api.apify.com/v2/actor-runs/{run_id}"

_operation: ContextVar[str] = ContextVar("cost_operation", default="unknown")


@contextmanager
def cost_operation(name: str) -> Iterator[None]:
    token = _operation.set(name or "unknown")
    try:
        yield
    finally:
        _operation.reset(token)


def current_operation() -> str:
    return _operation.get()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_state():
    from src.api.deps import get_state

    return get_state()


def start_or_get_run() -> str:
    state = _get_state()
    if not state.cost_run_id or state.cost_run_closed:
        state.cost_run_id = uuid.uuid4().hex
        state.cost_run_closed = False
        logger.info("COST_RUN_START run_id=%s", state.cost_run_id)
    return state.cost_run_id


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _nested(obj: Any, key: str, nested_key: str, default: Any = None) -> Any:
    return _value(_value(obj, key), nested_key, default)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.0000000001")))


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _brace_balance(value: str) -> int:
    return value.count("{") - value.count("}")


def _env_file_pricing_json() -> str | None:
    for env_file in reversed(ENV_FILES):
        path = Path(env_file)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, raw_value = stripped.split("=", 1)
            if name.strip() != "OPENAI_PRICING_JSON":
                continue

            raw_value = raw_value.strip()
            if not raw_value:
                return None
            if _brace_balance(raw_value) <= 0:
                return _strip_wrapping_quotes(raw_value)

            collected = [raw_value]
            balance = _brace_balance(raw_value)
            for continuation in lines[index + 1 :]:
                segment = continuation.strip()
                collected.append(segment)
                balance += _brace_balance(segment)
                if balance <= 0:
                    break
            return _strip_wrapping_quotes("\n".join(collected))
    return None


def _env_file_value(name: str) -> str:
    for env_file in reversed(ENV_FILES):
        path = Path(env_file)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw_value = stripped.split("=", 1)
            if key.strip() == name:
                return _strip_wrapping_quotes(raw_value.strip())
    return ""


def _pricing_catalog() -> dict[str, Any]:
    env_file_raw = _env_file_pricing_json()
    candidates = [raw for raw in (env_file_raw, settings.openai_pricing_json) if raw]

    for raw in candidates:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed:
            if raw == env_file_raw and raw != settings.openai_pricing_json:
                logger.info("Loaded OPENAI_PRICING_JSON directly from env file")
            return parsed

    raw = settings.openai_pricing_json or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        if env_file_raw and env_file_raw != raw:
            try:
                parsed = json.loads(env_file_raw)
                logger.info("Loaded OPENAI_PRICING_JSON from multiline env block")
            except json.JSONDecodeError:
                logger.warning("Invalid OPENAI_PRICING_JSON; OpenAI cost will be price_missing")
                return {}
        else:
            logger.warning("Invalid OPENAI_PRICING_JSON; OpenAI cost will be price_missing")
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _pricing_for_model(model: str) -> tuple[str | None, dict[str, Any] | None]:
    catalog = _pricing_catalog()
    if not model or not catalog:
        return None, None

    model_lower = model.lower()
    by_lower = {str(k).lower(): (str(k), v) for k, v in catalog.items()}
    exact = by_lower.get(model_lower)
    if exact and isinstance(exact[1], dict):
        return exact

    matches: list[tuple[int, str, dict[str, Any]]] = []
    for key, value in catalog.items():
        key_str = str(key)
        key_lower = key_str.lower()
        if not model_lower.startswith(f"{key_lower}-"):
            continue
        suffix = model_lower.removeprefix(key_lower)
        is_dated_snapshot = suffix.startswith("-") and suffix[1:5].isdigit()
        if isinstance(value, dict) and is_dated_snapshot:
            matches.append((len(key_lower), key_str, value))
    if not matches:
        return None, None
    _, key, value = sorted(matches, reverse=True)[0]
    return key, value


def _rate(pricing: dict[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        rate = _decimal(pricing.get(key))
        if rate is not None and rate > 0:
            return rate
    return None


def _calculate_openai_estimate(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: int,
) -> tuple[str, float | None, str | None, Decimal | None, Decimal | None, Decimal | None]:
    matched_model, pricing = _pricing_for_model(model)
    if pricing is None:
        return "price_missing", None, matched_model, None, None, None

    input_rate = _rate(pricing, "input_per_1m", "input", "input_usd_per_1m")
    output_rate = _rate(pricing, "output_per_1m", "output", "output_usd_per_1m")
    cached_rate = _rate(pricing, "cached_input_per_1m", "cached_input", "cached_usd_per_1m")
    if input_rate is None or output_rate is None:
        return "price_missing", None, matched_model, input_rate, output_rate, cached_rate

    billed_input_tokens = max(prompt_tokens - cached_tokens, 0) if cached_rate is not None else prompt_tokens
    cost = (Decimal(billed_input_tokens) / Decimal(1_000_000)) * input_rate
    cost += (Decimal(completion_tokens) / Decimal(1_000_000)) * output_rate
    if cached_rate is not None:
        cost += (Decimal(cached_tokens) / Decimal(1_000_000)) * cached_rate
    return "estimated", _float(cost), matched_model, input_rate, output_rate, cached_rate


def _append_event(event: dict[str, Any]) -> dict[str, Any]:
    state = _get_state()
    state.cost_events.append(event)
    state.cost_summary = summarize_run(event["run_id"])
    return event


def record_openai_usage(
    *,
    model: str,
    usage: Any,
    operation: str | None = None,
) -> dict[str, Any]:
    run_id = start_or_get_run()
    prompt_tokens = _int(_value(usage, "prompt_tokens"))
    completion_tokens = _int(_value(usage, "completion_tokens"))
    total_tokens = _int(_value(usage, "total_tokens"), prompt_tokens + completion_tokens)
    cached_tokens = _int(_nested(usage, "prompt_tokens_details", "cached_tokens"))

    status = "estimated"
    cost_usd: float | None = None
    matched_model = None
    input_rate = output_rate = cached_rate = None
    pricing_metadata: dict[str, Any] = {}

    if usage is None:
        status = "missing_usage"
    else:
        status, cost_usd, matched_model, input_rate, output_rate, cached_rate = _calculate_openai_estimate(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=cached_tokens,
        )
        if matched_model:
            _, pricing = _pricing_for_model(model)
            pricing_metadata = pricing if isinstance(pricing, dict) else {}

    event = {
        "id": uuid.uuid4().hex[:12],
        "run_id": run_id,
        "provider": "openai",
        "operation": operation or current_operation(),
        "timestamp": _now(),
        "status": status,
        "estimated": True,
        "currency": "USD",
        "cost_usd": cost_usd,
        "model": model,
        "matched_pricing_model": matched_model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
        "pricing": {
            "input_per_1m": _float(input_rate),
            "output_per_1m": _float(output_rate),
            "cached_input_per_1m": _float(cached_rate),
            "source_url": pricing_metadata.get("source_url"),
            "checked_at": pricing_metadata.get("checked_at"),
        },
    }
    _append_event(event)
    if status == "price_missing":
        logger.warning(
            "COST_OPENAI_PRICE_MISSING run_id=%s operation=%s model=%s "
            "prompt_tokens=%d completion_tokens=%d configure=OPENAI_PRICING_JSON",
            run_id,
            event["operation"],
            model,
            prompt_tokens,
            completion_tokens,
        )
    elif status == "missing_usage":
        logger.warning(
            "COST_OPENAI_USAGE_MISSING run_id=%s operation=%s model=%s",
            run_id,
            event["operation"],
            model,
        )
    logger.info(
        "COST_OPENAI run_id=%s operation=%s model=%s matched_pricing_model=%s "
        "prompt_tokens=%d completion_tokens=%d total_tokens=%d status=%s estimated_usd=%s",
        run_id,
        event["operation"],
        model,
        matched_model or "",
        prompt_tokens,
        completion_tokens,
        total_tokens,
        status,
        cost_usd if cost_usd is not None else "null",
    )
    return event


def _reprice_openai_events(events: list[dict[str, Any]]) -> None:
    for event in events:
        if event.get("provider") != "openai":
            continue
        if event.get("cost_usd") is not None or event.get("status") != "price_missing":
            continue

        status, cost_usd, matched_model, input_rate, output_rate, cached_rate = _calculate_openai_estimate(
            model=str(event.get("model") or ""),
            prompt_tokens=_int(event.get("prompt_tokens")),
            completion_tokens=_int(event.get("completion_tokens")),
            cached_tokens=_int(event.get("cached_tokens")),
        )
        if status != "estimated":
            continue

        event["status"] = "estimated"
        event["cost_usd"] = cost_usd
        event["matched_pricing_model"] = matched_model
        event["repriced"] = True
        _, pricing_metadata = _pricing_for_model(str(event.get("model") or ""))
        pricing_metadata = pricing_metadata if isinstance(pricing_metadata, dict) else {}
        event["pricing"] = {
            **(event.get("pricing") if isinstance(event.get("pricing"), dict) else {}),
            "input_per_1m": _float(input_rate),
            "output_per_1m": _float(output_rate),
            "cached_input_per_1m": _float(cached_rate),
            "source_url": pricing_metadata.get("source_url"),
            "checked_at": pricing_metadata.get("checked_at"),
        }
        logger.info(
            "COST_OPENAI_REPRICED run_id=%s operation=%s model=%s matched_pricing_model=%s estimated_usd=%s",
            event.get("run_id"),
            event.get("operation"),
            event.get("model"),
            matched_model or "",
            cost_usd,
        )


def record_apify_usage(
    *,
    actor_id: str,
    run_id: str,
    metadata: dict[str, Any],
    item_count: int,
    operation: str | None = None,
) -> dict[str, Any]:
    cost = _decimal(metadata.get("usageTotalUsd"))
    event = {
        "id": uuid.uuid4().hex[:12],
        "run_id": start_or_get_run(),
        "provider": "apify",
        "operation": operation or current_operation(),
        "timestamp": _now(),
        "status": "actual" if cost is not None else "missing_cost",
        "estimated": False,
        "currency": "USD",
        "cost_usd": _float(cost),
        "actor_id": actor_id,
        "apify_run_id": run_id,
        "dataset_id": metadata.get("defaultDatasetId"),
        "actor_status": metadata.get("status"),
        "usage_usd": metadata.get("usageUsd") if isinstance(metadata.get("usageUsd"), dict) else {},
        "usage": metadata.get("usage") if isinstance(metadata.get("usage"), dict) else {},
        "pricing_info": metadata.get("pricingInfo") if isinstance(metadata.get("pricingInfo"), dict) else {},
        "item_count": item_count,
    }
    _append_event(event)
    logger.info(
        "COST_APIFY run_id=%s operation=%s actor=%s apify_run_id=%s status=%s items=%d actual_usd=%s",
        event["run_id"],
        event["operation"],
        actor_id,
        run_id,
        event["actor_status"] or event["status"],
        item_count,
        event["cost_usd"] if event["cost_usd"] is not None else "null",
    )
    return event


def _apply_apify_metadata(event: dict[str, Any], metadata: dict[str, Any]) -> bool:
    cost = _decimal(metadata.get("usageTotalUsd"))
    old_cost = _decimal(event.get("cost_usd"))
    changed = False

    if cost is not None and cost != old_cost:
        event["cost_usd"] = _float(cost)
        event["status"] = "actual"
        changed = True
    elif cost is None and event.get("status") != "missing_cost":
        event["status"] = "missing_cost"
        changed = True

    field_updates = {
        "dataset_id": metadata.get("defaultDatasetId"),
        "actor_status": metadata.get("status"),
        "usage_usd": metadata.get("usageUsd") if isinstance(metadata.get("usageUsd"), dict) else {},
        "usage": metadata.get("usage") if isinstance(metadata.get("usage"), dict) else {},
        "pricing_info": metadata.get("pricingInfo") if isinstance(metadata.get("pricingInfo"), dict) else {},
    }
    for key, value in field_updates.items():
        if value not in (None, {}) and event.get(key) != value:
            event[key] = value
            changed = True

    if changed:
        event["apify_refreshed_at"] = _now()
        logger.info(
            "COST_APIFY_REFRESHED run_id=%s operation=%s actor=%s apify_run_id=%s old_actual_usd=%s actual_usd=%s",
            event.get("run_id"),
            event.get("operation"),
            event.get("actor_id"),
            event.get("apify_run_id"),
            _float(old_cost),
            event.get("cost_usd") if event.get("cost_usd") is not None else "null",
        )
    return changed


def _refresh_apify_events(events: list[dict[str, Any]]) -> None:
    token = _env_file_value("APIFY_TOKEN") or settings.apify_token
    if not token:
        logger.warning("Cannot refresh Apify cost metadata: APIFY_TOKEN is not configured")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            for event in events:
                if event.get("provider") != "apify" or not event.get("apify_run_id"):
                    continue
                response = client.get(APIFY_RUN_URL.format(run_id=event["apify_run_id"]))
                response.raise_for_status()
                metadata = response.json().get("data", {}) or {}
                _apply_apify_metadata(event, metadata)
    except Exception as exc:
        logger.warning("Could not refresh Apify cost metadata: %s", exc)


def summarize_run(run_id: str | None = None, refresh_apify: bool = False) -> dict[str, Any]:
    state = _get_state()
    target_run_id = run_id or state.cost_run_id
    events = [event for event in state.cost_events if event.get("run_id") == target_run_id]
    if refresh_apify:
        _refresh_apify_events(events)
    _reprice_openai_events(events)
    openai_events = [event for event in events if event.get("provider") == "openai"]
    apify_events = [event for event in events if event.get("provider") == "apify"]

    def _sum_complete(provider_events: list[dict[str, Any]]) -> float | None:
        if not provider_events:
            return None
        total = Decimal("0")
        for event in provider_events:
            value = _decimal(event.get("cost_usd"))
            if value is None:
                return None
            total += value
        return float(total.quantize(Decimal("0.0000000001")))

    openai_total = _sum_complete(openai_events)
    apify_total = _sum_complete(apify_events)
    has_missing_cost = any(event.get("cost_usd") is None for event in events)
    if not events or has_missing_cost:
        total = None
    else:
        total_decimal = Decimal("0")
        if openai_total is not None:
            total_decimal += Decimal(str(openai_total))
        if apify_total is not None:
            total_decimal += Decimal(str(apify_total))
        total = float(total_decimal.quantize(Decimal("0.0000000001")))
    timestamps = [event.get("timestamp") for event in events if event.get("timestamp")]

    summary = {
        "run_id": target_run_id,
        "event_count": len(events),
        "openai_event_count": len(openai_events),
        "apify_event_count": len(apify_events),
        "openai_estimated_usd": openai_total,
        "apify_actual_usd": apify_total,
        "total_usd": total,
        "price_missing_count": sum(1 for event in events if event.get("status") == "price_missing"),
        "missing_cost_count": sum(1 for event in events if event.get("cost_usd") is None),
        "started_at": min(timestamps) if timestamps else None,
        "last_event_at": max(timestamps) if timestamps else None,
        "closed": bool(state.cost_run_closed and state.cost_run_id == target_run_id),
    }
    if target_run_id == state.cost_run_id:
        state.cost_summary = summary
    return summary


def run_details(run_id: str | None = None) -> dict[str, Any]:
    state = _get_state()
    target_run_id = run_id or state.cost_run_id
    events = [event for event in state.cost_events if event.get("run_id") == target_run_id]
    return {"summary": summarize_run(target_run_id, refresh_apify=True), "events": events}


def end_run() -> dict[str, Any]:
    state = _get_state()
    run_id = start_or_get_run()
    summary = summarize_run(run_id, refresh_apify=True)
    state.cost_run_closed = True
    state.cost_summary = {**summary, "closed": True, "ended_at": _now()}
    logger.info(
        "COST_RUN_END run_id=%s openai_estimated_usd=%s apify_actual_usd=%s total_usd=%s events=%d",
        run_id,
        summary["openai_estimated_usd"],
        summary["apify_actual_usd"],
        summary["total_usd"],
        summary["event_count"],
    )
    return state.cost_summary
