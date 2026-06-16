import asyncio

import pandas as pd
import streamlit as st

from src.config import settings
from src.export.exporter import Exporter
from src.ingestion.csv_loader import CSVLoader
from src.ingestion.text_loader import TextLoader
from src.llm.factory import create_llm_client
from src.models.schemas import Intent, Persona, PipelineState
from src.pipeline.intent_extractor import IntentExtractor
from src.pipeline.persona_generator import PersonaGenerator
from src.pipeline.test_prompt_generator import TestCasePromptGenerator


def init_state():
    if "pipeline_state" not in st.session_state:
        st.session_state.pipeline_state = PipelineState()


def get_llm():
    model = st.session_state.get("llm_model", settings.default_model)
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        st.error("Vui lòng nhập API Key ở sidebar.")
        return None
    try:
        return create_llm_client(model, api_key)
    except Exception as e:
        st.error(f"Lỗi khởi tạo LLM client: {e}")
        return None


def render_sidebar():
    with st.sidebar:
        st.header("Cài đặt LLM")
        model = st.selectbox(
            "Model", ["gemini", "openai"], index=0 if settings.default_model == "gemini" else 1
        )
        st.session_state.llm_model = model

        placeholder = "Nhập Gemini API Key" if model == "gemini" else "Nhập OpenAI API Key"
        api_key = st.text_input("API Key", type="password", placeholder=placeholder)
        st.session_state.api_key = api_key

        st.divider()
        st.header("Pipeline State")
        state = st.session_state.pipeline_state
        st.write(f"Bước hiện tại: **{state.current_step}** / 3")
        st.write(f"Intents: {len([i for i in state.intents if i.status != 'deleted'])}")
        st.write(f"Personas: {len([p for p in state.personas if p.status != 'deleted'])}")
        st.write(f"Test Prompts: {len([t for t in state.test_prompts if t.status != 'deleted'])}")

        if st.button("Reset toàn bộ", type="secondary"):
            st.session_state.pipeline_state = PipelineState()
            st.rerun()


def step_input():
    st.header("Bước 0: Nhập dữ liệu")

    tab_csv, tab_text = st.tabs(["Upload CSV", "Paste Text"])

    with tab_csv:
        csv_file = st.file_uploader("Chọn file CSV", type=["csv"])
        if csv_file and st.button("Tải CSV", key="load_csv"):
            try:
                loader = CSVLoader(csv_file, filename=csv_file.name)
                st.session_state.pipeline_state.raw_input = loader.load()
                st.success(f"Đã tải {csv_file.name} thành công!")
            except Exception as e:
                st.error(f"Lỗi đọc CSV: {e}")

    with tab_text:
        text_input = st.text_area("Dán text thô vào đây", height=300)
        if st.button("Tải Text", key="load_text"):
            try:
                loader = TextLoader(text_input)
                st.session_state.pipeline_state.raw_input = loader.load()
                st.success("Đã tải text thành công!")
            except Exception as e:
                st.error(f"Lỗi: {e}")

    state = st.session_state.pipeline_state
    if state.raw_input:
        st.info(f"Đã có dữ liệu: **{state.raw_input.source_type}** — {len(state.raw_input.content)} ký tự")
        if st.button("Phân tích Intent →", type="primary"):
            st.session_state.pipeline_state.current_step = 1
            st.rerun()


def step_intent():
    st.header("Bước 1: Khai phá Intent")

    state = st.session_state.pipeline_state

    if not state.intents:
        with st.spinner("Đang phân tích Intent..."):
            llm = get_llm()
            if llm:
                extractor = IntentExtractor(llm, max_chunk_tokens=settings.chunk_max_tokens)
                loop = asyncio.new_event_loop()
                try:
                    intents = loop.run_until_complete(extractor.extract(state.raw_input))
                    st.session_state.pipeline_state.intents = intents
                except Exception as e:
                    st.error(f"Lỗi sinh Intent: {e}")
                finally:
                    loop.close()

    intents = [i for i in state.intents if i.status != "deleted"]
    if intents:
        df = pd.DataFrame([
            {"id": i.id, "Bối cảnh": i.context, "Mục tiêu": i.goal, "Trạng thái": i.status}
            for i in intents
        ])
        st.subheader("Danh sách Intent")
        edited_df = st.data_editor(df, num_rows="dynamic", key="intent_editor")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Lưu chỉnh sửa Intent"):
                _save_intent_edits(edited_df)
                st.success("Đã lưu!")
        with col2:
            guidance = st.text_input("Hướng dẫn Regenerate (VD: Thêm intent về...)", key="intent_guidance")
            if st.button("Regenerate Intent"):
                llm = get_llm()
                if llm:
                    extractor = IntentExtractor(llm, max_chunk_tokens=settings.chunk_max_tokens)
                    loop = asyncio.new_event_loop()
                    try:
                        new_intents = loop.run_until_complete(
                            extractor.regenerate(state.intents, state.raw_input, guidance)
                        )
                        st.session_state.pipeline_state.intents = new_intents
                        st.success("Đã regenerate!")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                    finally:
                        loop.close()
        with col3:
            if st.button("Chốt Intent → Sinh Persona", type="primary"):
                _approve_intents()
                st.session_state.pipeline_state.current_step = 2
                st.rerun()


def step_persona():
    st.header("Bước 2: Tạo Persona")

    state = st.session_state.pipeline_state
    approved_intents = [i for i in state.intents if i.status != "deleted"]

    if not state.personas and approved_intents:
        with st.spinner("Đang sinh Persona..."):
            llm = get_llm()
            if llm:
                generator = PersonaGenerator(llm)
                loop = asyncio.new_event_loop()
                try:
                    personas = loop.run_until_complete(generator.generate(approved_intents))
                    st.session_state.pipeline_state.personas = personas
                except Exception as e:
                    st.error(f"Lỗi sinh Persona: {e}")
                finally:
                    loop.close()

    personas = [p for p in state.personas if p.status != "deleted"]
    if personas:
        intent_map = {i.id: i for i in state.intents}
        df = pd.DataFrame([
            {
                "id": p.id,
                "Intent": intent_map.get(p.intent_id, Persona(intent_id="", name="", description="", trait_type="")).goal[:50] if p.intent_id in intent_map else "N/A",
                "Tên Persona": p.name,
                "Mô tả": p.description,
                "Loại": p.trait_type,
                "Trạng thái": p.status,
            }
            for p in personas
        ])
        st.subheader("Danh sách Persona")
        edited_df = st.data_editor(df, num_rows="dynamic", key="persona_editor")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Lưu chỉnh sửa Persona"):
                _save_persona_edits(edited_df)
                st.success("Đã lưu!")
        with col2:
            guidance = st.text_input("Hướng dẫn Regenerate", key="persona_guidance")
            if st.button("Regenerate Persona"):
                llm = get_llm()
                if llm:
                    generator = PersonaGenerator(llm)
                    loop = asyncio.new_event_loop()
                    try:
                        new_personas = loop.run_until_complete(
                            generator.generate(approved_intents, guidance)
                        )
                        st.session_state.pipeline_state.personas = new_personas
                        st.success("Đã regenerate!")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                    finally:
                        loop.close()
        with col3:
            if st.button("Chốt Persona → Sinh Test Prompt", type="primary"):
                st.session_state.pipeline_state.current_step = 3
                st.rerun()


def step_test_prompt():
    st.header("Bước 3: Sinh Test Prompt")

    state = st.session_state.pipeline_state
    approved_intents = [i for i in state.intents if i.status != "deleted"]
    approved_personas = [p for p in state.personas if p.status != "deleted"]

    if not state.test_prompts and approved_intents and approved_personas:
        with st.spinner("Đang sinh Test Prompt..."):
            llm = get_llm()
            if llm:
                generator = TestCasePromptGenerator(llm)
                loop = asyncio.new_event_loop()
                try:
                    prompts = loop.run_until_complete(
                        generator.generate(approved_intents, approved_personas)
                    )
                    st.session_state.pipeline_state.test_prompts = prompts
                except Exception as e:
                    st.error(f"Lỗi sinh Test Prompt: {e}")
                finally:
                    loop.close()

    prompts = [t for t in state.test_prompts if t.status != "deleted"]
    if prompts:
        intent_map = {i.id: i for i in state.intents}
        persona_map = {p.id: p for p in state.personas}
        df = pd.DataFrame([
            {
                "id": t.id,
                "Intent": intent_map.get(t.intent_id, Intent(context="", goal="")).goal[:40] if t.intent_id in intent_map else "N/A",
                "Persona": persona_map.get(t.persona_id, Persona(intent_id="", name="", description="", trait_type="")).name if t.persona_id in persona_map else "N/A",
                "Test Prompt": t.prompt_text,
                "Trạng thái": t.status,
            }
            for t in prompts
        ])
        st.subheader("Danh sách Test Prompt")
        edited_df = st.data_editor(df, num_rows="dynamic", key="prompt_editor", use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Lưu chỉnh sửa Test Prompt"):
                _save_prompt_edits(edited_df)
                st.success("Đã lưu!")
        with col2:
            guidance = st.text_input("Hướng dẫn Regenerate", key="prompt_guidance")
            if st.button("Regenerate Test Prompt"):
                llm = get_llm()
                if llm:
                    generator = TestCasePromptGenerator(llm)
                    loop = asyncio.new_event_loop()
                    try:
                        new_prompts = loop.run_until_complete(
                            generator.generate(approved_intents, approved_personas, guidance)
                        )
                        st.session_state.pipeline_state.test_prompts = new_prompts
                        st.success("Đã regenerate!")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                    finally:
                        loop.close()

        st.divider()
        st.subheader("Export")
        col_csv, col_md = st.columns(2)
        with col_csv:
            if st.button("Export CSV"):
                csv_data = Exporter.to_csv(
                    state.test_prompts, state.intents, state.personas
                )
                st.download_button(
                    "Tải CSV", csv_data, "test_cases.csv", "text/csv"
                )
        with col_md:
            if st.button("Export Markdown"):
                md_data = Exporter.to_markdown(
                    state.test_prompts, state.intents, state.personas
                )
                st.download_button(
                    "Tải Markdown", md_data, "test_cases.md", "text/markdown"
                )


def _save_intent_edits(edited_df: pd.DataFrame):
    state = st.session_state.pipeline_state
    intent_map = {i.id: i for i in state.intents}
    for _, row in edited_df.iterrows():
        intent_id = row.get("id")
        if intent_id and intent_id in intent_map:
            intent = intent_map[intent_id]
            intent.context = row.get("Bối cảnh", intent.context)
            intent.goal = row.get("Mục tiêu", intent.goal)
            intent.status = "edited"


def _save_persona_edits(edited_df: pd.DataFrame):
    state = st.session_state.pipeline_state
    persona_map = {p.id: p for p in state.personas}
    for _, row in edited_df.iterrows():
        persona_id = row.get("id")
        if persona_id and persona_id in persona_map:
            persona = persona_map[persona_id]
            persona.name = row.get("Tên Persona", persona.name)
            persona.description = row.get("Mô tả", persona.description)
            persona.trait_type = row.get("Loại", persona.trait_type)
            persona.status = "edited"


def _save_prompt_edits(edited_df: pd.DataFrame):
    state = st.session_state.pipeline_state
    prompt_map = {t.id: t for t in state.test_prompts}
    for _, row in edited_df.iterrows():
        prompt_id = row.get("id")
        if prompt_id and prompt_id in prompt_map:
            prompt = prompt_map[prompt_id]
            prompt.prompt_text = row.get("Test Prompt", prompt.prompt_text)
            prompt.status = "edited"


def _approve_intents():
    for intent in st.session_state.pipeline_state.intents:
        if intent.status == "generated":
            intent.status = "approved"


STEPS = [step_input, step_intent, step_persona, step_test_prompt]


def main():
    st.set_page_config(page_title="AI Test Case Generator", layout="wide")
    st.title("AI Test Case Generator")

    init_state()
    render_sidebar()

    state = st.session_state.pipeline_state
    step_idx = min(state.current_step, len(STEPS) - 1)

    progress = st.progress(step_idx / (len(STEPS) - 1))
    step_labels = ["Nhập liệu", "Intent", "Persona", "Test Prompt"]
    st.markdown(" → ".join(
        f"**{label}**" if i == step_idx else label
        for i, label in enumerate(step_labels)
    ))

    STEPS[step_idx]()


if __name__ == "__main__":
    main()
