"""End-to-end test: health, index stats, chat queries with source URLs."""
import httpx
import json
import time

BASE = "http://127.0.0.1:8000"

def test(name, fn):
    try:
        result = fn()
        print(f"PASS  {name}")
        return result
    except Exception as e:
        print(f"FAIL  {name}: {e}")
        return None

# ── 1. Health check ──
def t_health():
    r = httpx.get(f"{BASE}/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
test("Health check", t_health)

# ── 2. Index stats ──
def t_stats():
    r = httpx.get(f"{BASE}/api/index/stats")
    assert r.status_code == 200
    data = r.json()
    print(f"       → {data['indexed_files']} files, {data['total_chunks']} chunks")
    assert data["indexed_files"] > 0
    assert data["total_chunks"] > 0
    return data
test("Index stats", t_stats)

# ── 3. Chat queries ──
queries = [
    "What is the MVP Implementation about?",
    "What documents are available in SharePoint?",
    "Summarize the key points from the files.",
]

for q in queries:
    def t_chat(question=q):
        start = time.time()
        r = httpx.post(
            f"{BASE}/api/chat",
            json={"question": question},
            timeout=60,
        )
        elapsed = round(time.time() - start, 1)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        data = r.json()

        # Check answer exists
        assert data.get("answer"), "Empty answer"
        assert len(data["answer"]) > 20, "Answer too short"

        # Check sources are objects with name + url
        sources = data.get("sources", [])
        assert len(sources) > 0, "No sources returned"

        has_url = False
        for s in sources:
            assert "name" in s, f"Source missing 'name': {s}"
            assert "url" in s, f"Source missing 'url': {s}"
            if s["url"]:
                has_url = True
                print(f"       → Source: {s['name']}")
                print(f"         URL: {s['url'][:80]}...")

        print(f"       → {len(sources)} sources, URLs present: {has_url}, {elapsed}s")
        print(f"       → Answer preview: {data['answer'][:100]}...")
        return data

    test(f"Chat: {q[:50]}", t_chat)

# ── 4. Test with empty question (should fail gracefully) ──
def t_empty():
    r = httpx.post(f"{BASE}/api/chat", json={"question": ""})
    assert r.status_code == 400 or r.status_code == 422
test("Empty question rejected", t_empty)

# ── 5. Test file listing ──
def t_files():
    r = httpx.get(f"{BASE}/api/files?scope=folder")
    assert r.status_code == 200
    data = r.json()
    print(f"       → {data['total']} files in folder")
    for f in data["files"][:5]:
        print(f"         {f['name']} ({f['size']} bytes)")
    return data
test("File listing", t_files)

print("\n=== All tests complete ===")
