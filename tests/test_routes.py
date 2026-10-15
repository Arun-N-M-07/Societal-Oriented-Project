import db_support  # noqa: F401  (must be first)

import unittest
from unittest.mock import patch

from backend.auth import issue_provenance_token
from backend.extractor import ExtractionError
from backend.schemas import ProcedureSpine, ScrapeResult
from backend.scraper import ScraperError, SourceUnavailableError
from db_support import make_client


REEXTRACT_BODY = {
    "source_url": "https://example.gov.in/passport",
    "source_text": "Corrected official instructions.",
    "provenance_token": issue_provenance_token(
        "https://example.gov.in/passport", "Corrected official instructions."
    ),
}


class ExtractionRouteTest(unittest.TestCase):
    def setUp(self):
        self.client = make_client()

    @patch("backend.routes.extract_procedure")
    @patch("backend.routes.scrape_url")
    def test_scrapes_then_returns_extracted_procedure(
        self, mock_scrape, mock_extract
    ):
        mock_scrape.return_value = ScrapeResult(
            source_url="https://example.gov.in/final-passport-page",
            source_text="Official passport instructions.",
        )
        mock_extract.return_value = ProcedureSpine(
            name="Fresh Passport Application",
            department="Ministry of External Affairs",
            jurisdiction="Central Government",
            summary="Apply for a fresh passport.",
            eligibility=None,
            steps=["Register online."],
            source_url="https://example.gov.in/final-passport-page",
        )

        response = self.client.post(
            "/api/admin/extract",
            json={"source_url": "https://example.gov.in/passport"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        token = body.pop("provenance_token")
        self.assertEqual(
            body,
            {
                "source_text": "Official passport instructions.",
                "procedure": mock_extract.return_value.model_dump(),
            },
        )
        self.assertTrue(token.startswith("provenance:"))
        mock_scrape.assert_called_once_with(
            "https://example.gov.in/passport"
        )
        mock_extract.assert_called_once_with(
            "Official passport instructions.",
            "https://example.gov.in/final-passport-page",
        )

    @patch("backend.routes.extract_procedure")
    @patch("backend.routes.scrape_url")
    def test_returns_clear_model_error(self, mock_scrape, mock_extract):
        mock_scrape.return_value = ScrapeResult(
            source_url="https://example.gov.in/passport",
            source_text="Official passport instructions.",
        )
        mock_extract.side_effect = ExtractionError("Qwen extraction timed out.")

        response = self.client.post(
            "/api/admin/extract",
            json={"source_url": "https://example.gov.in/passport"},
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "Qwen extraction timed out."})

    @patch("backend.routes.extract_procedure")
    @patch("backend.routes.scrape_url")
    def test_returns_clear_scraper_error(self, mock_scrape, mock_extract):
        mock_scrape.side_effect = ScraperError("Unable to retrieve the source page.")

        response = self.client.post(
            "/api/admin/extract",
            json={"source_url": "https://example.gov.in/passport"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {"detail": "Unable to retrieve the source page."},
        )
        mock_extract.assert_not_called()

    @patch("backend.routes.extract_procedure")
    @patch("backend.routes.scrape_url")
    def test_rejects_invalid_input_before_extraction(
        self, mock_scrape, mock_extract
    ):
        response = self.client.post(
            "/api/admin/extract",
            json={"source_url": "not-a-url"},
        )

        self.assertEqual(response.status_code, 422)
        mock_scrape.assert_not_called()
        mock_extract.assert_not_called()

    @patch("backend.routes.scrape_url")
    @patch("backend.routes.extract_procedure")
    def test_reextracts_without_scraping(
        self, mock_extract, mock_scrape
    ):
        mock_extract.return_value = ProcedureSpine(
            name="Edited Passport Application",
            department="Ministry of External Affairs",
            jurisdiction="Central Government",
            summary="Apply using the corrected instructions.",
            eligibility=None,
            steps=["Create an account."],
            source_url="https://example.gov.in/passport",
        )

        response = self.client.post(
            "/api/admin/re-extract",
            json=REEXTRACT_BODY,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), mock_extract.return_value.model_dump())
        mock_extract.assert_called_once_with(
            "Corrected official instructions.",
            "https://example.gov.in/passport",
        )
        mock_scrape.assert_not_called()

    @patch("backend.routes.scrape_url")
    @patch("backend.routes.extract_procedure")
    def test_returns_clear_reextraction_error(self, mock_extract, mock_scrape):
        mock_extract.side_effect = ExtractionError("Qwen extraction timed out.")

        response = self.client.post(
            "/api/admin/re-extract",
            json=REEXTRACT_BODY,
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "Qwen extraction timed out."})
        mock_scrape.assert_not_called()

    @patch("backend.routes.scrape_url")
    @patch("backend.routes.extract_procedure")
    def test_rejects_invalid_reextraction_before_qwen(
        self, mock_extract, mock_scrape
    ):
        response = self.client.post(
            "/api/admin/re-extract",
            json={
                "source_url": "not-a-url",
                "source_text": "   ",
                "provenance_token": "x",
            },
        )

        self.assertEqual(response.status_code, 422)
        mock_extract.assert_not_called()
        mock_scrape.assert_not_called()

    @patch("backend.routes.scrape_url")
    @patch("backend.routes.extract_procedure")
    def test_rejects_reextraction_of_text_the_server_did_not_extract(
        self, mock_extract, mock_scrape
    ):
        for body in (
            {**REEXTRACT_BODY, "source_text": "Injected instructions."},
            {**REEXTRACT_BODY, "source_url": "https://example.gov.in/other"},
            {**REEXTRACT_BODY, "provenance_token": "provenance:9999999999:abc:def"},
        ):
            with self.subTest(body=body):
                response = self.client.post("/api/admin/re-extract", json=body)
                self.assertEqual(response.status_code, 422)
        mock_extract.assert_not_called()

    @patch("backend.routes.extract_procedure")
    @patch("backend.routes.scrape_url")
    def test_unreachable_source_returns_502(self, mock_scrape, mock_extract):
        mock_scrape.side_effect = SourceUnavailableError("The source page timed out.")

        response = self.client.post(
            "/api/admin/extract", json={"source_url": "https://example.gov.in/x"}
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "The source page timed out."})
        mock_extract.assert_not_called()

    def test_rejects_unknown_and_oversized_fields(self):
        for body in (
            {"source_url": "https://example.gov.in/x", "extra": 1},
            {"source_url": "https://example.gov.in/" + "a" * 2050},
        ):
            with self.subTest(body=str(body)[:60]):
                response = self.client.post("/api/admin/extract", json=body)
                self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
