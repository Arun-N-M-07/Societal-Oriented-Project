from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


def _required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be empty")
    return value


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _http_url(value: str) -> str:
    value = _required_text(value)
    parsed = urlparse(value)
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or any(character.isspace() for character in value)
    ):
        raise ValueError("must be a valid HTTP or HTTPS URL")
    return value


class ScrapeResult(BaseModel):
    source_url: str
    source_text: str

    _validate_source_url = field_validator("source_url")(_http_url)
    _validate_source_text = field_validator("source_text")(_required_text)


class ProcedureExtraction(BaseModel):
    name: str
    department: str | None = None
    jurisdiction: str | None = None
    summary: str
    eligibility: str | None = None
    steps: list[str]

    _validate_required_text = field_validator("name", "summary")(_required_text)
    _validate_optional_text = field_validator(
        "department", "jurisdiction", "eligibility"
    )(_optional_text)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, steps: list[str]) -> list[str]:
        cleaned_steps = [step.strip() for step in steps if step.strip()]
        if not cleaned_steps:
            raise ValueError("must contain at least one non-empty step")
        return cleaned_steps


class ProcedureSpine(ProcedureExtraction):
    source_url: str

    _validate_source_url = field_validator("source_url")(_http_url)


class ApprovalRequest(BaseModel):
    procedure: ProcedureSpine
    source_text: str

    _validate_source_text = field_validator("source_text")(_required_text)


class SavedProcedureResponse(BaseModel):
    id: int
    name: str
    status: str

    _validate_text = field_validator("name", "status")(_required_text)
