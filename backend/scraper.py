from __future__ import annotations

import ipaddress
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


DEFAULT_TIMEOUT = 30.0
PLAYWRIGHT_TIMEOUT = 45_000
MAX_SOURCE_TEXT_LENGTH = 100_000
MIN_MEANINGFUL_TEXT_LENGTH = 20

USER_AGENT = (
    "ProcedureAssistAI/1.0 "
    "(Government Procedure Information Retrieval)"
)


class ScraperError(Exception):
    """Controlled error raised for scraper failures."""


# ============================================================
# URL VALIDATION
# ============================================================

def validate_url(url: str) -> str:
    """Validate and normalize a supplied HTTP/HTTPS URL."""

    if not isinstance(url, str) or not url.strip():
        raise ScraperError("URL is required.")

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ScraperError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.netloc:
        raise ScraperError("Invalid URL.")

    hostname = parsed.hostname

    if not hostname:
        raise ScraperError("Invalid URL hostname.")

    hostname = hostname.lower().rstrip(".")

    blocked_hosts = {
        "localhost",
        "localhost.localdomain",
    }

    if hostname in blocked_hosts:
        raise ScraperError("Localhost URLs are not allowed.")

    try:
        ip = ipaddress.ip_address(hostname)

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            raise ScraperError(
                "Private or local network URLs are not allowed."
            )

    except ValueError:
        # Normal domain name.
        pass

    return url


# ============================================================
# HTML CLEANING
# ============================================================

def _remove_unwanted_elements(soup: BeautifulSoup) -> None:
    """
    Remove elements that normally do not contain useful
    government procedure information.
    """

    unwanted_tags = [
        "script",
        "style",
        "noscript",
        "svg",
        "canvas",
        "iframe",
        "object",
        "embed",
        "form",
        "input",
        "button",
        "select",
        "textarea",
        "nav",
        "footer",
        "aside",
    ]

    for tag_name in unwanted_tags:
        for tag in soup.find_all(tag_name):
            tag.decompose()


def _clean_text(text: str) -> str:
    """Normalize scraped text."""

    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Collapse horizontal whitespace.
    text = re.sub(r"[ \t]+", " ", text)

    lines = []

    for line in text.split("\n"):
        line = line.strip()

        if not line:
            continue

        lines.append(line)

    # Remove immediately repeated lines.
    cleaned_lines = []

    for line in lines:
        if not cleaned_lines or cleaned_lines[-1] != line:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    if len(text) > MAX_SOURCE_TEXT_LENGTH:
        text = text[:MAX_SOURCE_TEXT_LENGTH].rstrip()

    return text


# ============================================================
# GOVERNMENT PAGE EXTRACTION
# ============================================================

def _extract_page_content(html: str, source_url: str) -> str:
    """
    Extract useful information from a government page.

    The function handles:
    - normal article content
    - headings
    - page titles
    - important links
    - government homepage content
    """

    if not html or not html.strip():
        raise ScraperError("The downloaded page is empty.")

    soup = BeautifulSoup(html, "html.parser")

    # Save useful metadata before removing elements.
    title = ""

    if soup.title:
        title = soup.title.get_text(" ", strip=True)

    headings = []

    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = tag.get_text(" ", strip=True)

        if text:
            headings.append(text)

    # Remove unnecessary elements.
    _remove_unwanted_elements(soup)

    # Try to find the main content.
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(
            id=re.compile(
                r"(main|content|article|body-content)",
                re.I,
            )
        )
        or soup.body
        or soup
    )

    body_text = main.get_text(
        separator="\n",
        strip=True,
    )

    body_text = _clean_text(body_text)

    # --------------------------------------------------------
    # Extract useful links.
    #
    # This is important for government homepages because
    # some sites render very little visible text while their
    # actual services are represented by links.
    # --------------------------------------------------------

    links = []

    for link in soup.find_all("a", href=True):

        link_text = link.get_text(" ", strip=True)
        href = link.get("href")

        if not link_text or not href:
            continue

        # Ignore tiny/non-informative links.
        if len(link_text) < 3:
            continue

        absolute_url = urljoin(source_url, href)

        parsed = urlparse(absolute_url)

        if parsed.scheme not in {"http", "https"}:
            continue

        entry = f"{link_text} -> {absolute_url}"

        if entry not in links:
            links.append(entry)

    # Limit number of links so a huge menu does not dominate
    # the extracted source.
    links = links[:150]

    # --------------------------------------------------------
    # Build final source text.
    # --------------------------------------------------------

    sections = []

    if title:
        sections.append(f"PAGE TITLE:\n{title}")

    if headings:
        unique_headings = []

        for heading in headings:
            if heading not in unique_headings:
                unique_headings.append(heading)

        sections.append(
            "PAGE HEADINGS:\n"
            + "\n".join(unique_headings[:100])
        )

    if body_text:
        sections.append(
            "PAGE CONTENT:\n"
            + body_text
        )

    if links:
        sections.append(
            "IMPORTANT LINKS:\n"
            + "\n".join(links)
        )

    final_text = "\n\n".join(sections)
    final_text = _clean_text(final_text)

    if not final_text:
        raise ScraperError(
            "No readable content could be extracted from the page."
        )

    return final_text


# ============================================================
# HTTP FETCH
# ============================================================

def _is_html_response(response: httpx.Response) -> bool:
    """Check whether the response contains HTML."""

    content_type = response.headers.get(
        "content-type",
        "",
    ).lower()

    return (
        "text/html" in content_type
        or "application/xhtml+xml" in content_type
        or not content_type
    )


def fetch_with_httpx(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Download a page using httpx."""

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-IN,en;q=0.9",
        "Cache-Control": "no-cache",
    }

    try:

        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
        ) as client:

            response = client.get(url)

            response.raise_for_status()

            if not _is_html_response(response):
                raise ScraperError(
                    "The URL did not return an HTML page."
                )

            if not response.text.strip():
                raise ScraperError(
                    "The server returned an empty page."
                )

            return response.text

    except ScraperError:
        raise

    except httpx.TimeoutException as exc:
        raise ScraperError(
            "The government page took too long to respond."
        ) from exc

    except httpx.HTTPStatusError as exc:

        status = exc.response.status_code

        raise ScraperError(
            f"The source page returned HTTP {status}."
        ) from exc

    except httpx.RequestError as exc:

        raise ScraperError(
            f"Unable to connect to the source website: {exc}"
        ) from exc

    except Exception as exc:

        raise ScraperError(
            f"Unexpected error while downloading the page: {exc}"
        ) from exc


# ============================================================
# PLAYWRIGHT FALLBACK
# ============================================================

def fetch_with_playwright(
    url: str,
    timeout: int = PLAYWRIGHT_TIMEOUT,
) -> str:
    """
    Fetch JavaScript-rendered government pages using Playwright.
    """

    try:

        from playwright.sync_api import (
            TimeoutError as PlaywrightTimeoutError,
            sync_playwright,
        )

    except ImportError as exc:

        raise ScraperError(
            "Playwright is not installed. "
            "Run: python -m pip install playwright "
            "then: python -m playwright install chromium"
        ) from exc

    browser = None

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True
            )

            page = browser.new_page(
                user_agent=USER_AGENT,
                viewport={
                    "width": 1366,
                    "height": 768,
                },
            )

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout,
            )

            # Allow JavaScript to render.
            page.wait_for_timeout(3000)

            html = page.content()

            if not html.strip():
                raise ScraperError(
                    "Playwright returned an empty page."
                )

            return html

    except PlaywrightTimeoutError as exc:

        raise ScraperError(
            "The page timed out while being rendered."
        ) from exc

    except ScraperError:
        raise

    except Exception as exc:

        raise ScraperError(
            f"Playwright failed to load the page: {exc}"
        ) from exc

    finally:

        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass


# ============================================================
# MAIN SCRAPER
# ============================================================

def scrape_url(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    use_playwright_fallback: bool = True,
) -> dict[str, str]:
    """
    Main ProcedureAssist AI scraper.

    Flow:

        Government URL
              |
              v
        URL validation
              |
              v
        HTTP request
              |
              v
        BeautifulSoup
              |
              v
        Extract content
              |
              v
        If insufficient
              |
              v
        Playwright
              |
              v
        BeautifulSoup
              |
              v
        source_url + source_text
    """

    source_url = validate_url(url)

    first_error = None

    # ========================================================
    # 1. HTTPX
    # ========================================================

    try:

        html = fetch_with_httpx(
            source_url,
            timeout=timeout,
        )

        source_text = _extract_page_content(
            html,
            source_url,
        )

        # Do NOT require 200 characters.
        #
        # Government homepages can legitimately contain
        # very little visible text but still contain useful
        # titles, headings and service links.
        if len(source_text.strip()) >= MIN_MEANINGFUL_TEXT_LENGTH:

            return {
                "source_url": source_url,
                "source_text": source_text,
            }

        first_error = ScraperError(
            "HTTP page returned insufficient readable content."
        )

    except ScraperError as exc:

        first_error = exc

    # ========================================================
    # 2. PLAYWRIGHT FALLBACK
    # ========================================================

    if use_playwright_fallback:

        try:

            html = fetch_with_playwright(
                source_url
            )

            source_text = _extract_page_content(
                html,
                source_url,
            )

            if len(source_text.strip()) >= MIN_MEANINGFUL_TEXT_LENGTH:

                return {
                    "source_url": source_url,
                    "source_text": source_text,
                }

            raise ScraperError(
                "Playwright page returned insufficient "
                "readable content."
            )

        except ScraperError as playwright_error:

            raise ScraperError(
                "Unable to extract readable source text. "
                f"HTTP attempt: {first_error}. "
                f"Playwright attempt: {playwright_error}"
            ) from playwright_error

    raise ScraperError(
        "Unable to extract readable source text."
    )


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print("Usage:")
        print(
            "python -m backend.scraper "
            "<URL>"
        )

        raise SystemExit(1)

    target_url = sys.argv[1]

    print("=" * 70)
    print("PROCEDUREASSIST AI - GOVERNMENT SOURCE SCRAPER")
    print("=" * 70)

    print("\nURL:")
    print(target_url)

    print("\nScraping...")

    try:

        result = scrape_url(
            target_url
        )

        print("\nSUCCESS")
        print("=" * 70)

        print("\nSOURCE URL:")
        print(result["source_url"])

        print("\nSOURCE TEXT:")
        print(result["source_text"][:10000])

        print(
            "\nExtracted characters:",
            len(result["source_text"]),
        )

        print("\n" + "=" * 70)
        print("SCRAPING COMPLETED SUCCESSFULLY")
        print("=" * 70)

    except ScraperError as exc:

        print("\n" + "=" * 70)
        print("SCRAPER ERROR")
        print("=" * 70)

        print(exc)

        raise SystemExit(1)