from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.scraper import scrape_url, ScraperError


app = FastAPI(
    title="ProcedureAssist AI",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    url: str


@app.get("/")
def root():
    return {
        "message": "ProcedureAssist AI backend is running"
    }


@app.post("/api/admin/scrape")
def scrape_source(request: ScrapeRequest):
    try:
        result = scrape_url(request.url)

        return {
            "source_url": result["source_url"],
            "source_text": result["source_text"],
        }

    except ScraperError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc