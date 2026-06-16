from src.models.schemas import Intent, Persona, PipelineState, RawInput, TestCasePrompt


def test_intent_defaults():
    intent = Intent(context="ctx", goal="g", evidence=["e1"])
    assert intent.id
    assert intent.status == "generated"
    assert intent.evidence == ["e1"]


def test_persona_defaults():
    persona = Persona(intent_id="abc", name="P1", description="desc", trait_type="easy")
    assert persona.id
    assert persona.status == "generated"


def test_test_prompt_defaults():
    tp = TestCasePrompt(persona_id="p1", intent_id="i1", prompt_text="text")
    assert tp.id
    assert tp.status == "generated"


def test_raw_input():
    ri = RawInput(source_type="text", content="hello")
    assert ri.id
    assert ri.metadata == {}


def test_pipeline_state():
    state = PipelineState()
    assert state.raw_input is None
    assert state.intents == []
    assert state.current_step == 0

    state.current_step = 1
    assert state.current_step == 1
