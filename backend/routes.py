
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator

from extractor import extract_procedure, ProcedureSpine
from scraper import scrape

router = APIRouter(prefix="/api/admin")


class ExtractRequest(BaseModel):
    source_url: HttpUrl


class ReExtractRequest(BaseModel):
    source_url: HttpUrl
    source_text: str

    @field_validator("source_text")
    @classmethod
    def validate_source_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source text cannot be empty.")
        return value


class ApproveRequest(BaseModel):
    procedure: ProcedureSpine
    source_text: str

    @field_validator("source_text")
    @classmethod
    def validate_source_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source text cannot be empty.")
        return value


@router.post("/extract")
def extract(req: ExtractRequest):
    try:
        text = scrape(str(req.source_url))

        if not text or not text.strip():
            raise HTTPException(
                status_code=422,
                detail="No source text could be extracted from the URL."
            )

        procedure = extract_procedure(text, str(req.source_url))

        return {
            "procedure": procedure.model_dump(),
            "source_text": text
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to extract the procedure from the source."
        )


@router.post("/re-extract")
def re_extract(req: ReExtractRequest):
    try:
        procedure = extract_procedure(
            req.source_text,
            str(req.source_url)
        )

        return {
            "procedure": procedure.model_dump()
        }
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to re-extract the procedure."
        )


@router.post("/procedures")
def approve(req: ApproveRequest):
    return {
        "message": "Procedure approved",
        "procedure": req.procedure.model_dump()
    }

