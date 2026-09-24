import ipaddress
from urllib.parse import urljoin, urlparse

import httpx


HTTP_TIMEOUT = 20.0
MAX_REDIRECTS = 10
USER_AGENT = "ProcedureAssistAI/1.0"
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}


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
