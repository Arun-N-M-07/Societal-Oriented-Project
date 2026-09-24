import json
import os
import httpx
from pydantic import BaseModel, Field


class ProcedureExtraction(BaseModel):
    name: str
    department: str | None = None
    jurisdiction: str | None = None
    summary: str
    eligibility: str | None = None
    steps: list[str] = Field(min_length=1)


class ProcedureSpine(ProcedureExtraction):
    source_url: str


def build_prompt(text: str) -> str:
    return f"""
Extract the government procedure from the text below.

Use ONLY the supplied text.
Do not use outside knowledge.
Do not guess.
Return JSON only.

Required JSON format:
{{
  "name": "procedure name",
  "department": "department or null",
  "jurisdiction": "jurisdiction or null",
  "summary": "short summary",
  "eligibility": "eligibility or null",
  "steps": ["step 1", "step 2", "step 3"]
}}

The steps MUST be taken from the supplied text.
If numbered steps exist, preserve their order.

TEXT:
{text}
"""


def call_qwen(prompt: str) -> str:
    url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("LLM_MODEL", "qwen3:8b")

    response = httpx.post(
        f"{url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False
        },
        timeout=300
    )

    response.raise_for_status()
    return response.json()["response"]


def extract_procedure(source_text: str, source_url: str) -> ProcedureSpine:
    source_text = source_text[:8000]

    data = json.loads(call_qwen(build_prompt(source_text)))

    # Make fields safe
    data["name"] = data.get("name") or "Government Procedure"
    data["summary"] = data.get("summary") or "Procedure details"
    data["department"] = data.get("department") or None
    data["jurisdiction"] = data.get("jurisdiction") or None
    data["eligibility"] = data.get("eligibility") or None

    # Qwen sometimes returns one string instead of a list
    if isinstance(data.get("steps"), str):
        data["steps"] = [data["steps"]]

    # If Qwen gives no steps, extract numbered steps from source text
    if not isinstance(data.get("steps"), list) or not data["steps"]:
        steps = []

        for line in source_text.splitlines():
            line = line.strip()

            if len(line) > 2 and line[0].isdigit():
                dot = line.find(".")
                if dot != -1:
                    step = line[dot + 1:].strip()
                    if step:
                        steps.append(step)

        data["steps"] = steps

    # Final safety fallback
    if not data["steps"]:
        data["steps"] = [
            "Review the procedure information provided in the source."
        ]

    result = ProcedureExtraction.model_validate(data)

    return ProcedureSpine(
        **result.model_dump(),
        source_url=source_url
    )