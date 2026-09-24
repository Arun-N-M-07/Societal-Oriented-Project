import httpx
from bs4 import BeautifulSoup


def scrape(url: str) -> str:
    r = httpx.get(url, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    return " ".join(soup.stripped_strings)