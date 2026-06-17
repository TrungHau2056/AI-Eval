"""
Intent Loader Utilities
========================
Load intents từ nhiều nguồn khác nhau vào IntentInput format.

Hỗ trợ:
  1. JSON file (output của IntentExtractor từ team chính)
  2. CSV file (tương thích với export format của team)
  3. Dict trực tiếp (từ API call)

Không import từ src.models.schemas để tránh circular dependency
và conflict khi team chính refactor.
"""
import csv
import json
import io
from pathlib import Path
from typing import Any

from ..schemas.models import IntentInput


def load_intents_from_json(path: str | Path) -> list[IntentInput]:
    """
    Load từ JSON file.

    Hỗ trợ 2 format:
      1. {"intents": [...]} — output trực tiếp của IntentExtractor
      2. [...] — list intent trực tiếp

    Ví dụ JSON:
      {
        "intents": [
          {"id": "abc123", "context": "...", "goal": "...", "evidence": ["..."]},
          ...
        ]
      }
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    items: list[dict] = data.get("intents", data) if isinstance(data, dict) else data
    return [IntentInput.from_dict(item) for item in items]


def load_intents_from_csv(path: str | Path) -> list[IntentInput]:
    """
    Load từ CSV file.

    Yêu cầu columns: context, goal
    Optional columns: id, evidence (dạng "ev1; ev2; ev3")

    Tương thích với export CSV format của team (intent_context, intent_goal).
    """
    intents = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Support cả 2 naming convention
            context = row.get("context") or row.get("intent_context", "")
            goal = row.get("goal") or row.get("intent_goal", "")
            if not context or not goal:
                continue

            # Evidence có thể là field riêng hoặc semicolon-separated
            evidence_raw = row.get("evidence", "")
            evidence = (
                [e.strip() for e in evidence_raw.split(";") if e.strip()]
                if evidence_raw
                else []
            )

            intents.append(
                IntentInput(
                    id=row.get("id", row.get("intent_id", "")),
                    context=context.strip(),
                    goal=goal.strip(),
                    evidence=evidence,
                )
            )
    return intents


def load_intents_from_dicts(data: list[dict[str, Any]]) -> list[IntentInput]:
    """
    Load từ list of dicts (từ API / PipelineState trực tiếp).
    Dùng khi integrate với backend pipeline.
    """
    return [IntentInput.from_dict(d) for d in data]


def load_intents_from_api_state(state_dict: dict[str, Any]) -> list[IntentInput]:
    """
    Load intents từ GET /api/state response.

    state_dict format:
      {"intents": [...], "current_step": 2, ...}

    Chỉ lấy intent có status != "deleted".
    """
    intents_raw = state_dict.get("intents", [])
    valid = [i for i in intents_raw if i.get("status") != "deleted"]
    return load_intents_from_dicts(valid)
