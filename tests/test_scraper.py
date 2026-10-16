import socket
import unittest
from unittest.mock import patch

import httpx

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from backend.scraper import (
    MAX_RESPONSE_BYTES,
    ScraperError,
    SourceUnavailableError,
    clean_html,
    fetch_static_html,
    fetch_rendered_html,
    is_source_text_usable,
    normalize_url,
    scrape_url,
    validate_url,
)


def resolves_to(*addresses):
    return patch(
        "backend.scraper.socket.getaddrinfo",
        return_value=[(None, None, None, "", (address, 0)) for address in addresses],
    )


# Unit tests never use real DNS: every host resolves to a public address
# unless a test patches getaddrinfo itself.
_public_dns = resolves_to("93.184.216.34")
setUpModule = _public_dns.start
tearDownModule = _public_dns.stop


def html_response(url, status=200, headers=None, body=b"<p>Hello</p>"):
    headers = {"content-type": "text/html; charset=utf-8", **(headers or {})}
    return httpx.Response(
        status, headers=headers, content=body, request=httpx.Request("GET", url)
    )


class ValidateUrlTest(unittest.TestCase):
    def test_accepts_public_hosts(self):
        self.assertEqual(
            validate_url(" https://example.gov.in/a "), "https://example.gov.in/a"
        )

    def test_rejects_unsafe_urls(self):
        for url in (
            "",
            "ftp://example.gov.in/file",
            "https://exa mple.gov.in/",
            "https://user:pass@example.gov.in/",
            "http://localhost:8000/",
            "http://api.localhost/",
            "http://127.0.0.1/",
            "http://10.1.2.3/",
            "http://[::1]/",
            "http://[::ffff:127.0.0.1]/",
            "http://169.254.169.254/latest/meta-data",
            "http://224.0.0.1/",
            "https://example.gov.in:99999/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ScraperError):
                    validate_url(url)

    def test_rejects_hosts_resolving_to_private_addresses(self):
        for addresses in (("10.0.0.5",), ("93.184.216.34", "127.0.0.1"), ("::1",)):
            with self.subTest(addresses=addresses), resolves_to(*addresses):
                with self.assertRaisesRegex(ScraperError, "Private or local"):
                    validate_url("https://rebind.example.gov.in/")

    def test_unresolvable_host_is_an_upstream_failure(self):
        with patch(
            "backend.scraper.socket.getaddrinfo",
            side_effect=socket.gaierror("no such host"),
        ):
            with self.assertRaises(SourceUnavailableError):
                validate_url("https://missing.example.gov.in/")


class NormalizeUrlTest(unittest.TestCase):
    def test_normalizes_equivalent_urls(self):
        cases = {
            "HTTPS://WWW.Example.GOV.in/Path/": "https://www.example.gov.in/Path",
            "https://example.gov.in:443/a#section": "https://example.gov.in/a",
            "http://example.gov.in:80": "http://example.gov.in/",
            "https://example.gov.in:8443/a/?b=1&a=2": "https://example.gov.in:8443/a?b=1&a=2",
            "http://[2001:db8::1]/x/": "http://[2001:db8::1]/x",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(normalize_url(url), expected)


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

    def test_keeps_main_content_and_removes_page_chrome(self):
        html = """
        <html>
          <body>
            <header>
              <ul><li>Home</li><li>Departments</li><li>Contact</li></ul>
            </header>
            <main>
              <div class="breadcrumbs"><p>Home / Passport Services</p></div>
              <h1>Apply for a Passport</h1>
              <p>Complete the application and schedule an appointment.</p>
              <aside><p>Related government services</p></aside>
            </main>
            <footer><p>Privacy policy</p></footer>
          </body>
        </html>
        """

        self.assertEqual(
            clean_html(html),
            "Apply for a Passport\n\n"
            "Complete the application and schedule an appointment.",
        )

    def test_removes_semantic_chrome_when_main_is_missing(self):
        html = """
        <html>
          <head><title>Passport Service</title></head>
          <body>
            <header><p>Government portal menu</p></header>
            <section>
              <h1>Passport Renewal</h1>
              <p>Submit the renewal form with the required documents.</p>
            </section>
            <footer><p>Terms and conditions</p></footer>
          </body>
        </html>
        """

        self.assertEqual(
            clean_html(html),
            "Passport Service\n\n"
            "Passport Renewal\n\n"
            "Submit the renewal form with the required documents.",
        )

    def test_handles_styled_elements_inside_hidden_styled_parent(self):
        html = """
        <body>
          <div style="display:none"><span style="color:red">Hidden banner</span></div>
          <p>Apply online through the official portal.</p>
        </body>
        """

        self.assertEqual(
            clean_html(html), "Apply online through the official portal."
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

    def test_placeholder_words_inside_other_words_are_not_placeholders(self):
        procedure_text = (
            "Applicants should complete the form and attach scanned copies "
            "before uploading documents to the portal. "
        ) * 3

        self.assertLess(len(procedure_text), 500)
        self.assertTrue(is_source_text_usable(procedure_text))


class StaticFetchTest(unittest.TestCase):
    def fetch(self, *responses):
        with patch("backend.scraper.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.send.side_effect = list(responses)
            return fetch_static_html("https://example.gov/page"), client

    def test_retries_once_after_connection_reset(self):
        result, client = self.fetch(
            httpx.ConnectError("reset"), html_response("https://example.gov/page")
        )

        self.assertEqual(result, ("https://example.gov/page", "<p>Hello</p>"))
        self.assertEqual(client.send.call_count, 2)
        with self.assertRaisesRegex(SourceUnavailableError, "Unable to retrieve"):
            self.fetch(httpx.ConnectError("reset"), httpx.ConnectError("reset"))

    def test_follows_validated_redirects(self):
        result, _ = self.fetch(
            html_response("https://example.gov/page", 302, {"location": "/final"}),
            html_response("https://example.gov/final"),
        )
        self.assertEqual(result[0], "https://example.gov/final")

    def test_rejects_redirect_to_private_network(self):
        with self.assertRaisesRegex(ScraperError, "Localhost"):
            self.fetch(
                html_response(
                    "https://example.gov/page", 302, {"location": "http://localhost/"}
                )
            )

    def test_rejects_oversized_responses(self):
        too_big = str(MAX_RESPONSE_BYTES + 1)
        for response in (
            html_response("https://example.gov/page", headers={"content-length": too_big}),
            html_response("https://example.gov/page", body=b"x" * (MAX_RESPONSE_BYTES + 1)),
        ):
            with self.subTest(), self.assertRaisesRegex(ScraperError, "too large"):
                self.fetch(response)

    def test_classifies_failures(self):
        cases = (
            (httpx.ReadTimeout("slow"), SourceUnavailableError, "timed out"),
            (html_response("https://example.gov/page", 503), SourceUnavailableError, "HTTP 503"),
            (html_response("https://example.gov/page", 404), ScraperError, "HTTP 404"),
            (
                html_response("https://example.gov/page", headers={"content-type": "application/pdf"}),
                ScraperError,
                "application/pdf",
            ),
        )
        for response, error, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(error, message) as raised:
                    self.fetch(response)
                if error is ScraperError:
                    self.assertNotIsInstance(raised.exception, SourceUnavailableError)


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

    @patch("backend.scraper.sync_playwright")
    def test_rejects_failed_or_oversized_rendered_pages(self, sync_playwright):
        playwright = sync_playwright.return_value.__enter__.return_value
        page = playwright.chromium.launch.return_value.new_page.return_value
        page.url = "https://example.gov/final"

        page.goto.return_value.ok = False
        page.goto.return_value.status = 503
        with self.assertRaisesRegex(SourceUnavailableError, "HTTP 503"):
            fetch_rendered_html("https://example.gov/start")

        page.goto.return_value.ok = True
        page.content.return_value = "x" * (MAX_RESPONSE_BYTES + 1)
        with self.assertRaisesRegex(ScraperError, "too large"):
            fetch_rendered_html("https://example.gov/start")


class ScrapeUrlTest(unittest.TestCase):
    usable_html = """
    <h1>Passport Renewal Application</h1>
    <p>
      Eligible applicants can renew an expired passport through the official
      government portal. Complete the application form, upload proof of
      address and date of birth, pay the required fee, and schedule an
      appointment. Bring the original documents and application receipt to
      the passport office for verification on the selected date. Applicants
      should confirm current fees and office hours before attending.
    </p>
    """

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_returns_usable_static_content(
        self, fetch_static_html, fetch_rendered_html
    ):
        fetch_static_html.return_value = (
            "https://example.gov/final",
            self.usable_html,
        )

        result = scrape_url("https://example.gov/start")

        self.assertEqual(result.source_url, "https://example.gov/final")
        self.assertIn("Passport Renewal Application", result.source_text)
        fetch_rendered_html.assert_not_called()

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_uses_browser_for_insufficient_static_content(
        self, fetch_static_html, fetch_rendered_html
    ):
        fetch_static_html.return_value = (
            "https://example.gov/start",
            "<p>Loading...</p>",
        )
        fetch_rendered_html.return_value = (
            "https://example.gov/rendered",
            self.usable_html,
        )

        result = scrape_url("https://example.gov/start")

        self.assertEqual(result.source_url, "https://example.gov/rendered")
        fetch_rendered_html.assert_called_once_with(
            "https://example.gov/start"
        )

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_rejects_insufficient_rendered_content(
        self, fetch_static_html, fetch_rendered_html
    ):
        fetch_static_html.return_value = (
            "https://example.gov/start",
            "<p>Loading...</p>",
        )
        fetch_rendered_html.return_value = (
            "https://example.gov/start",
            "<p>Please enable JavaScript.</p>",
        )

        with self.assertRaisesRegex(
            ScraperError, "No meaningful page content found"
        ):
            scrape_url("https://example.gov/start")

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_returns_normalized_source_url(self, fetch_static_html, fetch_rendered_html):
        fetch_static_html.return_value = (
            "HTTPS://Example.GOV/Final/#top",
            self.usable_html,
        )

        result = scrape_url("https://example.gov/start")

        self.assertEqual(result.source_url, "https://example.gov/Final")

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_rejects_pages_with_too_much_text(self, fetch_static_html, fetch_rendered_html):
        fetch_static_html.return_value = (
            "https://example.gov/final",
            "<p>" + "word " * 30_000 + "</p>",
        )

        with self.assertRaisesRegex(ScraperError, "too much text"):
            scrape_url("https://example.gov/start")

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_does_not_use_browser_for_static_errors(
        self, fetch_static_html, fetch_rendered_html
    ):
        fetch_static_html.side_effect = ScraperError(
            "Unsupported content type: application/pdf."
        )

        with self.assertRaisesRegex(ScraperError, "application/pdf"):
            scrape_url("https://example.gov/document.pdf")
        fetch_rendered_html.assert_not_called()


if __name__ == "__main__":
    unittest.main()
