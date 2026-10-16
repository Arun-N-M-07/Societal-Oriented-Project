from backend.scraper import scrape_url, ScraperError


TEST_URLS = [
    "https://www.india.gov.in/",
    "https://www.tn.gov.in/",
]


def test_url(url: str) -> bool:
    print("\n" + "=" * 70)
    print("TESTING:", url)
    print("=" * 70)

    try:
        result = scrape_url(url)

        print("\nSCRAPER TEST PASSED")
        print("-" * 70)
        print("SOURCE URL:")
        print(result["source_url"])

        print("\nSOURCE TEXT:")
        print("-" * 70)
        print(result["source_text"][:3000])

        print("\nTEXT LENGTH:", len(result["source_text"]))

        return True

    except ScraperError as exc:
        print("\nSCRAPER ERROR:")
        print(exc)
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("PROCEDUREASSIST AI - MEMBER 2 SCRAPER TEST")
    print("=" * 70)

    passed = False

    for url in TEST_URLS:
        if test_url(url):
            passed = True
            break

    if passed:
        print("\n" + "=" * 70)
        print("FINAL RESULT: SCRAPER TEST PASSED")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("FINAL RESULT: ALL TEST URLS FAILED")
        print("=" * 70)