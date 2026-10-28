"""Operational checks against a running API instance (read-only: only public reads, identify and guidance).
    ops_tests.py <base url> normal     smoke, input validation, admin protection, concurrency
    ops_tests.py <base url> outage     what citizens get while the model server or the database is down
Prints one line per check and exits 1 if any check fails."""
import statistics, sys, time
from concurrent.futures import ThreadPoolExecutor
import httpx

BASE, MODE = sys.argv[1].rstrip("/"), sys.argv[2]
QUESTIONS = ["How do I renew my passport?", "How do I link PAN with Aadhaar?", "What is the fee for renewing a driving licence?",
             "I work in Saudi Arabia. How do I register to vote?", "How do I apply for a certificate in Tamil Nadu?",
             "How do I get a marriage certificate?", "how do i get an idp", "What is EDLI?",
             "How do I change my address in the electoral roll?", "How do I book a train ticket?"]
failures = []

def check(ok, what):
    print(f"{'ok  ' if ok else 'FAIL'} {what}", flush=True)
    if not ok:
        failures.append(what)

def identify(client, question):
    start = time.time()
    response = client.post(f"{BASE}/api/identify", json={"question": question})
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    return response.status_code, body, time.time() - start, response.headers.get("x-request-id")

with httpx.Client(timeout=300) as client:
    if MODE == "normal":
        check(client.get(f"{BASE}/health").status_code == 200, "GET /health 200")
        ready = client.get(f"{BASE}/health/ready")
        check(ready.status_code == 200 and ready.json().get("database") == "ok" and ready.json().get("ollama") == "ok",
              f"GET /health/ready {ready.status_code} {ready.json()}")
        listed = client.get(f"{BASE}/api/procedures")
        check(listed.status_code == 200, f"GET /api/procedures {listed.status_code}: {len(listed.json())} procedures")
        sequential = {}
        for q in QUESTIONS:
            status, body, took, request_id = identify(client, q)
            sequential[q] = (body.get("status"), [c["id"] for c in body.get("candidates", [])], bool(body.get("clarification")))
            check(status == 200 and bool(request_id), f"identify {q!r} -> {sequential[q]} in {took:.1f}s (request id {request_id})")
        reply = client.post(f"{BASE}/api/guidance", json={"procedure_id": sequential[QUESTIONS[0]][1][0], "question": QUESTIONS[0]})
        check(reply.status_code == 200, f"guidance on the passport page {reply.status_code}: "
              f"{'abstained' if reply.json().get('insufficient_evidence') else str(len(reply.json()['claims'])) + ' claims'}")
        for bad, why in (({"question": ""}, "empty question"), ({"question": "x" * 1001}, "question over 1000 characters"),
                         ({"text": "hi"}, "unknown field")):
            check(client.post(f"{BASE}/api/identify", json=bad).status_code == 422, f"identify rejects {why} with 422")
        check(client.post(f"{BASE}/api/admin/extract", json={"source_url": "https://www.india.gov.in"}).status_code == 401,
              "admin extract without a session -> 401")
        # 20 identify requests at once (each question twice), compared with the sequential answers.
        with ThreadPoolExecutor(20) as pool:
            start = time.time()
            results = list(pool.map(lambda q: (q, identify(client, q)), QUESTIONS * 2))
            wall = time.time() - start
        codes = [r[1][0] for r in results]
        same = sum((r[1][1].get("status"), [c["id"] for c in r[1][1].get("candidates", [])], bool(r[1][1].get("clarification")))
                   == sequential[r[0]] for r in results)
        took = [r[1][2] for r in results]
        check(codes.count(200) == 20, f"20 concurrent identify requests: {codes.count(200)} x 200, wall {wall:.1f}s, "
              f"latency median {statistics.median(took):.1f}s max {max(took):.1f}s")
        check(same == 20, f"concurrent answers equal the sequential ones: {same}/20")
        with ThreadPoolExecutor(3) as pool:
            start = time.time()
            replies = list(pool.map(lambda q: client.post(f"{BASE}/api/guidance", json={"procedure_id": sequential[QUESTIONS[0]][1][0],
                                                                                        "question": q}),
                                    ["Which documents do I need?", "How long does it take?", "What is the fee?"]))
        check(all(r.status_code == 200 for r in replies), f"3 concurrent guidance requests: {[r.status_code for r in replies]} "
              f"in {time.time() - start:.0f}s")
    else:
        ready = client.get(f"{BASE}/health/ready")
        check(ready.status_code == 503, f"GET /health/ready reports the outage: {ready.status_code} {ready.json()}")
        check(client.get(f"{BASE}/health").status_code == 200, "GET /health (liveness) still 200")
        status, body, took, request_id = identify(client, QUESTIONS[0])
        print(f"     identify while down -> {status} {body} in {took:.1f}s (request id {request_id})")
        check(status in (502, 503) and "detail" in body, f"identify fails cleanly with {status} and a message, not a crash")
        reply = client.post(f"{BASE}/api/guidance", json={"procedure_id": 15, "question": QUESTIONS[0]})
        print(f"     guidance while down -> {reply.status_code} {reply.text[:160]}")
        check(reply.status_code in (502, 503, 404) or reply.status_code >= 500, f"guidance fails with {reply.status_code}")
print(f"\n{len(failures)} failed check(s)")
sys.exit(1 if failures else 0)
