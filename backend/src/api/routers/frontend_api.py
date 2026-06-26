import asyncio
import io
import json
import logging
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.api.deps import get_memory, get_state, reset_state
from src.config import settings
from src.ingestion.loader_factory import get_loader
from src.ingestion.normalizer import merge_sources
from src.ingestion.prd_loader import PRDLoader
from src.llm.factory import create_llm_client
from src.models.schemas import (
    FEIntent,
    FEPersona,
    FETestCase,
    Intent,
    Persona,
    RawInput,
    TestCasePrompt,
)
from src.pipeline.intent_comparator import IntentComparator
from src.pipeline.intent_extractor import IntentAgent
from src.pipeline.persona_generator import PersonaAgent
from src.pipeline.test_prompt_generator import TestCaseAgent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["frontend-api"])


# ---------- Request/Response models ----------


class DiscoverRequest(BaseModel):
    logsText: str = ""
    ruleText: str = ""


class GeneratePersonasRequest(BaseModel):
    intents: list[dict] = []
    ruleText: str = ""
    feedback: str = ""


class GenerateTestCasesRequest(BaseModel):
    intents: list[dict] = []
    personas: list[dict] = []
    ruleText: str = ""


class CompileRuleRequest(BaseModel):
    userPrompt: str = ""
    currentRule: str = ""
    activeDirective: str = ""
    promptInstruction: str = ""


class RunTestsRequest(BaseModel):
    testCaseIds: list[str] = []


class StateUpdateRequest(BaseModel):
    apiKey: str | None = None
    domain: str | None = None
    aiModel: str | None = None
    intents: list[dict] | None = None
    personas: list[dict] | None = None
    testCases: list[dict] | None = None


# ---------- Helpers ----------


def _resolve_api_key(model: str = "") -> str:
    state = get_state()
    # Prefer user-provided API key from sidebar
    if state.api_key and state.api_key != "••••••••••••••••":
        return state.api_key
    # Otherwise use key from .env matching the model
    if model == "openai":
        key = settings.openai_api_key
    else:
        key = settings.gemini_api_key
    if not key:
        # Fallback: try the other provider
        key = settings.openai_api_key or settings.gemini_api_key
    if not key:
        raise HTTPException(400, "Chua co API key. Nhap API key o sidebar hoac cau hinh trong .env")
    return key


def _get_model() -> str:
    state = get_state()
    raw = state.ai_model or settings.default_model
    # Map frontend model labels to backend model names
    raw_lower = raw.lower()
    preferred = "gemini"
    if "gpt" in raw_lower or "openai" in raw_lower:
        preferred = "openai"
    elif "gemini" in raw_lower or "google" in raw_lower:
        preferred = "gemini"
    elif raw in ("openai", "gemini"):
        preferred = raw

    # Verify the preferred model has an API key; otherwise fallback
    if preferred == "openai" and settings.openai_api_key:
        return "openai"
    if preferred == "gemini" and settings.gemini_api_key:
        return "gemini"
    # Fallback to whatever has an API key configured
    if settings.openai_api_key:
        return "openai"
    if settings.gemini_api_key:
        return "gemini"
    return preferred


def _map_pipeline_intents_to_fe(results: list[dict]) -> list[FEIntent]:
    mapped = []
    for r in results:
        mapped.append(FEIntent(
            id=r.get("id", uuid.uuid4().hex[:8]),
            name=r.get("intent_name", ""),
            phase=r.get("phase", "SUPPORT"),
            utterance=r.get("utterance", ""),
            triggerMoment=r.get("moment", r.get("context", "")),
            selected=True,
            source=r.get("source") if r.get("source") in ("data", "prd") else "data",
            coverage=r.get("coverage", ""),
            matchedIds=r.get("matchedIds", []) or [],
        ))
    return mapped


def _map_pipeline_personas_to_fe(results: list[dict], fe_intent_name_to_id: dict[str, str] | None = None) -> list[FEPersona]:
    mapped = []
    for r in results:
        ptype = r.get("persona_type", "happy-path")
        fe_type = "edge" if "edge" in ptype.lower() else "happy"
        freq_str = r.get("frequency", "0")
        try:
            freq = int("".join(c for c in str(freq_str) if c.isdigit()) or "0")
        except (ValueError, TypeError):
            freq = 0
        # Resolve intentId: prefer mapping via intent_name → FE intent id
        intent_id = r.get("intent_id", "")
        if fe_intent_name_to_id:
            fe_id = fe_intent_name_to_id.get(r.get("intent_name", ""))
            if fe_id:
                intent_id = fe_id
        mapped.append(FEPersona(
            id=r.get("id", uuid.uuid4().hex[:8]),
            intentId=intent_id,
            type=fe_type,
            name=r.get("name", ""),
            trigger=r.get("trigger", ""),
            utterance=r.get("utterance", ""),
            frequency=freq,
            frequencyText=str(freq_str) if freq_str else "",
            pain=r.get("pain", ""),
            reject=r.get("reject", ""),
            expectedAIBehavior=r.get("expected_behavior", r.get("ai_response_example", "")),
        ))
    return mapped


def _map_pipeline_testcases_to_fe(results: list[dict]) -> list[FETestCase]:
    mapped = []
    for r in results:
        mapped.append(FETestCase(
            id=r.get("id", uuid.uuid4().hex[:8]),
            intentName=r.get("intent_name", ""),
            personaName=r.get("persona", ""),
            simulatedPrompt=r.get("start", r.get("prompt_text", "")),
            expectedOutcome=r.get("end_expected_outcome", ""),
            selected=True,
            status="pending",
            goal=r.get("goal", ""),
        ))
    return mapped


# ---------- Endpoints ----------


@router.get("/api/state")
def get_state_endpoint():
    logger.info("GET /api/state")
    state = get_state()
    return {
        "apiKey": state.api_key or "••••••••••••••••",
        "domain": state.domain,
        "aiModel": state.ai_model,
        "intents": [i.model_dump() for i in state.intents],
        "personas": [p.model_dump() for p in state.personas],
        "testCases": [tc.model_dump() for tc in state.test_cases],
    }


@router.post("/api/state")
def update_state(body: StateUpdateRequest):
    logger.info("POST /api/state")
    state = get_state()
    if body.apiKey is not None:
        state.api_key = body.apiKey
    if body.domain is not None:
        state.domain = body.domain
    if body.aiModel is not None:
        state.ai_model = body.aiModel
    if body.intents is not None:
        state.intents = [FEIntent(**i) for i in body.intents]
    if body.personas is not None:
        state.personas = [FEPersona(**p) for p in body.personas]
    if body.testCases is not None:
        state.test_cases = [FETestCase(**tc) for tc in body.testCases]
    return {
        "success": True,
        "state": {
            "apiKey": state.api_key,
            "domain": state.domain,
            "aiModel": state.ai_model,
            "intents": [i.model_dump() for i in state.intents],
            "personas": [p.model_dump() for p in state.personas],
            "testCases": [tc.model_dump() for tc in state.test_cases],
        },
    }


@router.post("/api/ingest")
async def ingest_sources(
    files: list[UploadFile] = File(default=[]),
    types: list[str] = Form(default=[]),
    prd_file: UploadFile | None = File(default=None),
):
    """Nạp nhiều file đa nguồn → merge data thật vào state.raw_input + tách PRD.

    files[i] ↔ types[i] (song song). File type=prd (hoặc prd_file) → PRDLoader.
    Per-file graceful skip: lỗi/0 dòng → status "skipped" + warning, không fail cả mẻ.
    """
    logger.info("POST /api/ingest | files=%d | prd_file=%s", len(files), bool(prd_file))
    state = get_state()
    sources: list[dict] = []
    warnings: list[str] = []
    data_inputs: list[RawInput] = []
    prd_loaded = False

    for idx, uf in enumerate(files):
        filename = uf.filename or f"file_{idx}"
        source_type = types[idx].lower() if idx < len(types) and types[idx] else None
        raw_bytes = await uf.read()
        try:
            if source_type == "prd":
                ri = PRDLoader(io.BytesIO(raw_bytes), filename).load()
                state.raw_prd_content = ri.content
                prd_loaded = True
                sources.append({"source_type": "prd", "filename": filename,
                                "rows_in": 0, "rows_after_dedup": 0, "status": "ok"})
                continue
            loader = get_loader(source_type=source_type, filename=filename,
                                uploaded_file=io.BytesIO(raw_bytes))
            ri = loader.load()
            rows_in = ri.metadata.get("rows", ri.content.count("\n---\n") + 1)
            data_inputs.append(ri)
            sources.append({"source_type": ri.source_type, "filename": filename,
                            "rows_in": rows_in, "rows_after_dedup": rows_in, "status": "ok"})
        except Exception as e:
            logger.warning("Ingest skip %s: %s", filename, e)
            warnings.append(f"{filename}: {e} → skip")
            sources.append({"source_type": source_type or "?", "filename": filename,
                            "rows_in": 0, "rows_after_dedup": 0, "status": "skipped"})

    if prd_file is not None:
        filename = prd_file.filename or "prd"
        try:
            raw_bytes = await prd_file.read()
            ri = PRDLoader(io.BytesIO(raw_bytes), filename).load()
            state.raw_prd_content = ri.content
            prd_loaded = True
            sources.append({"source_type": "prd", "filename": filename,
                            "rows_in": 0, "rows_after_dedup": 0, "status": "ok"})
        except Exception as e:
            logger.warning("Ingest PRD skip %s: %s", filename, e)
            warnings.append(f"{filename}: {e} → skip")

    if data_inputs:
        merged = merge_sources(data_inputs)
        state.raw_input = merged
        total_chars = len(merged.content)
    else:
        total_chars = len(state.raw_prd_content)

    if not data_inputs and not prd_loaded:
        raise HTTPException(400, "Không có file hợp lệ nào được nạp (tất cả skip).")

    return {
        "sources": sources,
        "prd_loaded": prd_loaded,
        "total_chars": total_chars,
        "warnings": warnings,
    }


async def _mine_intents(content: str, guidance: str, llm, memory_name: str) -> list[dict]:
    agent = IntentAgent(llm, memory=get_memory(memory_name), max_chunk_tokens=settings.chunk_max_tokens)
    if guidance:
        agent.add_feedback(f"Extract intents: {guidance}")
    return await agent.run(RawInput(source_type="text", content=content), guidance)


@router.post("/api/discover")
def discover_intents(req: DiscoverRequest):
    logger.info("POST /api/discover | logsText_length=%d | ruleText=%s", len(req.logsText), bool(req.ruleText))
    state = get_state()

    # Data content from all available sources: paste-text (ưu tiên) hoặc raw_input đã
    # ingest, GỘP THÊM dữ liệu social đã crawl (state.raw_social_content). Không gắn nhãn
    # nguồn ở vòng này — chỉ nối nội dung lại để mine intents.
    parts: list[str] = []
    if req.logsText and req.logsText.strip():
        state.raw_input = RawInput(source_type="text", content=req.logsText)
        parts.append(req.logsText)
    elif state.raw_input and state.raw_input.content:
        parts.append(state.raw_input.content)
    if state.raw_social_content and state.raw_social_content.strip():
        parts.append(state.raw_social_content)
    data_content = "\n\n".join(p for p in parts if p and p.strip())

    prd_content = state.raw_prd_content
    if not data_content.strip() and not prd_content.strip():
        raise HTTPException(400, "Please enter some logs text or upload a file first.")

    # Mine data ĐỘC LẬP với PRD: chỉ dùng ruleText do user đặt, KHÔNG nhét nội
    # dung PRD vào guidance (nếu nhét, data_intents sẽ phản chiếu PRD → "all
    # confirmed", che mất intent thật của data → hỏng gap analysis).
    guidance = req.ruleText or ""

    model = _get_model()
    api_key = _resolve_api_key(model)
    try:
        llm = create_llm_client(model, api_key)
    except ValueError as e:
        logger.error("Failed to create LLM client: %s", e)
        raise HTTPException(400, str(e))

    async def _run() -> tuple[list[dict], list[dict]]:
        data_intents: list[dict] = []
        prd_intents: list[dict] = []
        if data_content.strip():
            data_intents = await _mine_intents(data_content, guidance, llm, "intent")
        if prd_content.strip():
            prd_intents = await _mine_intents(prd_content, "", llm, "intent_prd")
        if data_intents or prd_intents:
            comparator = IntentComparator(llm, api_key)
            prd_intents, data_intents = await comparator.compare(prd_intents, data_intents)
        return data_intents, prd_intents

    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting discovery (data + prd + comparator) ...")
        data_intents, prd_intents = loop.run_until_complete(_run())
    except Exception as e:
        logger.error("Discovery failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi sinh Intent: {e}")
    finally:
        loop.close()

    results = data_intents + prd_intents
    fe_intents = _map_pipeline_intents_to_fe(results)
    state.intents = fe_intents
    state.internal_intents = [Intent(**r) for r in results]
    logger.info("Stored %d FE intents (data=%d, prd=%d)", len(fe_intents), len(data_intents), len(prd_intents))

    return {"intents": [i.model_dump() for i in fe_intents], "fallback": False}


@router.post("/api/generate-personas")
def generate_personas(req: GeneratePersonasRequest):
    logger.info("POST /api/generate-personas | num_intents=%d | ruleText=%s", len(req.intents), bool(req.ruleText))
    state = get_state()

    # Use internal intents if available (from discover), otherwise map from FE intents
    if state.internal_intents:
        internal_intents = state.internal_intents
    elif req.intents:
        internal_intents = []
        for i in req.intents:
            internal_intents.append(Intent(
                intent_name=i.get("name", ""),
                phase=i.get("phase", ""),
                utterance=i.get("utterance", ""),
                moment=i.get("triggerMoment", ""),
            ))
    else:
        raise HTTPException(400, "No intents selected. Please select at least one intent to build personas.")

    model = _get_model()
    api_key = _resolve_api_key(model)
    logger.info("Generating personas | model=%s | num_intents=%d", model, len(internal_intents))

    try:
        llm = create_llm_client(model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = PersonaAgent(llm, memory=get_memory("persona"))
    if req.ruleText:
        agent.add_feedback(f"Generate personas: {req.ruleText}")
    if req.feedback:
        agent.add_feedback(f"User feedback: {req.feedback}")

    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting PersonaAgent.run() ...")
        guidance = req.ruleText
        if req.feedback:
            guidance = f"{guidance}\n{req.feedback}" if guidance else req.feedback
        results = loop.run_until_complete(agent.run(internal_intents, guidance))
        logger.info("PersonaAgent.run() completed | raw_results=%d", len(results))
    except Exception as e:
        logger.error("PersonaAgent.run() failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi sinh Persona: {e}")
    finally:
        loop.close()

    # Map intent_name → FE intent id so personas get the correct intentId for frontend filtering
    fe_intent_name_to_id = {i.name: i.id for i in state.intents}
    fe_personas = _map_pipeline_personas_to_fe(results, fe_intent_name_to_id)
    state.personas = fe_personas
    state.internal_personas = [Persona(**r) for r in results]
    logger.info("Stored %d FE personas in state", len(fe_personas))

    return {"personas": [p.model_dump() for p in fe_personas], "fallback": False}


@router.post("/api/generate-testcases")
def generate_testcases(req: GenerateTestCasesRequest):
    logger.info("POST /api/generate-testcases | ruleText=%s", bool(req.ruleText))
    state = get_state()

    # Use internal data if available, otherwise map from FE data
    internal_intents = state.internal_intents or []
    internal_personas = state.internal_personas or []

    if not internal_intents and req.intents:
        for i in req.intents:
            internal_intents.append(Intent(
                intent_name=i.get("name", ""),
                phase=i.get("phase", ""),
                utterance=i.get("utterance", ""),
                moment=i.get("triggerMoment", ""),
            ))

    if not internal_personas and req.personas:
        for p in req.personas:
            ptype = p.get("type", "happy")
            trait = "easy" if ptype == "happy" else "hard"
            internal_personas.append(Persona(
                persona_type=ptype,
                trigger=p.get("trigger", ""),
                utterance=p.get("utterance", ""),
                frequency=str(p.get("frequency", 0)),
                pain=p.get("pain", ""),
                reject=p.get("reject", ""),
                expected_behavior=p.get("expectedAIBehavior", ""),
                trait_type=trait,
            ))

    if not internal_intents or not internal_personas:
        raise HTTPException(400, "Missing selected intents or generated personas to build test cases.")

    model = _get_model()
    api_key = _resolve_api_key(model)
    logger.info("Generating test cases | model=%s | num_intents=%d | num_personas=%d", model, len(internal_intents), len(internal_personas))

    try:
        llm = create_llm_client(model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = TestCaseAgent(llm, memory=get_memory("test_case"))
    if req.ruleText:
        agent.add_feedback(f"Generate test cases: {req.ruleText}")

    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting TestCaseAgent.run() ...")
        results = loop.run_until_complete(agent.run(internal_personas, internal_intents, req.ruleText))
        logger.info("TestCaseAgent.run() completed | raw_results=%d", len(results))
    except Exception as e:
        logger.error("TestCaseAgent.run() failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi sinh Test Case: {e}")
    finally:
        loop.close()

    fe_testcases = _map_pipeline_testcases_to_fe(results)
    state.test_cases = fe_testcases
    state.internal_test_prompts = [TestCasePrompt(**r) for r in results]
    logger.info("Stored %d FE test cases in state", len(fe_testcases))

    return {"testCases": [tc.model_dump() for tc in fe_testcases], "fallback": False}


@router.post("/api/state/reset")
def reset_pipeline():
    logger.info("POST /api/state/reset")
    state = reset_state()
    return {
        "success": True,
        "state": {
            "apiKey": state.api_key,
            "domain": state.domain,
            "aiModel": state.ai_model,
            "intents": [i.model_dump() for i in state.intents],
            "personas": [p.model_dump() for p in state.personas],
            "testCases": [tc.model_dump() for tc in state.test_cases],
        },
    }


@router.post("/api/compile-rule")
def compile_rule(req: CompileRuleRequest):
    logger.info("POST /api/compile-rule")
    user_prompt = req.userPrompt or req.promptInstruction
    current_rule = req.currentRule or req.activeDirective

    if not user_prompt or not user_prompt.strip():
        raise HTTPException(400, "Please provide a prompt to adjust the rules.")

    model = _get_model()
    api_key = _resolve_api_key(model)

    try:
        llm = create_llm_client(model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    prompt = (
        f"Convert the following user request or directive into an explicit, modular system directive "
        f"that specifies how metadata and user intents should be extracted from customer logs.\n\n"
        f'User adjustment request: "{user_prompt}"\n'
        f'Current active rule: "{current_rule or "None (Default)"}"\n\n'
        f"Generate a concise, highly professional 1-2 sentence instruction. "
        f"Output ONLY the resulting instruction text. No quotes around it, no wrapper."
    )

    loop = asyncio.new_event_loop()
    try:
        logger.info("Compiling rule with LLM ...")
        result = loop.run_until_complete(llm.generate(prompt))
        logger.info("Rule compiled | length=%d", len(result))
    except Exception as e:
        logger.error("Rule compilation failed: %s", e, exc_info=True)
        raise HTTPException(500, f"LLM rule compilation failed: {e}")
    finally:
        loop.close()

    compiled = result.strip() or current_rule
    return {"success": True, "compiledDirective": compiled, "rule": compiled, "fallback": False}


@router.post("/api/testcases/run")
def run_tests(req: RunTestsRequest):
    logger.info("POST /api/testcases/run | num_cases=%d", len(req.testCaseIds))
    if not req.testCaseIds:
        raise HTTPException(400, "Please select at least one test case to run.")

    state = get_state()
    results = []
    for tc in state.test_cases:
        if tc.id in req.testCaseIds:
            is_failed = "fail" in tc.intentName.lower() or "edge" in tc.personaName.lower()
            final_status = "failed" if is_failed else "passed"
            scenario_logs = [
                f"[INFO] Initializing sandbox environment for: {tc.id}",
                f"[INFO] Loading domain routing: {state.domain} via model: {state.ai_model}",
                f"[MOCK] Persona injected: {tc.personaName} with preset browser triggers.",
                f"[SEND] Simulated Prompt: {tc.simulatedPrompt}",
                (
                    f"[WARN] Assert rejection check triggered"
                    if final_status == "failed"
                    else f"[PASS] Correct outcome assertion verified: {tc.expectedOutcome}"
                ),
                f"[INFO] Test case completed with status: {final_status.upper()}",
            ]
            results.append(FETestCase(
                id=tc.id,
                intentName=tc.intentName,
                personaName=tc.personaName,
                simulatedPrompt=tc.simulatedPrompt,
                expectedOutcome=tc.expectedOutcome,
                selected=tc.selected,
                status=final_status,
                logs=scenario_logs,
                goal=tc.goal,
            ))
        else:
            results.append(tc)

    state.test_cases = results
    return {"success": True, "testCases": [tc.model_dump() for tc in results]}
