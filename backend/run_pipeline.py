import asyncio
import sys

from dotenv import load_dotenv
from src.llm.factory import create_llm_client
from src.models.schemas import Intent, Persona, RawInput
from src.pipeline.intent_extractor import IntentAgent
from src.pipeline.persona_generator import PersonaAgent
from src.pipeline.test_prompt_generator import TestCaseAgent
from src.memory.conversation_memory import ConversationMemory

load_dotenv()


def get_llm():
    import os
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("OPENAI_API_KEY not found in .env")
        api_key = input("Enter API key: ").strip()
    return create_llm_client("openai", api_key)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def print_separator():
    print("\n" + "=" * 60)


def input_text():
    print_separator()
    print("STEP 0: INPUT")
    print("Paste your raw text (press Enter twice to finish):")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            lines.pop()
            break
        lines.append(line)
    return "\n".join(lines)


def review_intents(intent_dicts):
    print_separator()
    print("STEP 1: INTENT REVIEW")
    print(f"Found {len(intent_dicts)} intents:\n")
    for i, intent in enumerate(intent_dicts, 1):
        print(f"  [{i}] Intent: {intent['intent_name']}")
        print(f"      Utterance: {intent['utterance']}")
        print(f"      Moment:    {intent['moment']}")
        print(f"      Phase:     {intent['phase']}")
        if intent.get('why_valid'):
            print(f"      Why valid: {intent['why_valid']}")
        print()

    while True:
        choice = input("Action: [a]ccept all / [d]elete some / [r]egenerate / [q]uit: ").strip().lower()
        if choice == "a":
            return intent_dicts, "accept"
        elif choice == "d":
            nums = input("Enter intent numbers to delete (e.g. 1,3,5): ").strip()
            to_delete = set()
            for n in nums.split(","):
                n = n.strip()
                if n.isdigit():
                    to_delete.add(int(n) - 1)
            intent_dicts = [d for i, d in enumerate(intent_dicts) if i not in to_delete]
            print(f"Deleted. {len(intent_dicts)} intents remaining.\n")
            for i, intent in enumerate(intent_dicts, 1):
                print(f"  [{i}] {intent['intent_name']}")
            print()
        elif choice == "r":
            guidance = input("Guidance for regeneration: ").strip()
            return intent_dicts, f"regenerate:{guidance}"
        elif choice == "q":
            sys.exit(0)


def review_personas(persona_dicts):
    print_separator()
    print("STEP 2: PERSONA REVIEW")
    print(f"Found {len(persona_dicts)} personas:\n")
    for i, p in enumerate(persona_dicts, 1):
        ptype = p.get('persona_type', p.get('trait_type', ''))
        print(f"  [{i}] [{ptype}] Intent: {p.get('intent_name', '')}")
        print(f"      Trigger:    {p.get('trigger', '')}")
        print(f"      Utterance:  {p.get('utterance', '')}")
        print(f"      Pain:       {p.get('pain', '')}")
        print(f"      Reject:     {p.get('reject', '')}")
        print()

    while True:
        choice = input("Action: [a]ccept all / [d]elete some / [r]egenerate / [q]uit: ").strip().lower()
        if choice == "a":
            return persona_dicts, "accept"
        elif choice == "d":
            nums = input("Enter persona numbers to delete (e.g. 1,3): ").strip()
            to_delete = set()
            for n in nums.split(","):
                n = n.strip()
                if n.isdigit():
                    to_delete.add(int(n) - 1)
            persona_dicts = [d for i, d in enumerate(persona_dicts) if i not in to_delete]
            print(f"Deleted. {len(persona_dicts)} personas remaining.\n")
            for i, p in enumerate(persona_dicts, 1):
                ptype = p.get('persona_type', p.get('trait_type', ''))
                print(f"  [{i}] [{ptype}] {p.get('trigger', '')[:60]}")
            print()
        elif choice == "r":
            guidance = input("Guidance for regeneration: ").strip()
            return persona_dicts, f"regenerate:{guidance}"
        elif choice == "q":
            sys.exit(0)


def review_test_cases(tc_dicts):
    print_separator()
    print("STEP 3: TEST CASE REVIEW")
    print(f"Found {len(tc_dicts)} test cases:\n")
    for i, tc in enumerate(tc_dicts, 1):
        print(f"  [{i}] {tc.get('title_user_moment', '')}")
        print(f"      Start:  {tc.get('start', '')}")
        print(f"      End:    {tc.get('end_expected_outcome', '')[:80]}")
        print()

    while True:
        choice = input("Action: [a]ccept all / [d]elete some / [r]egenerate / [e]xport / [q]uit: ").strip().lower()
        if choice == "a":
            return tc_dicts, "accept"
        elif choice == "d":
            nums = input("Enter test case numbers to delete (e.g. 1,3): ").strip()
            to_delete = set()
            for n in nums.split(","):
                n = n.strip()
                if n.isdigit():
                    to_delete.add(int(n) - 1)
            tc_dicts = [d for i, d in enumerate(tc_dicts) if i not in to_delete]
            print(f"Deleted. {len(tc_dicts)} test cases remaining.\n")
            for i, tc in enumerate(tc_dicts, 1):
                print(f"  [{i}] {tc.get('title_user_moment', '')[:60]}")
            print()
        elif choice == "r":
            guidance = input("Guidance for regeneration: ").strip()
            return tc_dicts, f"regenerate:{guidance}"
        elif choice == "e":
            return tc_dicts, "export"
        elif choice == "q":
            sys.exit(0)


def export_results(tc_dicts, persona_dicts, intent_dicts):
    from src.export.exporter import Exporter
    intents = [Intent(**d) for d in intent_dicts]
    personas = [Persona(**d) for d in persona_dicts]
    test_cases = tc_dicts

    csv = Exporter.to_csv(test_cases, intents, personas)
    with open("test_cases.csv", "w", encoding="utf-8") as f:
        f.write(csv)
    print("Exported: test_cases.csv")

    md = Exporter.to_markdown(test_cases, intents, personas)
    with open("test_cases.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("Exported: test_cases.md")


def main():
    print("=" * 60)
    print("  AI TEST CASE GENERATOR - Interactive Pipeline")
    print("=" * 60)

    llm = get_llm()
    raw_text = input_text()
    if not raw_text.strip():
        print("No input text. Exiting.")
        return

    raw_input = RawInput(source_type="text", content=raw_text)

    # --- Step 1: Intent ---
    intent_agent = IntentAgent(llm, memory=ConversationMemory())
    intent_dicts = None
    guidance = ""

    while True:
        print("\nGenerating intents...")
        results = run_async(intent_agent.run(raw_input, guidance=guidance))
        if not results:
            print("No intents generated. Try again with different input.")
            return

        intent_dicts, action = review_intents(results)
        if action == "accept":
            break
        elif action.startswith("regenerate:"):
            guidance = action.split(":", 1)[1]
            intent_agent = IntentAgent(llm, memory=ConversationMemory())
            continue

    # --- Step 2: Persona ---
    intents = [Intent(**d) for d in intent_dicts]
    persona_agent = PersonaAgent(llm, memory=ConversationMemory())
    persona_dicts = None
    guidance = ""

    while True:
        print("\nGenerating personas...")
        results = run_async(persona_agent.run(intents, guidance=guidance))
        if not results:
            print("No personas generated. Try again.")
            return

        persona_dicts, action = review_personas(results)
        if action == "accept":
            break
        elif action.startswith("regenerate:"):
            guidance = action.split(":", 1)[1]
            persona_agent = PersonaAgent(llm, memory=ConversationMemory())
            continue

    # --- Step 3: Test Case ---
    personas = [Persona(**d) for d in persona_dicts]
    tc_agent = TestCaseAgent(llm, memory=ConversationMemory())
    tc_dicts = None
    guidance = ""

    while True:
        print("\nGenerating test cases...")
        results = run_async(tc_agent.run(personas, intents, guidance=guidance))
        if not results:
            print("No test cases generated. Try again.")
            return

        tc_dicts, action = review_test_cases(results)
        if action == "accept":
            break
        elif action == "export":
            break
        elif action.startswith("regenerate:"):
            guidance = action.split(":", 1)[1]
            tc_agent = TestCaseAgent(llm, memory=ConversationMemory())
            continue

    # --- Export ---
    if tc_dicts:
        export_results(tc_dicts, persona_dicts, intent_dicts)
        print_separator()
        print("DONE! Files saved: test_cases.csv, test_cases.md")


if __name__ == "__main__":
    main()
