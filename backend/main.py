from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import models
from backend.config import FRONTEND_ORIGIN
from backend.database import Base, engine
from backend.routes import router


Base.metadata.create_all(bind=engine)


app = FastAPI(title="ProcedureAssist")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(router)
