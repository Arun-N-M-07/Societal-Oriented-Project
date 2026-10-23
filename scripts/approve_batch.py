"""Approve a reviewed batch of official pages through the admin API.

Logs in as the admin (password typed at the prompt, never stored), then for
each page: extracts it with the normal admin endpoint, applies the reviewed
name/department/jurisdiction, shows the draft and saves it only if you answer
"y". Pages already saved are skipped. Provenance checks, chunking and
embedding happen in the normal save endpoint.

    .venv/bin/python scripts/approve_batch.py fixtures/ingestion/demo_batch.json
"""

import getpass
import json
import sys

import httpx

FIELDS = ("name", "department", "jurisdiction")


def approve(client, entries, confirm):
    saved_urls = {p["source_url"] for p in client.get("/api/admin/procedures").raise_for_status().json()}
    results = []
    for entry in entries:
        extracted = client.post("/api/admin/extract", json={"source_url": entry["url"]}, timeout=180)
        if extracted.status_code != 200:
            results.append((entry["url"], f"extract failed: {extracted.json().get('detail')}"))
            continue
        body = extracted.json()
        draft = {**body["procedure"], **{f: entry[f] for f in FIELDS if f in entry}}
        if draft["source_url"] in saved_urls:
            results.append((entry["url"], "already saved"))
            continue
        print(f"\n{draft['name']} | {draft['department']} | {draft['source_url']}\n  {draft['summary']}")
        print(f"  eligibility: {draft['eligibility']}")
        for number, step in enumerate(draft["steps"], 1):
            print(f"  {number}. {step}")
        if not confirm(draft):
            results.append((entry["url"], "skipped by reviewer"))
            continue
        saved = client.post("/api/admin/procedures", timeout=180, json={
            "procedure": draft, "source_text": body["source_text"], "provenance_token": body["provenance_token"],
        })
        results.append((entry["url"], f"saved as {saved.json()['id']}" if saved.status_code == 200
                        else f"save failed: {saved.json().get('detail')}"))
    return results


if __name__ == "__main__":
    entries = json.load(open(sys.argv[1]))["procedures"]
    with httpx.Client(base_url="http://localhost:8000") as client:
        login = client.post("/api/admin/login", json={
            "username": input("Admin username: "), "password": getpass.getpass("Admin password: "),
        })
        if login.status_code != 200:
            sys.exit("Login failed.")
        ask = lambda draft: input(f"Save '{draft['name']}'? [y/N] ").strip().lower() == "y"
        for url, outcome in approve(client, entries, ask):
            print(f"{outcome:30} {url}")
