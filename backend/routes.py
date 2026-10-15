from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    ProvenanceError,
    check_admin_credentials,
    create_session_token,
    issue_provenance_token,
    require_admin,
    verify_provenance_token,
)
from backend.config import COOKIE_SECURE
from backend.database import get_db, get_read_only_db
from backend.extractor import ExtractionError, extract_procedure
from backend.models import Procedure
from backend.scraper import ScraperError, SourceUnavailableError, scrape_url
from backend.schemas import (
    AdminProcedure,
    AdminSession,
    ApprovalRequest,
    LoginRequest,
    ProcedureDetail,
    ProcedureSummary,
    ExtractionResponse,
    ExtractRequest,
    ProcedureSpine,
    ReExtractRequest,
    SavedProcedureResponse,
)


router = APIRouter()
# Every route on admin_router requires a valid admin session.
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/admin/login", response_model=AdminSession)
def login(request: LoginRequest, response: Response) -> AdminSession:
    if not check_admin_credentials(request.username, request.password):
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


@admin_router.post("/api/admin/re-extract", response_model=ProcedureSpine)
def re_extract_procedure(request: ReExtractRequest) -> ProcedureSpine:
    _verify_provenance(
        request.provenance_token, request.source_url, request.source_text
    )
    try:
        return extract_procedure(request.source_text, request.source_url)
    except ExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@admin_router.post("/api/admin/procedures", response_model=SavedProcedureResponse)
def save_procedure(
    request: ApprovalRequest, db: Session = Depends(get_db)
) -> SavedProcedureResponse:
    procedure = request.procedure
    _verify_provenance(
        request.provenance_token, procedure.source_url, request.source_text
    )
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
        db.commit()
        db.refresh(record)
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


router.include_router(admin_router)
