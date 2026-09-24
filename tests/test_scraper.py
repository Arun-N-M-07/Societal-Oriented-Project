import unittest
from unittest.mock import patch

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from backend.scraper import (
    ScraperError,
    clean_html,
    fetch_rendered_html,
    is_source_text_usable,
)


class CleanHtmlTest(unittest.TestCase):
    def test_keeps_content_and_removes_noise(self):
        html = """
        <html>
          <head>
            <title>Passport Service</title>
            <style>.hidden { display: none; }</style>
            <script>trackVisitor()</script>
          </head>
          <body>
            <nav><a href="/">Home</a></nav>
            <h1>Apply for a Passport</h1>
            <p>Applicants <strong>must</strong> bring&nbsp;proof.</p>
            <ul>
              <li>Proof of address</li>
              <li hidden>Hidden instruction</li>
            </ul>
            <table><tr><th>Fee</th><td>₹1,500</td></tr></table>
          </body>
        </html>
        """

        self.assertEqual(
            clean_html(html),
            "Passport Service\n\n"
            "Apply for a Passport\n\n"
            "Applicants must bring proof.\n\n"
            "Proof of address\n\n"
            "Fee\n\n"
            "₹1,500",
        )


class SourceTextUsabilityTest(unittest.TestCase):
    def test_identifies_useful_content(self):
        procedure_text = """
        Passport Renewal Application

        Eligible applicants can renew an expired passport through the official
        portal. Complete the application form, upload proof of address and date
        of birth, pay the required fee, and schedule an appointment. Bring the
        original documents and application receipt to the passport office for
        verification on the selected date.
        """

        self.assertTrue(is_source_text_usable(procedure_text))
        self.assertFalse(is_source_text_usable(""))
        self.assertFalse(is_source_text_usable("Loading... " * 30))
        self.assertFalse(
            is_source_text_usable("Please enable JavaScript to continue.")
        )


class RenderedHtmlTest(unittest.TestCase):
    @patch("backend.scraper.sync_playwright")
    def test_returns_html_and_closes_browser(self, sync_playwright):
        playwright = sync_playwright.return_value.__enter__.return_value
        browser = playwright.chromium.launch.return_value
        page = browser.new_page.return_value
        response = page.goto.return_value
        response.ok = True
        page.url = "https://example.gov/final"
        page.content.return_value = "<html><p>Rendered content</p></html>"

        self.assertEqual(
            fetch_rendered_html("https://example.gov/start"),
            (
                "https://example.gov/final",
                "<html><p>Rendered content</p></html>",
            ),
        )
        browser.close.assert_called_once()

        browser.reset_mock()
        page.goto.side_effect = PlaywrightTimeoutError("Timed out")
        with self.assertRaisesRegex(ScraperError, "rendered page timed out"):
            fetch_rendered_html("https://example.gov/start")
        browser.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
