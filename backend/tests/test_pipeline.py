from src.pipeline.intent_extractor import IntentExtractor
from src.pipeline.persona_generator import PersonaGenerator
from src.pipeline.test_prompt_generator import TestCasePromptGenerator
from src.models.schemas import Intent, Persona, RawInput


class MockLLM:
    def __init__(self, response: str):
        self.response = response

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        return self.response

    async def generate_structured(self, prompt, schema, system_prompt=""):
        return self.response


def test_intent_extractor_parse():
    response = '''```json
    {
        "intents": [
            {"context": "User wants refund", "goal": "Get money back", "evidence": ["I want my money back"]},
            {"context": "User asks about shipping", "goal": "Know delivery time", "evidence": ["When will it arrive?"]}
        ]
    }
    ```'''
    extractor = IntentExtractor(MockLLM(response))
    intents = extractor._parse_response(response)
    assert len(intents) == 2
    assert intents[0].context == "User wants refund"
    assert intents[0].evidence == ["I want my money back"]


def test_intent_extractor_deduplicate():
    extractor = IntentExtractor(MockLLM(""))
    intents = [
        Intent(context="  Refund  ", goal="Get money", evidence=[]),
        Intent(context="refund", goal="get money", evidence=["e"]),
        Intent(context="Shipping", goal="Delivery time", evidence=[]),
    ]
    deduped = extractor._deduplicate(intents)
    assert len(deduped) == 2


def test_persona_generator_parse():
    response = '''{
        "personas": [
            {"name": "Easy User", "description": "Patient and clear", "trait_type": "easy"},
            {"name": "Hard User", "description": "Impatient and vague", "trait_type": "hard"}
        ]
    }'''
    gen = PersonaGenerator(MockLLM(response))
    personas = gen._parse_response(response, "intent_1")
    assert len(personas) == 2
    assert personas[0].trait_type == "easy"
    assert personas[1].trait_type == "hard"
    assert personas[0].intent_id == "intent_1"


def test_test_prompt_generator_parse():
    response = '{"prompt_text": "I need a refund for my order please"}'
    gen = TestCasePromptGenerator(MockLLM(response))
    result = gen._parse_response(response, "p1", "i1")
    assert result is not None
    assert result.prompt_text == "I need a refund for my order please"
    assert result.persona_id == "p1"
    assert result.intent_id == "i1"


def test_test_prompt_generator_parse_empty():
    gen = TestCasePromptGenerator(MockLLM(""))
    result = gen._parse_response("{}", "p1", "i1")
    assert result is None
