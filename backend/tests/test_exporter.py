from src.export.exporter import Exporter
from src.models.schemas import Intent, Persona, TestCasePrompt


def _make_data():
    intent = Intent(intent_name="Yeu cau hoan tien", utterance="hoan tien cho toi", moment="Mua sai san pham", phase="Su dung")
    happy_persona = Persona(intent_id=intent.id, persona_type="happy-path", trigger="Nhan hang sai", utterance="cho minh hoan tien nhe", pain="Tra cham", reject="Khong hoan duoc", expected_behavior="Xu ly hoan tien nhanh")
    edge_persona = Persona(intent_id=intent.id, persona_type="edge-case", trigger="Bi lua", utterance="tra tien lai cho toi ngay", pain="Khong duoc hoan tien", reject="Tu choi hoan tien", expected_behavior="Xu ly khieu nai va de nghi giai phap")
    tp1 = TestCasePrompt(persona_id=happy_persona.id, intent_id=intent.id, start="cho minh hoan tien nhe", end_expected_outcome="[MUST HAVE] AI xu ly hoan tien trong 1 luet", title_user_moment="User mua sai san pham", goal="Hoan tien")
    tp2 = TestCasePrompt(persona_id=edge_persona.id, intent_id=intent.id, start="tra tien lai cho toi ngay", end_expected_outcome="[MUST HAVE] AI de nghi giai phap [MUST NOT HAVE] AI khong tu choi khieu nai", title_user_moment="User bi lua mua hang", goal="Giai quyet khieu nai")
    return intent, [happy_persona, edge_persona], [tp1, tp2]


def test_export_csv():
    intent, personas, prompts = _make_data()
    csv = Exporter.to_csv(prompts, [intent], personas)
    assert "intent_name" in csv
    assert "Yeu cau hoan tien" in csv
    assert "start" in csv
    assert "cho minh hoan tien nhe" in csv


def test_export_markdown():
    intent, personas, prompts = _make_data()
    md = Exporter.to_markdown(prompts, [intent], personas)
    assert "# Test Cases" in md
    assert "Yeu cau hoan tien" in md
    assert "cho minh hoan tien nhe" in md