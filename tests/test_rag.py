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
    _is_heading,
    chunk_text,
    embed_texts,
    retrieve,
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

    def test_starts_the_next_chunk_at_the_heading_of_a_list_it_would_split(self):
        steps = [f"Step {n}: the polling official does task number {n} for you." * 2 for n in range(1, 8)]
        text = "Intro " + "y" * 700 + "\n\nHow do I vote in person?\n\n" + "\n\n".join(steps)
        chunks = chunk_text(text)

        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[1].startswith("How do I vote in person?\n\nStep 1:"))
        self.assertTrue(all(step in chunks[1] for step in steps))

    def test_only_questions_and_lead_ins_are_headings(self):
        for heading in ["How do I vote in person?", "Who It Covers?", "Prerequisites:",
                        "7. What are the documents required for applying Community Certificate?"]:
            self.assertTrue(_is_heading(heading), heading)
        for item in ["Photo", "Address Proof", "Valid mobile number", "Requirements",
                     "8 Renewal of driving licence Rs. 200.00/-", "Age group: 18-54 years."]:
            self.assertFalse(_is_heading(item), item)

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

    @patch("backend.rag.httpx.post")
    def test_retries_a_transient_failure_once_but_never_a_timeout(self, post):
        for first in (self.response([], status=400), self.response([], status=503), httpx.ConnectError("reset")):
            with self.subTest(first=getattr(first, "status_code", type(first).__name__)):
                post.reset_mock()
                post.side_effect = [first, self.response([unit_vector()])]
                self.assertEqual(len(embed_texts(["one text"])), 1)
                self.assertEqual(post.call_count, 2)
        post.reset_mock()
        post.side_effect = [httpx.ReadTimeout("slow"), self.response([unit_vector()])]
        with self.assertRaises(EmbeddingError):
            embed_texts(["one text"])
        self.assertEqual(post.call_count, 1)


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


RC = "4. Issue or renewal of certificate of registration and assignment of new registration mark"


class RetrieveTest(DatabaseTestCase):
    def page(self, name, contents):
        procedure = Procedure(name=name, summary="s", source_url=f"https://example.gov.in/{name}", source_text="\n\n".join(contents),
                              structured_data={"eligibility": None, "steps": ["One"]})
        self.session.add(procedure)
        self.session.flush()
        chunks = [ProcedureChunk(procedure_id=procedure.id, chunk_index=i, content=c, embedding=unit_vector(i)) for i, c in enumerate(contents)]
        self.session.add_all(chunks)
        self.session.flush()
        return procedure, [c.id for c in chunks]

    def retrieved(self, procedure, closest, limit=1, question="What is the fee to renew the registration certificate?"):
        self.embed.side_effect = lambda texts, query=False: [unit_vector(closest)]
        return [c.id for c in retrieve(self.session, procedure.id, question, limit)]

    def test_a_table_item_running_over_chunks_comes_with_the_chunk_it_starts_in(self):
        fees, ids = self.page("Fee table", [
            f"3. Recording of change of address Rupees Two Hundred Only\n\n{RC}:",
            f"{RC}: (a) Invalid Carriage Rupees Fifty Only\n\n{RC}: (b) Motor cycle Rupees Three Hundred Only",
            f"{RC}: (c) Light Motor Vehicles Rupees Six Hundred Only\n\n5. Issue of duplicate certificate of registration Half of the fee",
            "9. Endorsing hire purchase/lease/hypothecation agreement: (c) Medium or heavy vehicle Rupees Three Thousand Only",
            "10. Conducting test of a vehicle for grant or renewal of certificate of fitness: (a) Motorcycle Rupees Two Hundred Only",
        ])
        # Another page whose chunk starts with the same item is never added.
        self.page("Other", ["Intro", f"{RC}: (b) Motor cycle Rupees Nine Hundred Only"])
        self.assertEqual(self.retrieved(fees, 0), [ids[0], ids[1], ids[2]])  # the retrieved chunk first, then item 4's rows
        # Item 9 never brings item 10, and a chunk that ends with an item's last row brings nothing.
        self.assertEqual(self.retrieved(fees, 3), [ids[3]])
        self.assertEqual(self.retrieved(fees, 2), [ids[2]])

    def test_an_item_continues_only_under_exactly_the_same_label(self):
        page, ids = self.page("Permits", ["1. Issue of a permit for goods carriage:",
                                          "1. Issue of a permit for goods carriage vehicles: (a) Rupees One Thousand Only"])
        self.assertEqual(self.retrieved(page, 0, question="What is the fee for a goods carriage permit?"), [ids[0]])

    def test_an_item_the_question_is_not_about_does_not_come_along(self):
        fitness = "10. Conducting test of a vehicle for grant or renewal of certificate of fitness"
        fees, ids = self.page("Fees", [
            f"9. Endorsing hire purchase/lease/hypothecation agreement: (b) Light motor vehicle Rupees One Thousand Only\n\n{fitness}:",
            f"{fitness}: (a) Motorcycle (i) Manual: Rupees Two Hundred Only",
        ])
        # A hypothecation question retrieves the chunk that happens to end with item 10, but not item 10's rows.
        self.assertEqual(self.retrieved(fees, 0, question="What is the hypothecation endorsement fee for a car?"), [ids[0]])
        self.assertEqual(self.retrieved(fees, 0, question="What is the fitness test fee for a motorcycle?"), [ids[0], ids[1]])
        # "RC" is spelled out: an RC question uses the registration item's words.
        rc, rc_ids = self.page("RC fees", [f"{RC}:", f"{RC}: (b) Motor cycle Rupees Three Hundred Only"])
        self.assertEqual(self.retrieved(rc, 0, question="What is the fee to renew the RC of a motorcycle?"), rc_ids)

    def test_pages_without_numbered_table_items_are_retrieved_as_before(self):
        page, ids = self.page("Plain", ["How to apply:", "Step 1: Log in.", "Step 2: Fill the form."])
        self.assertEqual(self.retrieved(page, 0, limit=2), [ids[0], ids[1]])
