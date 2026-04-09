"""Quick script to poll indexing status until done."""
import httpx, json, time

# Trigger indexing
r = httpx.post("http://127.0.0.1:8000/api/index?scope=folder", timeout=10)
print("Trigger:", r.status_code, r.json())

for _ in range(90):
    time.sleep(4)
    try:
        r = httpx.get("http://127.0.0.1:8000/api/index/status", timeout=30)
        s = r.json()
        running = s.get("running", False)
        progress = s.get("progress", "")
        print(f"  running={running}  progress={progress}")
        if not running:
            result = s.get("last_result")
            if result:
                print()
                print("RESULT:")
                print(json.dumps(result, indent=2))
            break
    except Exception as e:
        print(f"  poll error: {e}")
