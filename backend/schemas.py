from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_URL_LENGTH = 2_048
MAX_SOURCE_TEXT_LENGTH = 100_000
MAX_STEPS = 100
MAX_STEP_LENGTH = 2_000


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
    if len(value) > MAX_URL_LENGTH:
        raise ValueError("must be at most 2048 characters")
    parsed = urlparse(value)
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or any(character.isspace() for character in value)
    ):
        raise ValueError("must be a valid HTTP or HTTPS URL")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScrapeResult(StrictModel):
    source_url: str
    source_text: str = Field(max_length=MAX_SOURCE_TEXT_LENGTH)

    _validate_source_url = field_validator("source_url")(_http_url)
    _validate_source_text = field_validator("source_text")(_required_text)


class ExtractRequest(StrictModel):
    source_url: str

    _validate_source_url = field_validator("source_url")(_http_url)


class ProcedureExtraction(StrictModel):
    name: str = Field(max_length=300)
    department: str | None = Field(default=None, max_length=300)
    jurisdiction: str | None = Field(default=None, max_length=300)
    summary: str = Field(max_length=5_000)
    eligibility: str | None = Field(default=None, max_length=10_000)
    steps: list[str] = Field(max_length=MAX_STEPS)

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
        if any(len(step) > MAX_STEP_LENGTH for step in cleaned_steps):
            raise ValueError("each step must be at most 2000 characters")
        return cleaned_steps


class ProcedureSpine(ProcedureExtraction):
    source_url: str

    _validate_source_url = field_validator("source_url")(_http_url)


class ReExtractRequest(ScrapeResult):
    provenance_token: str = Field(max_length=512)


class ExtractionResponse(StrictModel):
    source_text: str
    procedure: ProcedureSpine
    provenance_token: str

    _validate_source_text = field_validator("source_text")(_required_text)


class ApprovalRequest(StrictModel):
    procedure: ProcedureSpine
    source_text: str = Field(max_length=MAX_SOURCE_TEXT_LENGTH)
    provenance_token: str = Field(max_length=512)

    _validate_source_text = field_validator("source_text")(_required_text)


class ProcedureSummary(StrictModel):
    id: int
    name: str
    department: str | None
    jurisdiction: str | None
    summary: str


class ProcedureDetail(ProcedureSummary):
    eligibility: str | None
    steps: list[str]
    source_url: str


class AdminProcedure(StrictModel):
    id: int
    name: str
    department: str | None
    jurisdiction: str | None
    source_url: str


class LoginRequest(StrictModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=200)


class AdminSession(StrictModel):
    username: str


class SavedProcedureResponse(StrictModel):
    id: int
    name: str
    status: str

    _validate_text = field_validator("name", "status")(_required_text)
