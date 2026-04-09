"""Clear index and re-index, then run chat tests including image/video queries."""
import httpx
import time
import json

BASE = "http://127.0.0.1:8000"

print("=== 1. Clear old index ===")
r = httpx.post(f"{BASE}/api/index/clear")
print(r.json())

print("\n=== 2. Re-index folder ===")
r = httpx.post(f"{BASE}/api/index?scope=folder")
print(r.json())

while True:
    time.sleep(4)
    s = httpx.get(f"{BASE}/api/index/status").json()
    print(f"  {s['progress']}")
    if not s["running"]:
        print("  Result:", json.dumps(s.get("last_result"), indent=2))
        break

print("\n=== 3. Index stats ===")
r = httpx.get(f"{BASE}/api/index/stats")
stats = r.json()
print(f"  Files: {stats['indexed_files']}, Chunks: {stats['total_chunks']}")
for fid, info in stats.get("files", {}).items():
    print(f"    {info['filename']} ({info['chunks']} chunks)")

print("\n=== 4. Chat tests ===")
queries = [
    "What is shown in the architecture diagram?",
    "What is the MVP Implementation about?",
    "Describe any images or diagrams in the SharePoint files.",
    "List all the files available and summarize their content.",
]

for q in queries:
    print(f"\n  Q: {q}")
    start = time.time()
    try:
        r = httpx.post(
            f"{BASE}/api/chat",
            json={"question": q},
            timeout=90,
        )
        elapsed = round(time.time() - start, 1)
        if r.status_code == 200:
            data = r.json()
            print(f"  A: {data['answer'][:200]}...")
            for s in data.get("sources", []):
                url_preview = s.get("url", "")[:70]
                print(f"     Source: {s['name']} → {url_preview}...")
            print(f"  ({elapsed}s, {len(data.get('sources', []))} sources)")
        else:
            print(f"  ERROR {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n=== Done ===")
