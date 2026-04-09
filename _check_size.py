import httpx
r = httpx.get("http://127.0.0.1:8000/api/files", timeout=30)
d = r.json()
total = sum(f["size"] for f in d["files"])
print(f"SharePoint folder: {total/1024/1024:.1f} MB across {d['total']} files")
