import sys

import httpx
from sqlalchemy.orm import Session

from backend.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, OLLAMA_BASE_URL
from backend.models import Procedure, ProcedureChunk


CHUNK_SIZE = 1_000
CHUNK_OVERLAP = 200
EMBEDDING_TIMEOUT_SECONDS = 60.0
# Qwen3-Embedding expects an instruction on queries and plain text for documents.
QUERY_INSTRUCTION = (
    "Instruct: Given a citizen's question or situation, retrieve official "
    "government procedure text that answers it\nQuery: "
)


class EmbeddingError(Exception):
    pass


def chunk_text(text: str) -> list[str]:
    """Split source text into ordered chunks on paragraph boundaries.

    Paragraphs longer than CHUNK_SIZE are split at a space. A short final
    paragraph (often a heading) is repeated at the start of the next chunk.
    """
    blocks = []
    for block in text.split("\n\n"):
        block = block.strip()
        while len(block) > CHUNK_SIZE:
            cut = block.rfind(" ", 0, CHUNK_SIZE)
            cut = cut if cut > 0 else CHUNK_SIZE
            blocks.append(block[:cut].strip())
            block = block[cut:].strip()
        if block:
            blocks.append(block)

    chunks, current = [], []
    for block in blocks:
        if current and len("\n\n".join([*current, block])) > CHUNK_SIZE:
            chunks.append("\n\n".join(current))
            current = current[-1:] if len(current[-1]) <= CHUNK_OVERLAP else []
        current.append(block)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def embed_texts(texts: list[str], *, query: bool = False) -> list[list[float]]:
    inputs = [QUERY_INSTRUCTION + text for text in texts] if query else texts
    try:
        response = httpx.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": inputs},
            timeout=EMBEDDING_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        vectors = response.json()["embeddings"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        raise EmbeddingError("The embedding service is unavailable.") from error

    if len(vectors) != len(texts) or any(
        len(vector) != EMBEDDING_DIMENSIONS for vector in vectors
    ):
        raise EmbeddingError("The embedding service returned unexpected vectors.")
    return vectors


def build_chunks(source_text: str) -> list[ProcedureChunk]:
    """Chunk and embed source text. Call outside any database transaction."""
    contents = chunk_text(source_text)
    vectors = embed_texts(contents)
    return [
        ProcedureChunk(chunk_index=index, content=content, embedding=vector)
        for index, (content, vector) in enumerate(zip(contents, vectors))
    ]


def backfill(db: Session) -> int:
    """Index every procedure that has no chunks yet. Safe to run repeatedly."""
    indexed = 0
    missing = db.query(Procedure).filter(~Procedure.id.in_(
        db.query(ProcedureChunk.procedure_id)
    ))
    for procedure in missing.all():
        for chunk in build_chunks(procedure.source_text):
            chunk.procedure_id = procedure.id
            db.add(chunk)
        db.commit()
        indexed += 1
    return indexed


if __name__ == "__main__" and sys.argv[1:] == ["backfill"]:
    from backend.database import SessionLocal

    with SessionLocal() as session:
        print(f"Indexed {backfill(session)} procedure(s).")
