import asyncio
import hashlib
import io
import json
import logging
import re
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.api.deps import get_memory, get_state, reset_state
from src.crawlers.crawl_persist import sync_social_content_to_state
from src.crawlers.crawl_store import load_posts as load_crawl_posts
from src.config import settings
from src.ingestion.loader_factory import get_loader
from src.ingestion.normalizer import merge_sources
from src.ingestion.prd_loader import PRDLoader
from src.llm.factory import create_llm_client
from src.observability.langfuse import flush_langfuse
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
from src.prompts.loader import INTENT_PRD_SYSTEM, INTENT_PRD_USER
from src.pipeline.persona_generator import PersonaAgent
from src.pipeline.test_prompt_generator import TestCaseAgent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["frontend-api"])


# ---------- Request/Response models ----------


class DiscoverRequest(BaseModel):
    logsText: str = ""
    ruleText: str = ""
    scope: str = "both"  # "data" | "prd" | "both"


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


_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _tokens(s: str) -> set[str]:
    """Token hoá thô (lowercase, bỏ từ 1 ký tự) để so khớp độ trùng."""
    return {t for t in _WORD_RE.findall((s or "").lower()) if len(t) >= 2}


def _attribute_source_posts(data_intents: list[dict]) -> None:
    """Mutate mỗi data intent: gắn source_posts từ crawl_posts.json.

    So khớp CHÍNH XÁC (substring) hay hỏng vì LLM thường paraphrase raw_observation.
    → Dùng fuzzy: độ chứa token của intent trong post (containment), cộng điểm mạnh
    nếu trùng nguyên văn. Lấy tối đa 3 post điểm cao nhất vượt ngưỡng.
    """
    all_posts = load_crawl_posts()
    if not all_posts:
        return
    # Tiền token hoá post 1 lần.
    post_toks = [(_tokens(p.get("text") or ""), p) for p in all_posts]

    THRESHOLD = 0.45  # ≥45% token đặc trưng của intent xuất hiện trong post (chặn trùng vu vơ)
    for intent in data_intents:
        raw_obs = (intent.get("raw_observation") or "").strip()
        utterance = (intent.get("utterance") or "").strip()
        # Ưu tiên raw_observation (gần với câu trong post); chỉ thêm utterance khi quá ngắn.
        query = _tokens(raw_obs)
        if len(query) < 3:
            query |= _tokens(utterance)
        if len(query) < 3:
            intent["source_posts"] = []
            continue

        ro_low = raw_obs.lower()
        scored: list[tuple[float, dict]] = []
        for toks, post in post_toks:
            if not toks:
                continue
            inter = len(query & toks)
            if inter == 0:
                continue
            score = inter / len(query)
            # Trùng nguyên văn = bằng chứng chắc chắn → cộng điểm để luôn xếp đầu.
            if len(ro_low) > 10 and ro_low in (post.get("text") or "").lower():
                score += 1.0
            scored.append((score, post))

        scored.sort(key=lambda x: x[0], reverse=True)
        matched = []
        for score, post in scored:
            if score < THRESHOLD:
                break
            matched.append({
                "url": post.get("url", ""),
                "username": post.get("username", ""),
                "platform": post.get("platform", ""),
                "textExcerpt": (post.get("text") or "")[:250],
            })
            if len(matched) >= 3:
                break
        intent["source_posts"] = matched


def _map_pipeline_intents_to_fe(results: list[dict]) -> list[FEIntent]:
    mapped = []
    for r in results:
        source = r.get("source") if r.get("source") in ("data", "prd", "prd_inferred") else "data"
        # raw_observation chỉ là trích dẫn PRD khi source == "prd"; với data nó là
        # quote từ social, với prd_inferred thì rỗng → không nhồi vào prdSource.
        prd_quote = (r.get("raw_observation") or "") if source == "prd" else ""
        mapped.append(FEIntent(
            id=r.get("id", uuid.uuid4().hex[:8]),
            name=r.get("intent_name", ""),
            phase=r.get("phase", "SUPPORT"),
            utterance=r.get("utterance", ""),
            triggerMoment=r.get("moment", r.get("context", "")),
            selected=True,
            source=source,
            coverage=r.get("coverage", ""),
            matchedIds=r.get("matchedIds", []) or [],
            sourcePosts=r.get("source_posts") or [],
            prdSource=prd_quote,
            sources=[source],
            prdSources=[prd_quote] if prd_quote else [],
        ))
    return mapped


def _build_merged_intents(prd_pool: list[FEIntent], data_pool: list[FEIntent]) -> list[FEIntent]:
    """Gộp các cụm PRD↔DATA đã match (confirmed) thành 1 intent.

    - Đồ thị: node = mọi FEIntent; cạnh = matchedIds (chỉ giữ cạnh trỏ tới id tồn tại).
    - Connected components (BFS). Cụm có cả PRD lẫn DATA → gộp 1 dòng; cụm 1 phía → giữ nguyên.
    - Dòng gộp lấy field từ DATA member nhiều sourcePosts nhất; cite cắt ≤3 post + ≤3 PRD quote.
    PRD/data pool gốc KHÔNG bị đụng — đây chỉ là phép chiếu tạo state.intents.
    """
    all_intents = list(prd_pool) + list(data_pool)
    by_id: dict[str, FEIntent] = {it.id: it for it in all_intents}

    # Adjacency 2 chiều, chỉ giữ cạnh hợp lệ (id đối tác tồn tại).
    adj: dict[str, set[str]] = {it.id: set() for it in all_intents}
    for it in all_intents:
        for mid in it.matchedIds or []:
            if mid in by_id:
                adj[it.id].add(mid)
                adj[mid].add(it.id)

    def _is_prd(it: FEIntent) -> bool:
        return it.source in ("prd", "prd_inferred")

    seen: set[str] = set()
    merged: list[FEIntent] = []
    # Giữ thứ tự ổn định theo all_intents (PRD trước, data sau).
    for start in all_intents:
        if start.id in seen:
            continue
        # BFS lấy component.
        comp_ids: list[str] = []
        queue = [start.id]
        seen.add(start.id)
        while queue:
            cur = queue.pop()
            comp_ids.append(cur)
            for nxt in adj[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        members = [by_id[i] for i in comp_ids]
        prd_members = [m for m in members if _is_prd(m)]
        data_members = [m for m in members if not _is_prd(m)]

        # Cụm 1 phía (chỉ PRD hoặc chỉ DATA) → giữ nguyên từng member.
        if not prd_members or not data_members:
            merged.extend(members)
            continue

        # Cụm gộp: primary = DATA nhiều sourcePosts nhất (tie → đầu tiên).
        primary = max(data_members, key=lambda m: len(m.sourcePosts or []))
        labels: list[str] = []
        for m in members:
            if m.source not in labels:
                labels.append(m.source)

        prd_quotes: list[str] = []
        for m in prd_members:
            for q in (m.prdSources or ([m.prdSource] if m.prdSource else [])):
                if q and q not in prd_quotes:
                    prd_quotes.append(q)

        posts: list[dict] = []
        seen_posts: set[str] = set()
        for m in data_members:
            for p in m.sourcePosts or []:
                key = p.get("url") or p.get("textExcerpt") or ""
                if key and key not in seen_posts:
                    seen_posts.add(key)
                    posts.append(p)

        merged.append(primary.model_copy(update={
            "source": "data",
            "sources": labels,
            "coverage": "confirmed",
            "prdSource": prd_quotes[0] if prd_quotes else "",
            "prdSources": prd_quotes[:3],
            "sourcePosts": posts[:3],
            "matchedIds": [],
        }))

    return merged


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
            name=r.get("persona_type", "") or r.get("name", ""),
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
        "prdLoaded": bool(state.raw_prd_content.strip()),
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


async def _mine_intents(content: str, guidance: str, llm, memory_name: str, trace_id: str | None = None) -> list[dict]:
    agent = IntentAgent(llm, memory=get_memory(memory_name), max_chunk_tokens=settings.chunk_max_tokens)
    if guidance:
        agent.add_feedback(f"Extract intents: {guidance}")
    return await agent.run(RawInput(source_type="text", content=content), guidance, trace_id=trace_id)


async def _mine_prd_intents(content: str, llm, memory_name: str, trace_id: str | None = None) -> list[dict]:
    agent = IntentAgent(llm, memory=get_memory(memory_name), max_chunk_tokens=settings.chunk_max_tokens, system_prompt=INTENT_PRD_SYSTEM, user_template=INTENT_PRD_USER)
    logger.info("_mine_prd_intents | user_template_preview=%s", INTENT_PRD_USER[:60].replace('\n', ' '))
    return await agent.run(RawInput(source_type="text", content=content), "", trace_id=trace_id)


def _replace_pool(old_pool: list[FEIntent], new_pool: list[FEIntent]) -> list[FEIntent]:
    """Thay toàn bộ pool (dùng cho PRD), giữ selected/phase/id cho intent trùng tên."""
    old_map = {i.name.lower().strip(): i for i in old_pool}
    result = []
    for intent in new_pool:
        key = intent.name.lower().strip()
        if key in old_map:
            old = old_map[key]
            intent = intent.model_copy(update={"selected": old.selected, "phase": old.phase, "id": old.id})
        result.append(intent)
    return result


def _append_pool(old_pool: list[FEIntent], new_pool: list[FEIntent]) -> list[FEIntent]:
    """Append vào pool (dùng cho data/crawl): cập nhật coverage cho intent đã có, thêm intent mới vào cuối."""
    old_map = {i.name.lower().strip(): i for i in old_pool}
    result = []
    # Giữ existing, cập nhật coverage/matchedIds từ run mới nếu có
    for old_intent in old_pool:
        key = old_intent.name.lower().strip()
        matching = next((i for i in new_pool if i.name.lower().strip() == key), None)
        if matching:
            result.append(matching.model_copy(update={"selected": old_intent.selected, "phase": old_intent.phase, "id": old_intent.id}))
        else:
            result.append(old_intent)
    # Thêm intent hoàn toàn mới
    for intent in new_pool:
        if intent.name.lower().strip() not in old_map:
            result.append(intent)
    return result


@router.post("/api/discover")
def discover_intents(req: DiscoverRequest):
    logger.info("POST /api/discover | logsText_length=%d | ruleText=%s", len(req.logsText), bool(req.ruleText))
    state = get_state()

    # Data content from all available sources: paste-text (ưu tiên) hoặc raw_input đã
    # ingest, GỘP THÊM dữ liệu social đã crawl (state.raw_social_content). Không gắn nhãn
    # nguồn ở vòng này — chỉ nối nội dung lại để mine intents.
    if not state.raw_social_content.strip():
        sync_social_content_to_state()

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

    # Scope: tách 2 luồng discovery (Data / PRD) — chỉ chạy đúng luồng user chọn.
    scope = req.scope if req.scope in ("data", "prd", "both") else "both"
    run_data = scope in ("data", "both")
    run_prd = scope in ("prd", "both")
    run_compare = scope == "both"

    if scope == "data" and not data_content.strip():
        raise HTTPException(
            400,
            "No crawl/data found. Crawl social data, upload a file, or paste text first.",
        )
    if scope == "prd" and not prd_content.strip():
        raise HTTPException(400, "No PRD loaded. Upload a PRD first.")
    if not data_content.strip() and not prd_content.strip():
        raise HTTPException(
            400,
            "No input data found. Upload a file, paste text, or crawl social data first.",
        )

    if not state.trace_id:
        state.trace_id = uuid.uuid4().hex

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

    prd_hash = hashlib.md5(prd_content.encode()).hexdigest() if prd_content.strip() else ""
    prd_changed = prd_hash != state.prd_content_hash

    async def _run() -> tuple[list[dict], list[dict]]:
        data_intents: list[dict] = []
        prd_intents: list[dict] = []
        if run_data and data_content.strip():
            data_intents = await _mine_intents(data_content, guidance, llm, "intent", trace_id=state.trace_id)
            _attribute_source_posts(data_intents)
        if run_prd and prd_content.strip():
            if prd_changed or not state.cached_prd_internal:
                logger.info("PRD changed or no cache — re-extracting PRD intents")
                prd_intents = await _mine_prd_intents(prd_content, llm, "intent_prd", trace_id=state.trace_id)
                state.cached_prd_internal = [Intent(**r) for r in prd_intents]
                state.prd_content_hash = prd_hash
            else:
                logger.info("PRD unchanged — using cached PRD intents (count=%d)", len(state.cached_prd_internal))
                prd_intents = [i.model_dump() for i in state.cached_prd_internal]
        if run_compare and (data_intents or prd_intents):
            # provider=model để embedding (gap analysis) dùng đúng API + key của LLM đang chọn.
            comparator = IntentComparator(llm, api_key, provider=model)
            prd_intents, data_intents = await comparator.compare(prd_intents, data_intents)
        return data_intents, prd_intents

    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting discovery | scope=%s ...", scope)
        data_intents, prd_intents = loop.run_until_complete(_run())
    except Exception as e:
        logger.error("Discovery failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi sinh Intent: {e}")
    finally:
        loop.close()
        flush_langfuse()

    new_prd_fe = _map_pipeline_intents_to_fe(prd_intents)
    new_data_fe = _map_pipeline_intents_to_fe(data_intents)

    if new_prd_fe:
        state.prd_intents = _replace_pool(state.prd_intents, new_prd_fe)
    if new_data_fe:
        state.data_intents = _append_pool(state.data_intents, new_data_fe)

    # Gộp các cụm PRD↔DATA đã match thành 1 dòng (phép chiếu — KHÔNG đụng 2 pool gốc).
    state.intents = _build_merged_intents(state.prd_intents, state.data_intents)

    # internal_intents phải khớp 1:1 với state.intents theo id để persona/test-case dùng
    # đúng intent đã gộp (sinh 1 bộ persona thay vì trùng). Lấy raw_observation/why_valid
    # từ dict nội bộ của run này nếu khớp id, còn lại suy từ FEIntent.
    internal_by_id = {r["id"]: r for r in prd_intents + data_intents}
    state.internal_intents = [
        Intent(
            id=fe.id,
            intent_name=fe.name,
            utterance=fe.utterance,
            moment=fe.triggerMoment,
            phase=fe.phase,
            source=fe.source,
            raw_observation=(internal_by_id.get(fe.id, {}).get("raw_observation") or fe.prdSource or ""),
            why_valid=internal_by_id.get(fe.id, {}).get("why_valid", ""),
        )
        for fe in state.intents
    ]
    logger.info("Stored %d FE intents (data=%d, prd=%d)", len(state.intents), len(data_intents), len(prd_intents))
    if not state.intents:
        logger.warning(
            "Discovery returned 0 intents | data_chars=%d | prd_chars=%d | social_chars=%d",
            len(data_content),
            len(prd_content),
            len(state.raw_social_content or ""),
        )

    return {"intents": [i.model_dump() for i in state.intents], "fallback": False}


@router.post("/api/generate-personas")
def generate_personas(req: GeneratePersonasRequest):
    logger.info("POST /api/generate-personas | num_intents=%d | ruleText=%s", len(req.intents), bool(req.ruleText))
    state = get_state()
    if not state.trace_id:
        state.trace_id = uuid.uuid4().hex

    # Use internal intents if available (from discover), otherwise map from FE intents
    if state.internal_intents:
        internal_intents = state.internal_intents
        # Respect the user's selection: the FE sends only the intents the user checked.
        # Without this filter we'd build personas for EVERY discovered intent (e.g. 6 -> 12
        # personas) and the FE would silently hide the ones not selected — wasting tokens
        # and showing a misleading count. Match by id (internal_intents[].id == FE intent id).
        selected_ids = {i.get("id") for i in req.intents if i.get("id")}
        if selected_ids:
            filtered = [i for i in internal_intents if i.id in selected_ids]
            if filtered:
                internal_intents = filtered
        logger.info(
            "generate_personas | selected_ids=%d | internal_intents used=%d (of %d discovered)",
            len(selected_ids), len(internal_intents), len(state.internal_intents),
        )
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
        results, failure_summary = loop.run_until_complete(
            agent.run_with_diagnostics(internal_intents, guidance, trace_id=state.trace_id)
        )
        logger.info("PersonaAgent.run() completed | raw_results=%d | unresolved=%d", len(results), len(failure_summary))
    except Exception as e:
        logger.error("PersonaAgent.run() failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi sinh Persona: {e}")
    finally:
        loop.close()
        flush_langfuse()

    # Map intent_name → FE intent id so personas get the correct intentId for frontend filtering
    fe_intent_name_to_id = {i.name: i.id for i in state.intents}
    fe_personas = _map_pipeline_personas_to_fe(results, fe_intent_name_to_id)
    state.personas = fe_personas
    state.internal_personas = [Persona(**r) for r in results]
    logger.info("Stored %d FE personas in state", len(fe_personas))

    # The generate/evaluate/refine loop (persona_graph.py) tracks the best-scoring attempt
    # per intent across iterations and gives up after max_iterations rather than erroring —
    # any intent still unresolved at that point shows up in failure_summary, with the
    # highest-scoring pair it ever produced (possibly none, if every attempt failed to parse).
    intent_num_to_name = {i.intent_num or idx + 1: i.intent_name for idx, i in enumerate(internal_intents)}
    persona_issues: dict[str, dict] = {}
    short_names: list[str] = []
    for entry in failure_summary:
        inum = entry.get("intent_num")
        name = intent_num_to_name.get(inum, "")
        fe_id = fe_intent_name_to_id.get(name)
        if not fe_id:
            continue
        short_names.append(name)
        fixes = entry.get("fixes", [])
        issues = entry.get("issues", [])
        reason = (
            f"Chưa đạt rubric sau {entry.get('iteration', 0)}/5 vòng thử "
            f"({entry.get('score', 0)}/{entry.get('max_score', 28)} điểm)."
        )
        persona_issues[fe_id] = {
            "score": entry.get("score", 0),
            "maxScore": entry.get("max_score", 28),
            "reason": reason,
            "fixes": [*fixes, *issues],
        }

    warning = None
    if short_names:
        warning = (
            f"{len(short_names)} intent(s) couldn't be fully completed after retries: "
            f"{', '.join(short_names)}. Showing the best attempt for each — try again or adjust the intent."
        )
        logger.warning("Persona generation incomplete | %s", warning)

    return {
        "personas": [p.model_dump() for p in fe_personas],
        "fallback": False,
        "warning": warning,
        "personaIssues": persona_issues,
    }


@router.post("/api/generate-testcases")
def generate_testcases(req: GenerateTestCasesRequest):
    logger.info("POST /api/generate-testcases | ruleText=%s", bool(req.ruleText))
    state = get_state()
    if not state.trace_id:
        state.trace_id = uuid.uuid4().hex

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
        results = loop.run_until_complete(agent.run(internal_personas, internal_intents, req.ruleText, trace_id=state.trace_id))
        logger.info("TestCaseAgent.run() completed | raw_results=%d", len(results))
    except Exception as e:
        logger.error("TestCaseAgent.run() failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi sinh Test Case: {e}")
    finally:
        loop.close()
        flush_langfuse()

    fe_testcases = _map_pipeline_testcases_to_fe(results)
    state.test_cases = fe_testcases
    state.internal_test_prompts = [TestCasePrompt(**r) for r in results]
    logger.info("Stored %d FE test cases in state", len(fe_testcases))

    return {"testCases": [tc.model_dump() for tc in fe_testcases], "fallback": False}


@router.post("/api/state/reset")
def reset_pipeline():
    logger.info("POST /api/state/reset")
    state = reset_state()
    # Keep persisted crawl sheet; only rehydrate in-memory social content for /api/discover.
    sync_social_content_to_state()
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
