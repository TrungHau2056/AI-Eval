from src.pipeline.intent_extractor import IntentExtractor
from src.pipeline.persona_generator import PersonaGenerator
from src.pipeline.test_prompt_generator import TestCaseAgent
from src.memory.conversation_memory import ConversationMemory
from src.api.deps import get_memory, reset_state
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


def test_test_case_agent_parse():
    persona = Persona(id="p1", intent_id="i1", name="Easy User", description="Patient", trait_type="easy")
    intent = Intent(id="i1", context="Refund", goal="Get money back", evidence=[])
    response = '{"test_cases": [{"prompt_text": "I need a refund for my order please"}]}'
    agent = TestCaseAgent(MockLLM(response))
    results = agent._parse(response, persona, intent)
    assert len(results) == 1
    assert results[0]["prompt_text"] == "I need a refund for my order please"
    assert results[0]["persona_id"] == "p1"
    assert results[0]["intent_id"] == "i1"


def test_test_case_agent_parse_empty():
    persona = Persona(id="p1", intent_id="i1", name="Easy User", description="Patient", trait_type="easy")
    intent = Intent(id="i1", context="Refund", goal="Get money back", evidence=[])
    agent = TestCaseAgent(MockLLM(""))
    results = agent._parse("{}", persona, intent)
    assert len(results) == 0


def test_memory_add_and_get_context():
    memory = ConversationMemory()
    memory.add("user", "Hãy sinh test case khó hơn")
    memory.add("assistant", ["Test case 1", "Test case 2"])
    memory.add("feedback", "Persona easy chưa đủ chi tiết")
    ctx = memory.get_context()
    assert "Hãy sinh test case khó hơn" in ctx
    assert "Test case 1" in ctx
    assert "Persona easy chưa đủ chi tiết" in ctx


def test_memory_get_context_max_entries():
    memory = ConversationMemory()
    memory.add("user", "guidance 1")
    memory.add("assistant", ["result 1"])
    memory.add("user", "guidance 2")
    ctx = memory.get_context(max_entries=2)
    assert "guidance 1" not in ctx
    assert "guidance 2" in ctx


def test_memory_clear():
    memory = ConversationMemory()
    memory.add("user", "test")
    memory.clear()
    assert memory.get_context() == ""


def test_agent_memory_integrated():
    persona = Persona(id="p1", intent_id="i1", name="Easy User", description="Patient", trait_type="easy")
    intent = Intent(id="i1", context="Refund", goal="Get money back", evidence=[])
    response = '{"test_cases": [{"prompt_text": "I need a refund please"}]}'
    memory = ConversationMemory()
    agent = TestCaseAgent(MockLLM(response), memory=memory)

    prompt = agent._build_prompt(persona, intent, "")
    assert "Lịch sử" not in prompt

    memory.add("feedback", "Make it more aggressive")
    prompt = agent._build_prompt(persona, intent, "")
    assert "Make it more aggressive" in prompt
    assert "Lịch sử" in prompt


def test_agent_add_feedback():
    memory = ConversationMemory()
    agent = TestCaseAgent(MockLLM(""), memory=memory)
    agent.add_feedback("Test case quá chung chung")
    assert "Test case quá chung chung" in memory.get_context()


def test_agent_clear_memory():
    memory = ConversationMemory()
    agent = TestCaseAgent(MockLLM(""), memory=memory)
    agent.add_feedback("test")
    agent.clear_memory()
    assert memory.get_context() == ""


def test_deps_memory_per_agent():
    reset_state()
    m1 = get_memory("intent")
    m2 = get_memory("persona")
    m3 = get_memory("test_case")

    m1.add("user", "intent guidance")
    m2.add("user", "persona guidance")

    assert "intent guidance" in m1.get_context()
    assert "persona guidance" not in m1.get_context()
    assert "persona guidance" in m2.get_context()
    assert "intent guidance" not in m2.get_context()
    assert m3.get_context() == ""


def test_deps_memory_same_agent_persisted():
    reset_state()
    m_first = get_memory("test_case")
    m_first.add("user", "remember this")

    m_second = get_memory("test_case")
    assert "remember this" in m_second.get_context()


def test_deps_reset_clears_memory():
    reset_state()
    get_memory("test_case").add("user", "should be gone")
    reset_state()
    assert get_memory("test_case").get_context() == ""
