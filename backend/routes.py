from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Procedure
from backend.schemas import ApprovalRequest, SavedProcedureResponse


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
