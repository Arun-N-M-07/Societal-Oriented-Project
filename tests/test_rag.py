import db_support  # noqa: F401  (must be first)

import json
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy.exc import IntegrityError

from backend.auth import issue_provenance_token
from backend.models import Procedure, ProcedureChunk
from backend.rag import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    QUERY_INSTRUCTION,
    EmbeddingError,
    backfill,
    chunk_text,
    embed_texts,
)
from db_support import DatabaseTestCase, unit_vector


APPROVAL = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "sample_procedure.json").read_text()
)
APPROVAL["source_text"] = "\n\n".join(f"Paragraph {i}." + " word" * 150 for i in range(5))
APPROVAL["provenance_token"] = issue_provenance_token(
    APPROVAL["procedure"]["source_url"], APPROVAL["source_text"]
)


class ChunkTextTest(unittest.TestCase):
    def test_keeps_short_text_as_one_chunk(self):
        self.assertEqual(chunk_text("Heading\n\nOne paragraph."), ["Heading\n\nOne paragraph."])
        self.assertEqual(chunk_text("  \n\n "), [])

    def test_splits_on_paragraphs_in_order_within_the_size_limit(self):
        paragraphs = [f"Step {i}: " + "detail " * 60 for i in range(8)]
        chunks = chunk_text("\n\n".join(paragraphs))

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= CHUNK_SIZE + CHUNK_OVERLAP for chunk in chunks))
        joined = "\n\n".join(chunks)
        positions = [joined.index(paragraph.strip()) for paragraph in paragraphs]
        self.assertEqual(positions, sorted(positions))
        for paragraph in paragraphs:
            self.assertTrue(any(paragraph.strip() in chunk for chunk in chunks))

    def test_splits_long_paragraphs_at_spaces(self):
        chunks = chunk_text("word " * 600)

        self.assertTrue(all(len(chunk) <= CHUNK_SIZE for chunk in chunks))
        self.assertTrue(all(not chunk.endswith("wor") for chunk in chunks))
        self.assertEqual(" ".join(chunks).split(), ["word"] * 600)

    def test_carries_a_short_heading_into_the_next_chunk(self):
        text = "A " + "x" * 900 + "\n\nRequired documents\n\n" + "Proof of address. " * 10
        chunks = chunk_text(text)

        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[1].startswith("Required documents"))

    def test_is_deterministic(self):
        text = "\n\n".join("Paragraph " + "z " * i for i in range(200))
        self.assertEqual(chunk_text(text), chunk_text(text))


class EmbedTextsTest(unittest.TestCase):
    def response(self, embeddings, status=200):
        return httpx.Response(
            status,
            json={"embeddings": embeddings},
            request=httpx.Request("POST", "http://ollama.test/api/embed"),
        )

    @patch("backend.rag.httpx.post")
    def test_embeds_documents_plainly_and_queries_with_an_instruction(self, post):
        post.return_value = self.response([unit_vector(), unit_vector(1)])

        self.assertEqual(len(embed_texts(["a", "b"])), 2)
        self.assertEqual(post.call_args.kwargs["json"]["input"], ["a", "b"])
        self.assertEqual(post.call_args.kwargs["json"]["model"], "qwen3-embedding:0.6b")

        post.return_value = self.response([unit_vector()])
        embed_texts(["passport"], query=True)
        self.assertEqual(post.call_args.kwargs["json"]["input"], [QUERY_INSTRUCTION + "passport"])

    @patch("backend.rag.httpx.post")
    def test_rejects_failures_and_unexpected_vectors(self, post):
        for outcome in (
            httpx.ConnectError("down"),
            httpx.ReadTimeout("slow"),
            self.response([], status=500),
            self.response([[0.1, 0.2]]),
            self.response([unit_vector(), unit_vector()]),
        ):
            with self.subTest(outcome=type(outcome).__name__):
                post.side_effect = outcome if isinstance(outcome, Exception) else None
                post.return_value = None if isinstance(outcome, Exception) else outcome
                with self.assertRaises(EmbeddingError):
                    embed_texts(["one text"])


class IndexingTest(DatabaseTestCase):
    def chunks(self):
        return self.session.query(ProcedureChunk).order_by(ProcedureChunk.chunk_index).all()

    def test_save_stores_ordered_chunks_with_vectors(self):
        response = self.client.post("/api/admin/procedures", json=APPROVAL)

        self.assertEqual(response.status_code, 200)
        chunks = self.chunks()
        self.assertEqual([chunk.content for chunk in chunks], chunk_text(APPROVAL["source_text"]))
        self.assertTrue(all(chunk.procedure_id == response.json()["id"] for chunk in chunks))
        self.assertEqual(len(chunks[0].embedding), 1024)

    def test_embedding_failure_saves_nothing(self):
        self.embed.side_effect = EmbeddingError("The embedding service is unavailable.")

        response = self.client.post("/api/admin/procedures", json=APPROVAL)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json(), {"detail": "Could not index the procedure. Nothing was saved."}
        )
        self.assertEqual(self.session.query(Procedure).count(), 0)
        self.assertEqual(self.session.query(ProcedureChunk).count(), 0)

    def test_duplicate_save_does_not_duplicate_chunks(self):
        self.client.post("/api/admin/procedures", json=APPROVAL)
        count = len(self.chunks())
        response = self.client.post("/api/admin/procedures", json=APPROVAL)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.chunks()), count)

    def test_chunk_positions_are_unique(self):
        procedure_id = self.client.post("/api/admin/procedures", json=APPROVAL).json()["id"]
        self.session.add(
            ProcedureChunk(procedure_id=procedure_id, chunk_index=0, content="x", embedding=unit_vector())
        )
        with self.assertRaises(IntegrityError):
            self.session.flush()

    def test_deleting_a_procedure_deletes_its_chunks(self):
        procedure_id = self.client.post("/api/admin/procedures", json=APPROVAL).json()["id"]

        self.client.delete(f"/api/admin/procedures/{procedure_id}")

        self.assertEqual(self.session.query(ProcedureChunk).count(), 0)

    def test_backfill_indexes_missing_procedures_once(self):
        self.session.add(
            Procedure(
                name="Old",
                summary="Saved before indexing.",
                source_url="https://example.gov.in/old",
                source_text="Old official text.\n\nSecond paragraph.",
                structured_data={"eligibility": None, "steps": ["One"]},
            )
        )
        self.session.flush()

        self.assertEqual(backfill(self.session), 1)
        self.assertEqual(backfill(self.session), 0)
        self.assertEqual(len(self.chunks()), 1)


if __name__ == "__main__":
    unittest.main()
