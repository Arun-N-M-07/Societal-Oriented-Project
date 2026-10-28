import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from backend import models
from backend.config import FRONTEND_ORIGIN
from backend.database import Base, engine
from backend.routes import router


Base.metadata.create_all(bind=engine)

# One log line per request (its id, also returned as X-Request-ID, method, path, status, duration) and one per
# model call (extractor.ollama_post), tagged with the same id. Question text, source text and credentials are
# never logged.
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID.get()
        return True


handler = logging.StreamHandler()
handler.addFilter(RequestIdFilter())
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s request=%(request_id)s %(message)s"))
log = logging.getLogger("procedureassist")
log.addHandler(handler)
log.setLevel(logging.INFO)


app = FastAPI(title="ProcedureAssist")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    REQUEST_ID.set(uuid.uuid4().hex[:12])
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("%s %s failed after %.0fms", request.method, request.url.path, (time.perf_counter() - start) * 1000)
        raise
    log.info("%s %s %s %.0fms", request.method, request.url.path, response.status_code, (time.perf_counter() - start) * 1000)
    response.headers["X-Request-ID"] = REQUEST_ID.get()
    return response


@app.exception_handler(OperationalError)
async def database_unavailable(request: Request, error: OperationalError) -> JSONResponse:
    """The database cannot be reached: a message and the request id, as for the model, instead of a bare 500."""
    log.error("database unavailable: %s", type(error.orig).__name__)
    return JSONResponse(status_code=503, content={"detail": "The procedure database is unavailable. Try again."})


app.include_router(router)
