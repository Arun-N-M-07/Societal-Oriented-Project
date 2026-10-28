import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    ProvenanceError,
    check_admin_credentials,
    create_session_token,
    issue_provenance_token,
    login_blocked,
    record_login,
    require_admin,
    verify_provenance_token,
)
from backend.config import COOKIE_SECURE, EMBEDDING_MODEL, LLM_MODEL, OLLAMA_BASE_URL
from backend.database import get_db, get_read_only_db
from backend.extractor import ExtractionError, extract_procedure
from backend.models import Procedure
from backend.normalize import needs_normalizing, normalize_query
from backend.procedure_search import (identify, identify_needs, names_procedure, names_something, read_abbreviations,
                                      unnamed_document)
from backend.rag import (
    COMPARISON,
    EmbeddingError,
    GuidanceError,
    answer_from_naming_pages,
    answer_question,
    build_chunks,
    compare,
    relate,
)
from backend.scraper import ScraperError, SourceUnavailableError, scrape_url
from backend.schemas import (
    AdminProcedure,
    AdminSession,
    ApprovalRequest,
    ExtractionResponse,
    ExtractRequest,
    GuidanceRequest,
    GuidanceResponse,
    IdentifyRequest,
    IdentifyResponse,
    Language,
    LoginRequest,
    Need,
    PendingNeed,
    ProcedureDetail,
    ProcedureSummary,
    RelationRequest,
    RelationResponse,
    SavedProcedureResponse,
    TranscriptionResponse,
)
from backend.speech import (
    MAX_AUDIO_BYTES,
    TIMEOUT_SECONDS,
    AudioError,
    SpeechBusyError,
    SpeechUnavailableError,
    TranscriptionError,
    transcribe,
)


router = APIRouter()
# Every route on admin_router requires a valid admin session.
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    """Check the database (with the pgvector table) and the Ollama models."""
    checks = {"database": "ok", "ollama": "ok"}
    try:
        db.execute(text("SELECT 1 FROM procedure_chunks LIMIT 1"))
    except SQLAlchemyError:
        checks["database"] = "unavailable"
    try:
        tags = httpx.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=3)
        tags.raise_for_status()
        installed = {model["name"] for model in tags.json()["models"]}
        if not {LLM_MODEL, EMBEDDING_MODEL} <= installed:
            checks["ollama"] = "models missing"
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        checks["ollama"] = "unavailable"
    ready = all(value == "ok" for value in checks.values())
    response.status_code = 200 if ready else 503
    return {"status": "ok" if ready else "unavailable", **checks}


@router.post("/api/admin/login", response_model=AdminSession)
def login(request: LoginRequest, response: Response, http: Request) -> AdminSession:
    client = http.client.host if http.client else "unknown"
    if login_blocked(client):
        raise HTTPException(status_code=429, detail="Too many failed sign-ins. Try again in 15 minutes.")
    ok = check_admin_credentials(request.username, request.password)
    record_login(client, ok)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(request.username),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="strict",
        secure=COOKIE_SECURE,
    )
    return AdminSession(username=request.username)


@router.post("/api/admin/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, samesite="strict", secure=COOKIE_SECURE
    )


@router.get("/api/admin/session", response_model=AdminSession)
def session(username: str = Depends(require_admin)) -> AdminSession:
    return AdminSession(username=username)


@admin_router.post("/api/admin/extract", response_model=ExtractionResponse)
def create_extraction(request: ExtractRequest) -> ExtractionResponse:
    try:
        source = scrape_url(request.source_url)
        procedure = extract_procedure(source.source_text, source.source_url)
    except SourceUnavailableError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ScraperError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return ExtractionResponse(
        source_text=source.source_text,
        procedure=procedure,
        provenance_token=issue_provenance_token(
            source.source_url, source.source_text
        ),
    )


def _verify_provenance(token: str, source_url: str, source_text: str) -> None:
    try:
        verify_provenance_token(token, source_url, source_text)
    except ProvenanceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@admin_router.post("/api/admin/procedures", response_model=SavedProcedureResponse)
def save_procedure(
    request: ApprovalRequest, db: Session = Depends(get_db)
) -> SavedProcedureResponse:
    procedure = request.procedure
    _verify_provenance(
        request.provenance_token, procedure.source_url, request.source_text
    )
    try:
        chunks = build_chunks(request.source_text)
    except EmbeddingError as error:
        raise HTTPException(
            status_code=502,
            detail="Could not index the procedure. Nothing was saved.",
        ) from error
    record = Procedure(
        name=procedure.name,
        department=procedure.department,
        jurisdiction=procedure.jurisdiction,
        summary=procedure.summary,
        source_url=procedure.source_url,
        source_text=request.source_text,
        structured_data={
            "eligibility": procedure.eligibility,
            "steps": procedure.steps,
        },
    )
    db.add(record)

    try:
        db.flush()
        for chunk in chunks:
            chunk.procedure_id = record.id
        db.add_all(chunks)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "pgcode", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="A procedure using this source URL already exists.",
            ) from error
        raise HTTPException(
            status_code=500, detail="Unable to save the procedure."
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Unable to save the procedure."
        ) from error

    return SavedProcedureResponse(id=record.id, name=record.name, status="saved")


@admin_router.get("/api/admin/procedures", response_model=list[AdminProcedure])
def list_saved_procedures(db: Session = Depends(get_db)) -> list[AdminProcedure]:
    return [
        AdminProcedure(
            id=p.id,
            name=p.name,
            department=p.department,
            jurisdiction=p.jurisdiction,
            source_url=p.source_url,
        )
        for p in db.query(Procedure).order_by(Procedure.id.desc())
    ]


@admin_router.delete("/api/admin/procedures/{procedure_id}", status_code=204)
def delete_procedure(procedure_id: int, db: Session = Depends(get_db)) -> None:
    procedure = db.get(Procedure, procedure_id)
    if procedure is None:
        raise HTTPException(status_code=404, detail="Procedure not found.")
    db.delete(procedure)
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Unable to delete the procedure."
        ) from error


def _summary(procedure: Procedure) -> dict:
    return {
        "id": procedure.id,
        "name": procedure.name,
        "department": procedure.department,
        "jurisdiction": procedure.jurisdiction,
        "summary": procedure.summary,
    }


@router.get("/api/procedures", response_model=list[ProcedureSummary])
def list_procedures(db: Session = Depends(get_read_only_db)) -> list[ProcedureSummary]:
    return [
        ProcedureSummary(**_summary(p))
        for p in db.query(Procedure).order_by(Procedure.name)
    ]


@router.get("/api/procedures/{procedure_id}", response_model=ProcedureDetail)
def get_procedure(
    procedure_id: int, db: Session = Depends(get_read_only_db)
) -> ProcedureDetail:
    procedure = db.get(Procedure, procedure_id)
    if procedure is None:
        raise HTTPException(status_code=404, detail="Procedure not found.")
    return ProcedureDetail(
        **_summary(procedure),
        eligibility=procedure.structured_data.get("eligibility"),
        steps=procedure.structured_data.get("steps", []),
        source_url=procedure.source_url,
    )


CLARIFY = "Which service or document is your question about? For example: passport renewal or Aadhaar address update."
WHICH_DOCUMENT = "Which {noun} is your question about? Please say its name or what it is for."
WAV_TYPES = {"audio/wav", "audio/x-wav", "audio/wave"}


def _normalized(question: str, language: str) -> dict | None:
    """The English query for a Tamil or Tamil-English question; None for English
    questions, or when normalization fails (the original question is then searched)."""
    return normalize_query(question) if needs_normalizing(question, language) else None


@router.post("/api/speech/transcribe", response_model=TranscriptionResponse)
async def transcribe_speech(request: Request, language: Language = "ta") -> TranscriptionResponse:
    """Transcribe a short recording on this machine. The audio and transcript are not
    stored or logged; the citizen edits the transcript before sending it."""
    if request.headers.get("content-type", "").split(";")[0].strip().lower() not in WAV_TYPES:
        raise HTTPException(status_code=415, detail="Send the recording as WAV audio.")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="The recording is too long. Keep it under 30 seconds.")
    try:
        # On timeout the citizen gets an answer; the running transcription still finishes
        # (and deletes its file) in its thread, and later requests report "busy" meanwhile.
        text = await asyncio.wait_for(run_in_threadpool(transcribe, bytes(data), language), TIMEOUT_SECONDS)
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail="Transcription took too long. Try again or type your question.") from error
    except AudioError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SpeechUnavailableError as error:
        raise HTTPException(status_code=503, detail="Voice input is not set up on this server. Type your question instead.") from error
    except SpeechBusyError as error:
        raise HTTPException(status_code=503, detail="Voice input is busy. Try again in a moment.") from error
    except TranscriptionError as error:
        raise HTTPException(status_code=502, detail="The recording could not be transcribed. Try again or type your question.") from error
    return TranscriptionResponse(text=text, language=language)


@router.post("/api/identify", response_model=IdentifyResponse, response_model_exclude_unset=True)
def identify_procedure(
    request: IdentifyRequest, db: Session = Depends(get_read_only_db)
) -> IdentifyResponse:
    question, extra = request.question, {}
    if normalized := _normalized(question, request.language):
        if normalized["needs_clarification"]:
            return IdentifyResponse(status="no_match", candidates=[], clarification=CLARIFY)
        question = normalized["normalized_query"]
        extra = {"normalized_query": question}
    if not names_something(question):
        return IdentifyResponse(status="no_match", candidates=[], clarification=CLARIFY)
    question = read_abbreviations(question, [name for (name,) in db.query(Procedure.name)])  # "idp" is "IDP"
    try:
        multiple = identify_needs(db, question)
        if not isinstance(multiple, tuple):
            status, procedures = identify(db, question, need=multiple)
    except EmbeddingError as error:
        raise HTTPException(
            status_code=502, detail="The search service is unavailable. Try again."
        ) from error
    if not isinstance(multiple, tuple):
        # A document asked about without saying which ("a certificate in Tamil Nadu") is not matched to one
        # page: the citizen is asked which, unless the search found several that fit to choose from.
        if status != "ambiguous" and (noun := unnamed_document(question)):
            return IdentifyResponse(status="no_match", candidates=[], clarification=WHICH_DOCUMENT.format(noun=noun), **extra)
        return IdentifyResponse(
            status=status,
            candidates=[ProcedureSummary(**_summary(p)) for p in procedures],
            **({"named": True} if status == "matched" and names_procedure(question, procedures[0]) else {}),
            **extra,
        )
    needs, pending, relation = multiple
    return IdentifyResponse(
        status="multiple",
        candidates=[],
        needs=[
            Need(**{**n, "candidates": [ProcedureSummary(**_summary(p)) for p in n["candidates"]]})
            for n in needs
        ],
        pending=[PendingNeed(**n) for n in pending],
        relation_question=relation,
        **extra,
    )


@router.post("/api/guidance", response_model=GuidanceResponse, response_model_exclude_unset=True)
def guidance(
    request: GuidanceRequest, db: Session = Depends(get_read_only_db)
) -> GuidanceResponse:
    procedure = db.get(Procedure, request.procedure_id)
    if procedure is None:
        raise HTTPException(status_code=404, detail="Procedure not found.")
    # The procedure is already chosen, so a vague question is answered, not clarified.
    question, extra = request.question, {}
    if normalized := _normalized(question, request.language):
        question = normalized["normalized_query"]
        extra = {"normalized_query": question}
    try:
        claims, omitted, complete = answer_question(db, procedure.id, question)
        # A page saying only "Fees as prescribed" may be completed by a page naming this
        # procedure (a fee table). Those claims carry that page's id and link.
        if not complete and (related := answer_from_naming_pages(db, procedure, question)):
            page, more, more_omitted, complete = related
            claims += [{**claim, "procedure_id": page.id, "source_url": page.source_url} for claim in more]
            omitted += more_omitted
    except (EmbeddingError, GuidanceError) as error:
        raise HTTPException(
            status_code=502, detail="The answer service is unavailable. Try again."
        ) from error
    return GuidanceResponse(
        procedure_id=procedure.id,
        source_url=procedure.source_url,
        insufficient_evidence=not claims,
        claims=claims,
        omitted_claims=omitted,
        **extra,
        **({"partial": True} if claims and not complete else {}),
    )


@router.post("/api/relation", response_model=RelationResponse, response_model_exclude_defaults=True)
def relation(
    request: RelationRequest, db: Session = Depends(get_read_only_db)
) -> RelationResponse:
    procedures = db.query(Procedure).filter(Procedure.id.in_(request.procedure_ids)).all()
    if len(procedures) != len(set(request.procedure_ids)):
        raise HTTPException(status_code=404, detail="Procedure not found.")
    comparison = bool(COMPARISON.search(request.question))
    try:
        claims, omitted = (compare if comparison else relate)(db, [p.id for p in procedures], request.question)
    except (EmbeddingError, GuidanceError) as error:
        raise HTTPException(
            status_code=502, detail="The answer service is unavailable. Try again."
        ) from error
    urls = {p.id: p.source_url for p in procedures}
    return RelationResponse(
        insufficient_evidence=not claims,
        claims=[{**c, "source_url": urls[c["procedure_id"]]} for c in claims],
        omitted_claims=omitted,
        comparison=comparison,
    )


router.include_router(admin_router)
