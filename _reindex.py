"""Clear old index and re-index the folder."""
import httpx
import time

BASE = "http://127.0.0.1:8000"

# 1. Clear old index
r = httpx.post(f"{BASE}/api/index/clear")
print("Clear:", r.json())

# 2. Start indexing folder
r = httpx.post(f"{BASE}/api/index?scope=folder")
print("Index start:", r.json())

# 3. Poll until done
while True:
    time.sleep(3)
    s = httpx.get(f"{BASE}/api/index/status").json()
    print(f"  {s['progress']}")
    if not s["running"]:
        print("Result:", s.get("last_result"))
        break
