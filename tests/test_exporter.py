from src.export.exporter import Exporter
from src.models.schemas import Intent, Persona, TestCasePrompt


def _make_data():
    intent = Intent(context="User bought product", goal="Get refund", evidence=["want money back"])
    easy_persona = Persona(intent_id=intent.id, name="Easy User", description="Patient", trait_type="easy")
    hard_persona = Persona(intent_id=intent.id, name="Hard User", description="Angry", trait_type="hard")
    tp1 = TestCasePrompt(persona_id=easy_persona.id, intent_id=intent.id, prompt_text="I'd like a refund please")
    tp2 = TestCasePrompt(persona_id=hard_persona.id, intent_id=intent.id, prompt_text="Give me my money back NOW!")
    return intent, [easy_persona, hard_persona], [tp1, tp2]


def test_export_csv():
    intent, personas, prompts = _make_data()
    csv = Exporter.to_csv(prompts, [intent], personas)
    assert "intent_context" in csv
    assert "Easy User" in csv
    assert "Hard User" in csv
    assert "refund" in csv


def test_export_markdown():
    intent, personas, prompts = _make_data()
    md = Exporter.to_markdown(prompts, [intent], personas)
    assert "# Test Cases" in md
    assert "Easy User" in md
    assert "Hard User" in md
    assert "refund please" in md
