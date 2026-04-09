"""Test SharePoint REST API with SharePoint-specific token."""
import httpx
import base64
import json
import config

# Get SharePoint-specific token
token_url = f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/oauth2/v2.0/token"
data = {
    "client_id": config.AZURE_CLIENT_ID,
    "client_secret": config.AZURE_CLIENT_SECRET,
    "scope": f"https://{config.SHAREPOINT_HOSTNAME}/.default",
    "grant_type": "client_credentials",
}
r = httpx.post(token_url, data=data, timeout=15)
result = r.json()
token = result["access_token"]

# Decode token
parts = token.split(".")
payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
decoded = json.loads(base64.b64decode(payload))
print("Audience:", decoded.get("aud", "?"))
print("Roles:", decoded.get("roles", []))

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json;odata=verbose",
}

# Test 1: Site info
print("\n--- /_api/web ---")
r2 = httpx.get(
    f"https://{config.SHAREPOINT_HOSTNAME}/_api/web",
    headers=headers,
    timeout=15,
)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    d = r2.json().get("d", r2.json())
    print("Title:", d.get("Title", "?"))
    print("Url:", d.get("Url", "?"))
else:
    print("Error:", r2.text[:500])

# Test 2: Document libraries
print("\n--- Document Libraries ---")
r3 = httpx.get(
    f"https://{config.SHAREPOINT_HOSTNAME}/_api/web/lists?$filter=BaseTemplate eq 101",
    headers=headers,
    timeout=15,
)
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    items = r3.json().get("d", {}).get("results", [])
    for lib in items[:10]:
        print(f"  - {lib.get('Title', '?')} (ItemCount: {lib.get('ItemCount', '?')})")
else:
    print("Error:", r3.text[:500])

# Test 3: Files in default library
print("\n--- Files in Shared Documents ---")
r4 = httpx.get(
    f"https://{config.SHAREPOINT_HOSTNAME}/_api/web/GetFolderByServerRelativeUrl('Shared Documents')/Files",
    headers=headers,
    timeout=15,
)
print(f"Status: {r4.status_code}")
if r4.status_code == 200:
    files = r4.json().get("d", {}).get("results", [])
    for f in files[:10]:
        print(f"  - {f.get('Name', '?')} ({f.get('Length', '?')} bytes)")
else:
    print("Error:", r4.text[:500])
