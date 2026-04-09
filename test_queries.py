"""Run test queries against the chunk-based chat endpoint."""
import httpx
import json
import time

QUERIES = [
    "What modules does LegalGenie have?",
    "What is the RAG pipeline architecture used in LegalGenie?",
    "What is the Kaladevi judgment about?",
    "What are the API contracts for the research tab in LegalGenie?",
    "What database does LegalGenie use for vector storage?",
]

for i, q in enumerate(QUERIES, 1):
    print(f"\n{'='*60}")
    print(f"Query {i}: {q}")
    print("="*60)
    start = time.time()
    r = httpx.post(
        "http://127.0.0.1:8000/api/chat",
        json={"question": q},
        timeout=120,
    )
    elapsed = round(time.time() - start, 1)
    print(f"Status: {r.status_code}  Time: {elapsed}s")
    data = r.json()
    print(f"Sources: {data.get('sources')}")
    print(f"\n{data.get('answer')}")
