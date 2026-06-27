import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from src.models.schemas import FEIntent, Intent, Persona, TestCasePrompt


class Exporter:
    @staticmethod
    def _intent_row(
        fe: dict[str, Any],
        internal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = {
            "id": fe.get("id", ""),
            "name": fe.get("name", ""),
            "phase": fe.get("phase", ""),
            "utterance": fe.get("utterance", ""),
            "trigger_moment": fe.get("triggerMoment", ""),
            "source": fe.get("source", ""),
            "coverage": fe.get("coverage", ""),
            "selected": fe.get("selected", True),
            "matched_ids": "; ".join(fe.get("matchedIds") or []),
        }
        if internal:
            row.update({
                "context": internal.get("context", ""),
                "goal": internal.get("goal", ""),
                "evidence": "; ".join(internal.get("evidence") or []),
                "raw_observation": internal.get("raw_observation", ""),
                "why_valid": internal.get("why_valid", ""),
            })
        return row

    @staticmethod
    def intents_to_json_dict(
        intents: list[FEIntent] | list[dict],
        internal_intents: list[Intent] | list[dict] | None = None,
    ) -> dict[str, Any]:
        fe_list = [i.model_dump() if hasattr(i, "model_dump") else i for i in intents]
        internal_map: dict[str, dict[str, Any]] = {}
        if internal_intents:
            for item in internal_intents:
                data = item.model_dump() if hasattr(item, "model_dump") else item
                internal_map[data.get("id", "")] = data

        enriched: list[dict[str, Any]] = []
        for fe in fe_list:
            entry = dict(fe)
            internal = internal_map.get(fe.get("id", ""))
            if internal:
                entry["context"] = internal.get("context", "")
                entry["goal"] = internal.get("goal", "")
                entry["evidence"] = internal.get("evidence", [])
                entry["raw_observation"] = internal.get("raw_observation", "")
                entry["why_valid"] = internal.get("why_valid", "")
            enriched.append(entry)

        return {
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "count": len(enriched),
            "intents": enriched,
        }

    @staticmethod
    def intents_to_json(
        intents: list[FEIntent] | list[dict],
        internal_intents: list[Intent] | list[dict] | None = None,
    ) -> str:
        return json.dumps(
            Exporter.intents_to_json_dict(intents, internal_intents),
            ensure_ascii=False,
            indent=2,
        )

    @staticmethod
    def intents_to_csv(
        intents: list[FEIntent] | list[dict],
        internal_intents: list[Intent] | list[dict] | None = None,
    ) -> str:
        fe_list = [i.model_dump() if hasattr(i, "model_dump") else i for i in intents]
        internal_map: dict[str, dict[str, Any]] = {}
        if internal_intents:
            for item in internal_intents:
                data = item.model_dump() if hasattr(item, "model_dump") else item
                internal_map[data.get("id", "")] = data

        rows = [
            Exporter._intent_row(fe, internal_map.get(fe.get("id", "")))
            for fe in fe_list
        ]
        if not rows:
            rows = [Exporter._intent_row({})]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    @staticmethod
    def to_csv(
        test_prompts: list[TestCasePrompt] | list[dict],
        intents: list[Intent],
        personas: list[Persona],
    ) -> str:
        intent_map = {i.id: i for i in intents}
        persona_map = {p.id: p for p in personas}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "intent_id",
            "intent_num",
            "intent_name",
            "persona_id",
            "persona_type",
            "case_num",
            "title_user_moment",
            "persona",
            "goal",
            "start",
            "end_expected_outcome",
        ])
        for tp in test_prompts:
            if isinstance(tp, dict):
                tp_data = tp
            else:
                tp_data = tp.model_dump()

            intent = intent_map.get(tp_data.get("intent_id", ""))
            persona = persona_map.get(tp_data.get("persona_id", ""))

            writer.writerow([
                tp_data.get("intent_id", ""),
                tp_data.get("intent_num") or (intent.intent_num if intent else ""),
                tp_data.get("intent_name") or (intent.intent_name if intent else ""),
                tp_data.get("persona_id", ""),
                persona.persona_type if persona else "",
                tp_data.get("case_num", ""),
                tp_data.get("title_user_moment", ""),
                tp_data.get("persona", ""),
                tp_data.get("goal", ""),
                tp_data.get("start", ""),
                tp_data.get("end_expected_outcome", ""),
            ])
        return output.getvalue()

    @staticmethod
    def to_markdown(
        test_prompts: list[TestCasePrompt] | list[dict],
        intents: list[Intent],
        personas: list[Persona],
    ) -> str:
        intent_map = {i.id: i for i in intents}
        persona_map = {p.id: p for p in personas}

        grouped: dict[str, dict] = {}
        for tp in test_prompts:
            if isinstance(tp, dict):
                tp_data = tp
            else:
                tp_data = tp.model_dump()

            intent = intent_map.get(tp_data.get("intent_id", ""))
            persona = persona_map.get(tp_data.get("persona_id", ""))
            if not intent or not persona:
                continue

            if intent.id not in grouped:
                grouped[intent.id] = {"intent": intent, "personas": {}}
            if persona.id not in grouped[intent.id]["personas"]:
                grouped[intent.id]["personas"][persona.id] = {
                    "persona": persona,
                    "prompts": [],
                }
            grouped[intent.id]["personas"][persona.id]["prompts"].append(tp_data)

        lines = ["# Test Cases\n"]
        for intent_data in grouped.values():
            intent = intent_data["intent"]
            lines.append(f"## Intent: {intent.intent_name}\n")
            lines.append(f"**Utterance:** {intent.utterance}\n")
            lines.append(f"**Moment:** {intent.moment}\n")
            for persona_data in intent_data["personas"].values():
                persona = persona_data["persona"]
                lines.append(f"### Persona: [{persona.persona_type}] {persona.trigger}\n")
                lines.append(f"- **Utterance:** {persona.utterance}")
                lines.append(f"- **Pain:** {persona.pain}")
                lines.append(f"- **Reject:** {persona.reject}\n")
                for tp in persona_data["prompts"]:
                    lines.append(f"#### Test Case: {tp.get('title_user_moment', '')}\n")
                    lines.append(f"- **Goal:** {tp.get('goal', '')}")
                    lines.append(f"- **Start:** `{tp.get('start', '')}`")
                    lines.append(f"- **Expected Outcome:** {tp.get('end_expected_outcome', '')}\n")
        return "\n".join(lines)
