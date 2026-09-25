from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.extractor import ExtractionError, extract_procedure
from backend.models import Procedure
from backend.scraper import ScraperError, scrape_url
from backend.schemas import (
    ApprovalRequest,
    ExtractionResponse,
    ExtractRequest,
    ProcedureSpine,
    SavedProcedureResponse,
    ScrapeResult,
)


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/admin/extract", response_model=ExtractionResponse)
def create_extraction(request: ExtractRequest) -> ExtractionResponse:
    try:
        source = scrape_url(request.source_url)
        procedure = extract_procedure(source.source_text, source.source_url)
    except ScraperError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return ExtractionResponse(
        source_text=source.source_text,
        procedure=procedure,
    )


@router.post("/api/admin/re-extract", response_model=ProcedureSpine)
def re_extract_procedure(request: ScrapeResult) -> ProcedureSpine:
    try:
        return extract_procedure(request.source_text, request.source_url)
    except ExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/api/admin/procedures", response_model=SavedProcedureResponse)
def save_procedure(
    request: ApprovalRequest, db: Session = Depends(get_db)
) -> SavedProcedureResponse:
    procedure = request.procedure
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
