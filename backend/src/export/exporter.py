import csv
import io

from src.models.schemas import Intent, Persona, TestCasePrompt


class Exporter:
    @staticmethod
    def to_csv(
        test_prompts: list[TestCasePrompt],
        intents: list[Intent],
        personas: list[Persona],
    ) -> str:
        intent_map = {i.id: i for i in intents}
        persona_map = {p.id: p for i in intents for p in personas if p.intent_id == i.id}
        persona_map = {p.id: p for p in personas}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "intent_id",
            "intent_context",
            "intent_goal",
            "persona_id",
            "persona_name",
            "persona_trait",
            "persona_description",
            "test_prompt",
        ])
        for tp in test_prompts:
            intent = intent_map.get(tp.intent_id)
            persona = persona_map.get(tp.persona_id)
            writer.writerow([
                tp.intent_id,
                intent.context if intent else "",
                intent.goal if intent else "",
                tp.persona_id,
                persona.name if persona else "",
                persona.trait_type if persona else "",
                persona.description if persona else "",
                tp.prompt_text,
            ])
        return output.getvalue()

    @staticmethod
    def to_markdown(
        test_prompts: list[TestCasePrompt],
        intents: list[Intent],
        personas: list[Persona],
    ) -> str:
        intent_map = {i.id: i for i in intents}
        persona_map = {p.id: p for p in personas}

        grouped: dict[str, dict[str, list[TestCasePrompt]]] = {}
        for tp in test_prompts:
            intent = intent_map.get(tp.intent_id)
            persona = persona_map.get(tp.persona_id)
            if not intent or not persona:
                continue
            if intent.id not in grouped:
                grouped[intent.id] = {"intent": intent, "personas": {}}
            if persona.id not in grouped[intent.id]["personas"]:
                grouped[intent.id]["personas"][persona.id] = {
                    "persona": persona,
                    "prompts": [],
                }
            grouped[intent.id]["personas"][persona.id]["prompts"].append(tp)

        lines = ["# Test Cases\n"]
        for intent_data in grouped.values():
            intent = intent_data["intent"]
            lines.append(f"## Intent: {intent.goal}\n")
            lines.append(f"**Bối cảnh:** {intent.context}\n")
            for persona_data in intent_data["personas"].values():
                persona = persona_data["persona"]
                lines.append(f"### Persona: {persona.name} ({persona.trait_type})\n")
                lines.append(f"{persona.description}\n")
                for tp in persona_data["prompts"]:
                    lines.append(f"**Test Prompt:**\n> {tp.prompt_text}\n")
        return "\n".join(lines)
