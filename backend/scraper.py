import ipaddress
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


HTTP_TIMEOUT = 20.0
BROWSER_TIMEOUT_MS = 30_000
RENDER_WAIT_MS = 1_000
MAX_REDIRECTS = 10
USER_AGENT = "ProcedureAssistAI/1.0"
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
MIN_SOURCE_CHARACTERS = 200
MIN_SOURCE_WORDS = 20
PLACEHOLDER_PHRASES = ("enable javascript", "javascript is required", "loading")
CONTENT_TAGS = (
    "title",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "li",
    "th",
    "td",
    "dt",
    "dd",
    "label",
    "legend",
)


class ScraperError(Exception):
    pass


def validate_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ScraperError("URL is required.")

    url = url.strip()
    if any(character.isspace() for character in url):
        raise ScraperError("Invalid URL.")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ScraperError("Only HTTP and HTTPS URLs are supported.")
    if not parsed.hostname:
        raise ScraperError("Invalid URL hostname.")

    try:
        parsed.port
    except ValueError as error:
        raise ScraperError("Invalid URL port.") from error

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(
        ".localhost"
    ):
        raise ScraperError("Localhost URLs are not allowed.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return url

    if not address.is_global:
        raise ScraperError("Private or local network URLs are not allowed.")

    return url


def fetch_static_html(
    url: str, timeout: float = HTTP_TIMEOUT
) -> tuple[str, str]:
    current_url = validate_url(url)

    try:
        with httpx.Client(
            follow_redirects=False,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                response = client.get(current_url)

                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ScraperError(
                            "Redirect response did not include a destination."
                        )
                    current_url = validate_url(
                        urljoin(str(response.url), location)
                    )
                    continue

                response.raise_for_status()

                final_url = validate_url(str(response.url))
                content_type = (
                    response.headers.get("content-type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if content_type not in HTML_CONTENT_TYPES:
                    raise ScraperError(
                        f"Unsupported content type: {content_type or 'unknown'}."
                    )

                html = response.text
                if not html.strip():
                    raise ScraperError("The source page returned empty HTML.")

                return final_url, html

        raise ScraperError("Too many redirects.")
    except ScraperError:
        raise
    except httpx.TimeoutException as error:
        raise ScraperError("The source page timed out.") from error
    except httpx.HTTPStatusError as error:
        raise ScraperError(
            f"The source page returned HTTP {error.response.status_code}."
        ) from error
    except httpx.RequestError as error:
        raise ScraperError("Unable to retrieve the source page.") from error


def clean_html(html: str) -> str:
    if not isinstance(html, str) or not html.strip():
        raise ScraperError("No meaningful page content found.")

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(
        ["script", "style", "noscript", "svg", "canvas", "template", "nav"]
    ):
        tag.decompose()

    for tag in soup.select("[hidden], [aria-hidden='true']"):
        tag.decompose()

    for tag in soup.find_all(style=True):
        style = tag["style"].lower().replace(" ", "")
        if "display:none" in style or "visibility:hidden" in style:
            tag.decompose()

    blocks = []
    for tag in soup.find_all(CONTENT_TAGS):
        if tag.find_parent(CONTENT_TAGS):
            continue

        text = " ".join(tag.get_text(" ", strip=True).split())
        if text and (not blocks or text != blocks[-1]):
            blocks.append(text)

    source_text = "\n\n".join(blocks)
    if not source_text:
        raise ScraperError("No meaningful page content found.")

    return source_text


def is_source_text_usable(source_text: str) -> bool:
    if not isinstance(source_text, str):
        return False

    normalized = " ".join(source_text.split())
    words = normalized.split()
    if any(
        phrase in normalized.lower() for phrase in PLACEHOLDER_PHRASES
    ) and len(normalized) < 500:
        return False

    return (
        len(normalized) >= MIN_SOURCE_CHARACTERS
        and len(words) >= MIN_SOURCE_WORDS
    )


def fetch_rendered_html(
    url: str, timeout_ms: int = BROWSER_TIMEOUT_MS
) -> tuple[str, str]:
    validated_url = validate_url(url)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)

                def handle_request(route):
                    request_url = route.request.url
                    if urlparse(request_url).scheme.lower() in {"http", "https"}:
                        try:
                            validate_url(request_url)
                        except ScraperError:
                            route.abort()
                            return
                    route.continue_()

                page.route("**/*", handle_request)
                response = page.goto(
                    validated_url,
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )
                if response is not None and not response.ok:
                    raise ScraperError(
                        f"The rendered page returned HTTP {response.status}."
                    )

                page.wait_for_timeout(RENDER_WAIT_MS)
                final_url = validate_url(page.url)
                html = page.content()
                if not html.strip():
                    raise ScraperError("The rendered page returned empty HTML.")

                return final_url, html
            finally:
                browser.close()
    except ScraperError:
        raise
    except PlaywrightTimeoutError as error:
        raise ScraperError("The rendered page timed out.") from error
    except PlaywrightError as error:
        raise ScraperError("The rendered page could not be loaded.") from error
