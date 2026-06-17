import asyncio
import os
import pytest

from dotenv import load_dotenv
from src.llm.factory import create_llm_client
from src.models.schemas import Intent, Persona, RawInput
from src.pipeline.intent_extractor import IntentAgent
from src.pipeline.persona_generator import PersonaAgent
from src.pipeline.test_prompt_generator import TestCaseAgent

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "")


def get_llm():
    if not API_KEY:
        pytest.skip("No OPENAI_API_KEY configured in .env")
    return create_llm_client("openai", API_KEY)


SAMPLE_RAW_TEXT = """
I bought a phone last week and it arrived with a cracked screen. I want a refund immediately!
The delivery took 10 days, way too long. When I try to track my order it says "processing" for days.
I need to change my shipping address but there's no option in the app. Help please.
The product quality is great but the customer service is terrible. No one replies to my emails.
Can I return this item? It doesn't fit. I ordered size M but it runs small.
I've been waiting for 2 weeks and my order still hasn't shipped. This is unacceptable.
"""


def test_e2e_intent_agent():
    llm = get_llm()
    raw_input = RawInput(source_type="text", content=SAMPLE_RAW_TEXT)

    agent = IntentAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(agent.run(raw_input))
    finally:
        loop.close()

    assert len(results) >= 2, f"Expected at least 2 intents, got {len(results)}"

    for r in results:
        assert "id" in r
        assert r.get("intent_name"), "intent_name should not be empty"
        assert r.get("utterance"), "utterance should not be empty"

    # LLM returns Vietnamese text; avoid print() on cp1252 Windows console


def test_e2e_intent_with_guidance():
    llm = get_llm()
    raw_input = RawInput(source_type="text", content=SAMPLE_RAW_TEXT)

    agent = IntentAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(
            agent.run(raw_input, guidance="Focus on delivery and refund related intents only")
        )
    finally:
        loop.close()

    assert len(results) >= 1
    for r in results:
        assert r.get("intent_name"), "intent_name should not be empty"


def test_e2e_full_3_agent_pipeline():
    llm = get_llm()

    # Step 1: IntentAgent
    raw_input = RawInput(source_type="text", content=SAMPLE_RAW_TEXT)
    intent_agent = IntentAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        intent_dicts = loop.run_until_complete(intent_agent.run(raw_input))
    finally:
        loop.close()

    assert len(intent_dicts) >= 2, f"Step 1 failed: got {len(intent_dicts)} intents"
    intents = [Intent(**d) for d in intent_dicts]

    # Step 2: PersonaAgent
    persona_agent = PersonaAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        persona_dicts = loop.run_until_complete(persona_agent.run(intents))
    finally:
        loop.close()

    assert len(persona_dicts) >= 2, f"Step 2 failed: got {len(persona_dicts)} personas"
    personas = [Persona(**d) for d in persona_dicts]

    easy = [p for p in personas if p.trait_type == "easy"]
    hard = [p for p in personas if p.trait_type == "hard"]
    assert len(easy) >= 1, "Expected at least 1 easy persona"
    assert len(hard) >= 1, "Expected at least 1 hard persona"

    # Step 3: TestCaseAgent
    tc_agent = TestCaseAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        test_cases = loop.run_until_complete(tc_agent.run(personas, intents))
    finally:
        loop.close()

    assert len(test_cases) >= 1, f"Step 3 failed: got {len(test_cases)} test cases"
    for tc in test_cases:
        assert tc.get("start"), "start should not be empty"
        assert tc.get("end_expected_outcome"), "end_expected_outcome should not be empty"
        assert tc["persona_id"] in [p.id for p in personas]
        assert tc["intent_id"] in [i.id for i in intents]

    # Pipeline completed: intents -> personas -> test cases
