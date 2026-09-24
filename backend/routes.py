
from fastapi import APIRouter
from pydantic import BaseModel

from extractor import extract_procedure, ProcedureSpine
from scraper import scrape

router = APIRouter(prefix="/api/admin")


class ExtractRequest(BaseModel):
    source_url: str


class ReExtractRequest(BaseModel):
    source_url: str
    source_text: str


class ApproveRequest(BaseModel):
    procedure: ProcedureSpine
    source_text: str


@router.post("/extract")
def extract(req: ExtractRequest):
    text = scrape(req.source_url)
    procedure = extract_procedure(text, req.source_url)

    return {
        "procedure": procedure.model_dump(),
        "source_text": text
    }


@router.post("/re-extract")
def re_extract(req: ReExtractRequest):
    procedure = extract_procedure(
        req.source_text,
        req.source_url
    )

    return {
        "procedure": procedure.model_dump()
    }


@router.post("/procedures")
def approve(req: ApproveRequest):
    return {
        "message": "Procedure approved",
        "procedure": req.procedure.model_dump()
    }

