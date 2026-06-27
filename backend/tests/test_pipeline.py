import asyncio

from src.pipeline.intent_extractor import IntentAgent
from src.pipeline.persona_generator import PersonaAgent
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


class MockLLMSequence:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls: list[dict[str, str]] = []

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        return self.responses.pop(0)

    async def generate_structured(self, prompt, schema, system_prompt=""):
        return await self.generate(prompt, system_prompt)


# --- Intent ---

def test_intent_agent_parse():
    response = '''```json
    {
        "intents": [
            {"intent_num": 1, "intent_name": "Tim tram sac gan cho dang dung", "utterance": "sac o dau day troi oi", "moment": "Dang di duong, pin sap het", "source": "chat", "phase": "Su dung", "raw_observation": "User hoi tram sac khi pin thap", "why_valid": "Nhu cau thuc te khi di chuyen"},
            {"intent_num": 2, "intent_name": "Bao tram sac hong", "utterance": "tram sac o quan 7 hong roi", "moment": "Den tram va thay khong sac duoc", "source": "review", "phase": "Loi/Khan cap", "raw_observation": "User bao loi tram sac", "why_valid": "Can bao loi de bao tri"}
        ]
    }
    ```'''
    agent = IntentAgent(MockLLM(response))
    intents = agent._parse(response)
    assert len(intents) == 2
    assert intents[0]["intent_name"] == "Tim tram sac gan cho dang dung"
    assert intents[0]["utterance"] == "sac o dau day troi oi"
    assert intents[0]["moment"] == "Dang di duong, pin sap het"
    assert intents[1]["intent_name"] == "Bao tram sac hong"


def test_intent_agent_parse_name_alias():
    response = '{"intents": [{"name": "Dat lich lai thu VF8", "utterance": "dat lai thu vf8 t7", "trigger_moment": "Dang xem web"}]}'
    agent = IntentAgent(MockLLM(response))
    intents = agent._parse(response)
    assert len(intents) == 1
    assert intents[0]["intent_name"] == "Dat lich lai thu VF8"
    assert intents[0]["moment"] == "Dang xem web"


def test_intent_agent_deduplicate():
    agent = IntentAgent(MockLLM(""))
    intents = [
        Intent(intent_name="  Tim tram sac  ", utterance="sac o dau", moment="Dang di").model_dump(),
        Intent(intent_name="tim tram sac", utterance="sac o dau", moment="Dang di").model_dump(),
        Intent(intent_name="Bao tram sac hong", utterance="tram hong", moment="Den tram").model_dump(),
    ]
    deduped = agent._deduplicate(intents)
    assert len(deduped) == 2


def test_intent_agent_memory_integrated():
    memory = ConversationMemory()
    agent = IntentAgent(MockLLM(""), memory=memory)

    prompt = agent._build_prompt("some text", "")
    assert "Lich su" not in prompt

    memory.add("feedback", "Find more specific intents")
    prompt = agent._build_prompt("some text", "")
    assert "Find more specific intents" in prompt
    assert "Lich su" in prompt


def test_intent_agent_add_feedback():
    memory = ConversationMemory()
    agent = IntentAgent(MockLLM(""), memory=memory)
    agent.add_feedback("Too many generic intents")
    assert "Too many generic intents" in memory.get_context()


# --- Persona ---

def test_persona_agent_add_feedback():
    memory = ConversationMemory()
    agent = PersonaAgent(MockLLM(""), memory=memory)
    agent.add_feedback("Persona qua chung chung")
    assert "Persona qua chung chung" in memory.get_context()


def test_persona_agent_run_uses_langgraph_generator_and_evaluator():
    persona_response = '''{
        "personas": [
            {"intent_num": 1, "intent_name": "Tim tram sac", "persona_num": 1, "persona_type": "happy-path", "trigger": "Di ve nha, muon sac xe", "utterance": "cho minh hoi tram sac o quan 7 con cho k a", "frequency": "2 lan/tuan", "pain": "Khong biet tram nao con cho", "reject": "Tram doi dien vi xa va dat", "special_situation": "", "research_source": "gia dinh", "why_different": "User ranh cong nghe, kien nhan", "expected_behavior": "Hoi ro rang, de hieu", "ai_response_example": "AI tra ve 2-3 tram gan nhat"},
            {"intent_num": 1, "intent_name": "Tim tram sac", "persona_num": 2, "persona_type": "edge-case", "trigger": "Dang di duong, pin sap het", "utterance": "sac o dau day troi oi pin sap het roi", "frequency": "1 lan/thang", "pain": "Khong ranh cong nghe, gap", "reject": "App phuc tap can dang nhap", "special_situation": "Dang lai xe", "research_source": "gia dinh", "why_different": "User khan cap, khong ranh cong nghe", "expected_behavior": "Can ket qua nhanh, don gian", "ai_response_example": "AI tra ve 1 tram gan nhat voi chi dan don gian"},
            {"intent_num": 2, "intent_name": "Bao tram sac hong", "persona_num": 1, "persona_type": "happy-path", "trigger": "Den tram va thay tru khong nhan sac", "utterance": "minh bao tram o quan 7 bi hong nhe", "frequency": "1 lan/thang luc gap tram loi", "pain": "Khong biet gui bao loi o dau", "reject": "Khong quan tam voucher vi can tram duoc sua som", "special_situation": "", "research_source": "review", "why_different": "User binh tinh va cung cap vi tri ro", "expected_behavior": "Ghi nhan loi va xin thong tin tram", "ai_response_example": "AI huong dan gui ma tram va anh chup"},
            {"intent_num": 2, "intent_name": "Bao tram sac hong", "persona_num": 2, "persona_type": "edge-case", "trigger": "Dang can sac gap nhung tru bao loi", "utterance": "tru nay hong roi lam sao gio", "frequency": "2 lan/nam khi di xa", "pain": "So het pin giua duong", "reject": "Khong muon nghe quy trinh dai vi dang gap", "special_situation": "Dang di xa", "research_source": "chat log", "why_different": "User gap va thieu thong tin", "expected_behavior": "Hoi vi tri ngan gon va dua cach xu ly nhanh", "ai_response_example": "AI de nghi tram gan nhat va cach bao loi"}
        ]
    }'''
    eval_response = '''{
        "approved": true,
        "score": 0.91,
        "issues": [],
        "revision_guidance": ""
    }'''
    llm = MockLLMSequence([persona_response, eval_response])
    agent = PersonaAgent(llm)
    intent = Intent(id="i1", intent_num=1, intent_name="Tim tram sac", utterance="sac o dau", moment="Dang di")
    second_intent = Intent(id="i2", intent_num=2, intent_name="Bao tram sac hong", utterance="tram hong", moment="Den tram")

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(agent.run([intent, second_intent]))
    finally:
        loop.close()

    assert len(results) == 4
    assert len(llm.calls) == 2
    assert "Senior UX Researcher" in llm.calls[0]["system_prompt"]
    assert "Persona Quality Evaluator" in llm.calls[1]["system_prompt"]
    assert results[0]["trait_type"] == "easy"
    assert results[1]["trait_type"] == "hard"


# --- Test Case ---

def test_test_case_agent_parse():
    persona = Persona(id="p1", intent_id="i1", persona_num=1, persona_type="happy-path", trigger="Di ve nha", utterance="cho minh hoi tram sac", pain="Khong biet tram nao")
    intent = Intent(id="i1", intent_num=1, intent_name="Tim tram sac")
    response = '{"test_cases": [{"intent_num": 1, "intent_name": "Tim tram sac", "case_num": 1, "title_user_moment": "User di ve nha muon sac xe", "persona": "User rành công nghệ", "goal": "Tim tram sac gan nhat", "start": "cho minh hoi tram sac o quan 7 con cho k a", "end_expected_outcome": "[MUST HAVE] AI tra ve 2-3 tram gan nhat. [MUST NOT HAVE] AI khong goi y tram cach >2km."}]}'
    agent = TestCaseAgent(MockLLM(response))
    results = agent._parse(response, persona, intent)
    assert len(results) == 1
    assert results[0]["start"] == "cho minh hoi tram sac o quan 7 con cho k a"
    assert results[0]["end_expected_outcome"] == "[MUST HAVE] AI tra ve 2-3 tram gan nhat. [MUST NOT HAVE] AI khong goi y tram cach >2km."
    assert results[0]["persona_id"] == "p1"
    assert results[0]["title_user_moment"] == "User di ve nha muon sac xe"


def test_test_case_agent_parse_empty():
    persona = Persona(id="p1", intent_id="i1", persona_type="happy-path")
    intent = Intent(id="i1", intent_name="Test")
    agent = TestCaseAgent(MockLLM(""))
    results = agent._parse("{}", persona, intent)
    assert len(results) == 0


def test_test_case_agent_memory_integrated():
    persona = Persona(id="p1", intent_id="i1", persona_type="happy-path", trigger="Di ve nha")
    intent = Intent(id="i1", intent_name="Tim tram sac")
    memory = ConversationMemory()
    agent = TestCaseAgent(MockLLM(""), memory=memory)

    prompt = agent._build_prompt(persona, intent, "")
    assert "Lich su" not in prompt

    memory.add("feedback", "Make it more aggressive")
    prompt = agent._build_prompt(persona, intent, "")
    assert "Make it more aggressive" in prompt


def test_test_case_agent_add_feedback():
    memory = ConversationMemory()
    agent = TestCaseAgent(MockLLM(""), memory=memory)
    agent.add_feedback("Test case qua chung chung")
    assert "Test case qua chung chung" in memory.get_context()


def test_agent_clear_memory():
    memory = ConversationMemory()
    agent = TestCaseAgent(MockLLM(""), memory=memory)
    agent.add_feedback("test")
    agent.clear_memory()
    assert memory.get_context() == ""


# --- Memory ---

def test_memory_add_and_get_context():
    memory = ConversationMemory()
    memory.add("user", "Sinh test case kho hon")
    memory.add("assistant", ["Test case 1", "Test case 2"])
    memory.add("feedback", "Persona easy chua du chi tiet")
    ctx = memory.get_context()
    assert "Sinh test case kho hon" in ctx
    assert "Test case 1" in ctx
    assert "Persona easy chua du chi tiet" in ctx


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


# --- Deps memory ---

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
