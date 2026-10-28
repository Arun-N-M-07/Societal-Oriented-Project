import ipaddress
import re
import socket
from collections import Counter
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from backend.config import OFFICIAL_SOURCE_DOMAINS
from backend.schemas import MAX_SOURCE_TEXT_LENGTH, ScrapeResult


HTTP_TIMEOUT = 20.0
BROWSER_TIMEOUT_MS = 30_000
RENDER_WAIT_MS = 1_000
MAX_REDIRECTS = 10
MAX_RESPONSE_BYTES = 2_000_000
USER_AGENT = "ProcedureAssistAI/1.0"
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
MIN_SOURCE_CHARACTERS = 200
MIN_SOURCE_WORDS = 20
# A short page saying only this is a placeholder or an error page served as success ("404 ... not found").
PLACEHOLDER_PATTERN = re.compile(
    r"\b(enable javascript|javascript is required|loading|404|not found)\b", re.IGNORECASE
)
CONTENT_TAGS = (
    "title", "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "li", "th", "td", "dt", "dd", "label", "legend", "summary",
)
# Tags that hold other blocks, so a <div> or <span> containing one is a wrapper, not text.
BLOCK_TAGS = (*CONTENT_TAGS, "div", "tr", "ul", "ol", "table", "section", "article", "details")
# A table row holding any of these is page layout, not one row of data.
LAYOUT_TAGS = ("table", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6")


def is_menu(text: str) -> bool:
    """A run of link labels, not prose: the same four words three or more times and no
    sentence ending ("... Guidance to file Tax Return Return / Forms applicable to me ...")."""
    words = text.split()
    repeats = Counter(tuple(words[i:i + 4]) for i in range(len(words) - 3))
    return max(repeats.values(), default=0) >= 3 and not re.search(r"[.?!](?:\s|$)", text)


def _is_block(tag) -> bool:
    """One paragraph of the page: a content tag; a table row of plain cells, so a fee stays
    with its purpose ("Renewal of driving licence Rs. 200.00/-"); or a <div> or <span>
    holding text itself rather than other blocks (accordion questions, scheme cards)."""
    if tag.name == "tr":
        return tag.find(LAYOUT_TAGS) is None
    if tag.name in ("div", "span"):
        return tag.find(BLOCK_TAGS) is None and bool(tag.get_text(strip=True))
    return tag.name in CONTENT_TAGS


def _text(tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def _row_context(row) -> str:
    """The rows a fee sub-row belongs to. In a fee schedule a row with an empty first cell
    ("| (b) Motor cycle | Rupees Three Hundred Only |") continues the numbered row above it
    ("4. Issue or renewal of certificate of registration ...:"), and a row such as
    "i) Non transport;" also continues the label-only row "(c) Three wheeler ...:" above it."""
    cells = row.find_all(["td", "th"], recursive=False)
    if len(cells) < 2 or cells[0].name == "th" or _text(cells[0]):
        return ""
    own, sub = _text(cells[1]), None
    for previous in row.find_previous_siblings("tr"):
        before = previous.find_all(["td", "th"], recursive=False)
        if not before or before[0].name == "th":
            return ""
        if _text(before[0]):  # the numbered row this one continues
            return " ".join(filter(None, [_text(previous), sub]))
        label = _text(before[1]) if len(before) > 1 else ""
        if label.startswith("(") and sub is None:
            # The nearest "(x)" row heads this one only if it is a label alone and this row is not an "(x)" row.
            sub = label if len(before) == 2 and not own.startswith("(") else ""
    return ""


class ScraperError(Exception):
    """The submitted URL or page cannot be used (client error)."""


class SourceUnavailableError(ScraperError):
    """The source site could not be reached or failed (upstream error)."""


def _is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return ip.is_global and not ip.is_multicast


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or ""
    host = f"[{host}]" if ":" in host else host
    default_port = {"http": 80, "https": 443}.get(parts.scheme.lower())
    netloc = host if parts.port in (None, default_port) else f"{host}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    # Tracking parameters (utm_source=...) are not part of the official page.
    query = "&".join(p for p in parts.query.split("&") if p and not p.lower().startswith("utm_"))
    return urlunsplit((parts.scheme.lower(), netloc, path, query, ""))


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
    if parsed.username or parsed.password:
        raise ScraperError("URLs containing credentials are not allowed.")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(
        ".localhost"
    ):
        raise ScraperError("Localhost URLs are not allowed.")

    # Resolve the host and reject it if any address is not public. A host can
    # still re-resolve differently between this check and the connection (DNS
    # rebinding); every redirect hop and browser sub-request is re-checked.
    try:
        addresses = {str(ipaddress.ip_address(hostname))}
    except ValueError:
        try:
            addresses = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
        except (socket.gaierror, UnicodeError) as error:
            raise SourceUnavailableError("Could not resolve the source host.") from error
    if not addresses or not all(_is_public_address(a) for a in addresses):
        raise ScraperError("Private or local network URLs are not allowed.")

    return url


def require_official(url: str) -> str:
    """The page itself, before and after redirects, must be on an official domain. Pages may still load
    scripts and styles from elsewhere when rendered; those are only checked for safety (validate_url)."""
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if not any(host == domain or host.endswith(f".{domain}") for domain in OFFICIAL_SOURCE_DOMAINS):
        raise ScraperError("Only official government websites can be used as sources.")
    return url


def _check_connected_address(address: str | None) -> None:
    """The address actually connected to must be public too: a host can resolve differently between
    validate_url and the connection (DNS rebinding). Checked before the page is read."""
    if address and not _is_public_address(address):
        raise ScraperError("Private or local network URLs are not allowed.")


def _get_with_retry(client: httpx.Client, url: str) -> httpx.Response:
    # Some government sites reset the first connection at random; retry once.
    try:
        return client.send(client.build_request("GET", url), stream=True)
    except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
        return client.send(client.build_request("GET", url), stream=True)


def _read_limited(response: httpx.Response) -> str:
    if int(response.headers.get("content-length") or 0) > MAX_RESPONSE_BYTES:
        raise ScraperError("The source page is too large.")
    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ScraperError("The source page is too large.")
    return body.decode(response.encoding or "utf-8", errors="replace")


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
                response = _get_with_retry(client, current_url)
                try:
                    stream = response.extensions.get("network_stream")
                    _check_connected_address((stream.get_extra_info("server_addr") or [None])[0] if stream else None)
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

                    html = _read_limited(response)
                    if not html.strip():
                        raise ScraperError("The source page returned empty HTML.")

                    return final_url, html
                finally:
                    response.close()

        raise ScraperError("Too many redirects.")
    except ScraperError:
        raise
    except httpx.TimeoutException as error:
        raise SourceUnavailableError("The source page timed out.") from error
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        error_class = SourceUnavailableError if status >= 500 else ScraperError
        raise error_class(f"The source page returned HTTP {status}.") from error
    except httpx.RequestError as error:
        raise SourceUnavailableError("Unable to retrieve the source page.") from error


def clean_html(html: str) -> str:
    if not isinstance(html, str) or not html.strip():
        raise ScraperError("No meaningful page content found.")

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(
        ["script", "style", "noscript", "svg", "canvas", "template", "nav"]
    ):
        tag.decompose()

    content = soup.select_one("main, [role='main']")
    if content is None:
        for tag in soup(["header", "footer", "aside"]):
            tag.decompose()
        content = soup

    for tag in content(["footer", "aside"]):
        tag.decompose()

    for tag in content.select(
        "[role='navigation'], [role='banner'], [role='contentinfo'], "
        "[role='complementary'], .breadcrumb, .breadcrumbs, "
        "#breadcrumb, #breadcrumbs"
    ):
        tag.decompose()

    for tag in soup.select("[hidden], [aria-hidden='true']"):
        tag.decompose()

    for tag in soup.find_all(style=True):
        if tag.decomposed:
            continue
        style = tag["style"].lower().replace(" ", "")
        if "display:none" in style or "visibility:hidden" in style:
            tag.decompose()

    blocks = []
    for tag in content.find_all(_is_block):
        if tag.find_parent(_is_block):
            continue

        text = _text(tag)
        if tag.name == "tr" and (context := _row_context(tag)):
            text = f"{context} {text}"
        if text and (not blocks or text != blocks[-1]) and not is_menu(text):
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
    if PLACEHOLDER_PATTERN.search(normalized) and len(normalized) < 500:
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
                server = response.server_addr() if response is not None else None
                _check_connected_address(server.get("ipAddress") if isinstance(server, dict) else None)
                if response is not None and not response.ok:
                    error_class = (
                        SourceUnavailableError if response.status >= 500 else ScraperError
                    )
                    raise error_class(
                        f"The rendered page returned HTTP {response.status}."
                    )

                page.wait_for_timeout(RENDER_WAIT_MS)
                final_url = validate_url(page.url)
                html = page.content()
                if not html.strip():
                    raise ScraperError("The rendered page returned empty HTML.")
                if len(html.encode()) > MAX_RESPONSE_BYTES:
                    raise ScraperError("The source page is too large.")

                return final_url, html
            finally:
                browser.close()
    except ScraperError:
        raise
    except PlaywrightTimeoutError as error:
        raise SourceUnavailableError("The rendered page timed out.") from error
    except PlaywrightError as error:
        raise SourceUnavailableError("The rendered page could not be loaded.") from error


def _result(final_url: str, source_text: str) -> ScrapeResult:
    require_official(final_url)
    if len(source_text) > MAX_SOURCE_TEXT_LENGTH:
        raise ScraperError("The source page has too much text to process.")
    return ScrapeResult(source_url=normalize_url(final_url), source_text=source_text)


def scrape_url(url: str) -> ScrapeResult:
    require_official(url)
    try:
        final_url, html = fetch_static_html(url)  # both fetchers validate the URL
    except SourceUnavailableError:
        # Some official servers send an incomplete certificate chain: a browser completes and still verifies it.
        html = ""

    try:
        source_text = clean_html(html)
    except ScraperError:
        source_text = ""

    if is_source_text_usable(source_text):
        return _result(final_url, source_text)

    final_url, html = fetch_rendered_html(url)
    source_text = clean_html(html)
    if not is_source_text_usable(source_text):
        raise ScraperError("No meaningful page content found.")

    return _result(final_url, source_text)
