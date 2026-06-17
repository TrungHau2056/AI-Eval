import asyncio
import json
import os
import pytest

from dotenv import load_dotenv
from src.llm.factory import create_llm_client
from src.models.schemas import Intent, Persona
from src.pipeline.persona_generator import PersonaAgent
from src.pipeline.test_prompt_generator import TestCaseAgent

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "")


def get_llm():
    if not API_KEY:
        pytest.skip("No OPENAI_API_KEY configured in .env")
    return create_llm_client("openai", API_KEY)


def test_e2e_persona_agent():
    llm = get_llm()
    intents = [
        Intent(context="User wants refund for order", goal="Get money back for defective product", evidence=["I want a refund", "Product is defective and can't exchange"]),
        Intent(context="User asks about delivery time", goal="Know when order arrives", evidence=["How long for delivery?", "When will I receive it?"]),
    ]

    agent = PersonaAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(agent.run(intents))
    finally:
        loop.close()

    assert len(results) >= 2, f"Expected at least 2 personas, got {len(results)}"

    for r in results:
        assert "id" in r
        assert "intent_id" in r
        assert "name" in r
        assert r["name"], "name should not be empty"
        assert "description" in r
        assert r["description"], "description should not be empty"
        assert "trait_type" in r
        assert r["trait_type"] in ("easy", "hard"), f"Invalid trait_type: {r['trait_type']}"

    easy_count = sum(1 for r in results if r["trait_type"] == "easy")
    hard_count = sum(1 for r in results if r["trait_type"] == "hard")
    assert easy_count >= 1, f"Expected at least 1 easy persona, got {easy_count}"
    assert hard_count >= 1, f"Expected at least 1 hard persona, got {hard_count}"


def test_e2e_test_case_agent():
    llm = get_llm()
    intent = Intent(
        id="i1",
        context="User wants refund for order",
        goal="Get money back for defective product",
        evidence=["I want a refund", "Product is defective"],
    )
    personas = [
        Persona(id="p1", intent_id="i1", name="Patient User", description="Patient user who explains issues clearly", trait_type="easy"),
        Persona(id="p2", intent_id="i1", name="Impatient User", description="Impatient user who types short messages and complains", trait_type="hard"),
    ]

    agent = TestCaseAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(agent.run(personas, [intent]))
    finally:
        loop.close()

    assert len(results) >= 1, f"Expected at least 1 test case, got {len(results)}"

    for r in results:
        assert "id" in r
        assert "persona_id" in r
        assert "intent_id" in r
        assert "prompt_text" in r
        assert r["prompt_text"], "prompt_text should not be empty"


def test_e2e_persona_with_guidance():
    llm = get_llm()
    intents = [
        Intent(context="User wants refund", goal="Get money back", evidence=["Refund please"]),
    ]

    agent = PersonaAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(
            agent.run(intents, guidance="Create personas with detailed background and occupation")
        )
    finally:
        loop.close()

    assert len(results) >= 2
    for r in results:
        assert r["name"], "name should not be empty"
        assert r["description"], "description should not be empty"


def test_e2e_full_pipeline():
    llm = get_llm()

    raw_intents = [
        Intent(context="User wants refund for order", goal="Get money back for defective product", evidence=["I want a refund", "Product is defective"]),
    ]

    persona_agent = PersonaAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        personas_dict = loop.run_until_complete(persona_agent.run(raw_intents))
    finally:
        loop.close()

    assert len(personas_dict) >= 2

    personas = [Persona(**p) for p in personas_dict]

    tc_agent = TestCaseAgent(llm)
    loop = asyncio.new_event_loop()
    try:
        test_cases = loop.run_until_complete(tc_agent.run(personas, raw_intents))
    finally:
        loop.close()

    assert len(test_cases) >= 1

    for tc in test_cases:
        assert tc["prompt_text"], "prompt_text should not be empty"
        assert tc["persona_id"] in [p.id for p in personas]
