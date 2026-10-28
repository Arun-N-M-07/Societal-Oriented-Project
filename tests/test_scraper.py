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
    require_official,
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
            "https://example.gov.in/a?mobile-app=1&utm_source=chatgpt.com": "https://example.gov.in/a?mobile-app=1",
            "https://example.gov.in/a?utm_source=x&UTM_medium=y": "https://example.gov.in/a",
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
            "Fee ₹1,500",
        )

    def test_keeps_each_table_row_together_with_its_fee(self):
        html = """
        <main><table>
          <tr><th>Purpose</th><th>Amount in Rs.</th></tr>
          <tr><td>Renewal of driving licence</td><td><p>Rs. 200.00/-</p></td></tr>
          <tr><td>Issue of duplicate licence to a school</td><td>Rs. 5000.00/-</td></tr>
        </table></main>
        """

        self.assertEqual(
            clean_html(html),
            "Purpose Amount in Rs.\n\n"
            "Renewal of driving licence Rs. 200.00/-\n\n"
            "Issue of duplicate licence to a school Rs. 5000.00/-",
        )

    def test_fee_sub_rows_keep_their_numbered_parent_row(self):
        html = """
        <main><table>
          <tr><th>Sl.No.</th><th>Purpose</th><th>Amount</th></tr>
          <tr><td>2.</td><td colspan="2">Duplicate trade certificate:</td></tr>
          <tr><td></td><td>(a) Motorcycle</td><td>Rupees Three Hundred Only</td></tr>
          <tr><td>4.</td><td colspan="2">Issue or renewal of certificate of registration:</td></tr>
          <tr><td></td><td>(b) Motor cycle</td><td>Rupees Three Hundred Only</td></tr>
          <tr><td></td><td colspan="2">(c) Three wheeler/Light Motor Vehicles:</td></tr>
          <tr><td></td><td>i) Non transport;</td><td>Rupees Six Hundred Only</td></tr>
          <tr><td></td><td>(d) Medium goods vehicle</td><td>Rupees One Thousand Only</td></tr>
          <tr><td>5.</td><td>Issue of duplicate certificate of registration</td><td>Half of the fee</td></tr>
        </table></main>
        """

        self.assertEqual(clean_html(html).split("\n\n"), [
            "Sl.No. Purpose Amount",
            "2. Duplicate trade certificate:",
            "2. Duplicate trade certificate: (a) Motorcycle Rupees Three Hundred Only",
            "4. Issue or renewal of certificate of registration:",
            "4. Issue or renewal of certificate of registration: (b) Motor cycle Rupees Three Hundred Only",
            "4. Issue or renewal of certificate of registration: (c) Three wheeler/Light Motor Vehicles:",
            "4. Issue or renewal of certificate of registration: (c) Three wheeler/Light Motor Vehicles: "
            "i) Non transport; Rupees Six Hundred Only",
            # A sibling "(d)" row is not put under the "(c)" heading.
            "4. Issue or renewal of certificate of registration: (d) Medium goods vehicle Rupees One Thousand Only",
            "5. Issue of duplicate certificate of registration Half of the fee",
        ])

    def test_rows_of_ordinary_tables_get_no_parent(self):
        html = """
        <main><table>
          <tr><th>S.no</th><th>Service</th><th>Fee</th></tr>
          <tr><td>1</td><td>Aadhaar Enrolment</td><td>FREE</td></tr>
          <tr><td>4</td><td>Biometric update</td><td>₹125</td></tr>
        </table>
        <table><tr><td></td><td>Photo</td></tr><tr><td></td><td>Address Proof</td></tr></table></main>
        """

        self.assertEqual(clean_html(html).split("\n\n"),
                         ["S.no Service Fee", "1 Aadhaar Enrolment FREE", "4 Biometric update ₹125", "Photo", "Address Proof"])

    def test_keeps_text_held_directly_in_divs_spans_and_accordion_questions(self):
        html = """
        <main>
          <h2>Who It Covers?</h2>
          <div class="card"><div>Age group: 18–54 years.</div><div>Must be an Indian resident.</div></div>
          <details><summary>Can apprentices become EPF members?</summary><p>No.</p></details>
          <div class="card-header"><a href="#q7">7. What documents are required for a Community Certificate?</a></div>
          <div class="card-body"><p>Photo</p></div>
          <section><span>*Inclusive of GST</span><p>Fees are collected at the centre.</p></section>
        </main>
        """

        self.assertEqual(
            clean_html(html),
            "Who It Covers?\n\n"
            "Age group: 18–54 years.\n\n"
            "Must be an Indian resident.\n\n"
            "Can apprentices become EPF members?\n\n"
            "No.\n\n"
            "7. What documents are required for a Community Certificate?\n\n"
            "Photo\n\n"
            "*Inclusive of GST\n\n"
            "Fees are collected at the centre.",
        )

    def test_removes_menus_of_repeated_link_labels_but_keeps_repetitive_prose(self):
        menu = ("Individual Guidance to file Tax Return Return / Forms applicable to me Tax slabs "
                "Senior Citizen Guidance to file Tax Return Return / Forms applicable to me Tax slabs "
                "Non Resident Guidance to file Tax Return Return / Forms applicable to me Tax slabs")
        prose = ("Fill Form 6 (Link to online form). NRI voters fill Form 6A (Link to online form). "
                 "For corrections fill Form 8 (Link to online form).")
        html = f"<main><h1>Link PAN with Aadhaar</h1><p>{menu}</p><p>{prose}</p></main>"

        self.assertEqual(clean_html(html), f"Link PAN with Aadhaar\n\n{prose}")

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
        # An error page served as success is not content either.
        error_page = ("404 Page | Election Commission of India 404 Ooops!!! The page you are looking for is not found "
                      "Back to home Election Commission of India Accessibility Tools Screen Reader Access Skip to "
                      "main content Contact Us Sitemap Help Feedback Terms of Use Privacy Policy Copyright Policy")
        self.assertFalse(is_source_text_usable(error_page))

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


class OfficialSourceTest(unittest.TestCase):
    def test_only_official_domains_and_their_subdomains(self):
        for url in ["https://parivahan.gov.in/en/content/renewal", "https://tnesevai.tn.gov.in/Citizen/FAQ.html",
                    "https://ecisveep.nic.in/voters", "https://www.pfrda.org.in/schemes/apy", "https://GOV.IN./"]:
            with self.subTest(url):
                self.assertEqual(require_official(url), url)
        for url in ["https://example.com/gov.in", "https://gov.in.example.com/", "https://notgov.in/",
                    "https://www.gov.uk/renew-driving-licence", "https://pfrda.org.in.evil.example/"]:
            with self.subTest(url):
                with self.assertRaisesRegex(ScraperError, "official government websites"):
                    require_official(url)

    @patch("backend.scraper.fetch_static_html")
    def test_the_page_after_redirects_must_be_official_too(self, fetch_static_html):
        with self.assertRaisesRegex(ScraperError, "official"):
            scrape_url("https://example.com/page")
        fetch_static_html.assert_not_called()
        fetch_static_html.return_value = ("https://example.com/landing", ScrapeUrlTest.usable_html)
        with self.assertRaisesRegex(ScraperError, "official"):
            scrape_url("https://example.gov.in/moved")


class ConnectedAddressTest(unittest.TestCase):
    def test_a_host_that_resolves_to_a_private_address_on_connection_is_rejected(self):
        class Stream:
            def get_extra_info(self, name):
                return ("10.0.0.5", 443) if name == "server_addr" else None

        rebound = html_response("https://example.gov/page")
        rebound.extensions["network_stream"] = Stream()
        with patch("backend.scraper.httpx.Client") as client_class:
            client_class.return_value.__enter__.return_value.send.return_value = rebound
            with self.assertRaisesRegex(ScraperError, "Private or local"):
                fetch_static_html("https://example.gov/page")

    @patch("backend.scraper.sync_playwright")
    def test_the_rendered_page_is_checked_the_same_way(self, sync_playwright):
        page = sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value
        page.goto.return_value.server_addr.return_value = {"ipAddress": "127.0.0.1", "port": 443}
        with self.assertRaisesRegex(ScraperError, "Private or local"):
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
            "https://example.gov.in/final",
            self.usable_html,
        )

        result = scrape_url("https://example.gov.in/start")

        self.assertEqual(result.source_url, "https://example.gov.in/final")
        self.assertIn("Passport Renewal Application", result.source_text)
        fetch_rendered_html.assert_not_called()

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_uses_browser_for_insufficient_static_content(
        self, fetch_static_html, fetch_rendered_html
    ):
        fetch_static_html.return_value = (
            "https://example.gov.in/start",
            "<p>Loading...</p>",
        )
        fetch_rendered_html.return_value = (
            "https://example.gov.in/rendered",
            self.usable_html,
        )

        result = scrape_url("https://example.gov.in/start")

        self.assertEqual(result.source_url, "https://example.gov.in/rendered")
        fetch_rendered_html.assert_called_once_with(
            "https://example.gov.in/start"
        )

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_rejects_insufficient_rendered_content(
        self, fetch_static_html, fetch_rendered_html
    ):
        fetch_static_html.return_value = (
            "https://example.gov.in/start",
            "<p>Loading...</p>",
        )
        fetch_rendered_html.return_value = (
            "https://example.gov.in/start",
            "<p>Please enable JavaScript.</p>",
        )

        with self.assertRaisesRegex(
            ScraperError, "No meaningful page content found"
        ):
            scrape_url("https://example.gov.in/start")

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_returns_normalized_source_url(self, fetch_static_html, fetch_rendered_html):
        fetch_static_html.return_value = (
            "HTTPS://Example.GOV.IN/Final/#top",
            self.usable_html,
        )

        result = scrape_url("https://example.gov.in/start")

        self.assertEqual(result.source_url, "https://example.gov.in/Final")

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_rejects_pages_with_too_much_text(self, fetch_static_html, fetch_rendered_html):
        fetch_static_html.return_value = (
            "https://example.gov.in/final",
            "<p>" + "Apply at the office. " * 6_000 + "</p>",  # prose, so not a menu
        )

        with self.assertRaisesRegex(ScraperError, "too much text"):
            scrape_url("https://example.gov.in/start")

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_uses_browser_when_the_page_cannot_be_fetched_directly(self, fetch_static_html, fetch_rendered_html):
        # e.g. a server that sends an incomplete certificate chain, which a browser completes and verifies
        fetch_static_html.side_effect = SourceUnavailableError("Unable to retrieve the source page.")
        fetch_rendered_html.return_value = ("https://example.gov.in/start", self.usable_html)
        self.assertIn("Passport Renewal Application", scrape_url("https://example.gov.in/start").source_text)
        fetch_rendered_html.side_effect = SourceUnavailableError("The rendered page could not be loaded.")
        with self.assertRaisesRegex(SourceUnavailableError, "rendered page"):
            scrape_url("https://example.gov.in/start")

    @patch("backend.scraper.fetch_rendered_html")
    @patch("backend.scraper.fetch_static_html")
    def test_does_not_use_browser_for_static_errors(
        self, fetch_static_html, fetch_rendered_html
    ):
        fetch_static_html.side_effect = ScraperError(
            "Unsupported content type: application/pdf."
        )

        with self.assertRaisesRegex(ScraperError, "application/pdf"):
            scrape_url("https://example.gov.in/document.pdf")
        fetch_rendered_html.assert_not_called()


if __name__ == "__main__":
    unittest.main()
