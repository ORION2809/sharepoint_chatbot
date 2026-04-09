"""Diagnostic script to find the correct SharePoint site."""
import msal
import httpx
import json
import config

app = msal.ConfidentialClientApplication(
    client_id=config.AZURE_CLIENT_ID,
    client_credential=config.AZURE_CLIENT_SECRET,
    authority=f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}",
)
result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
token = result["access_token"]
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

urls = [
    "https://graph.microsoft.com/v1.0/sites/bluevoirus.sharepoint.com:/",
    "https://graph.microsoft.com/v1.0/sites?search=*",
    "https://graph.microsoft.com/v1.0/sites/root",
]

for url in urls:
    print(f"\n--- {url} ---")
    r = httpx.get(url, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        if "value" in data:
            for s in data["value"][:5]:
                name = s.get("displayName", "?")
                web = s.get("webUrl", "?")
                sid = s.get("id", "?")
                print(f"  Site: {name} | {web} | id={sid}")
        else:
            print(f"  id={data.get('id', '?')}")
            print(f"  displayName={data.get('displayName', '?')}")
            print(f"  webUrl={data.get('webUrl', '?')}")
    else:
        print(f"  Error: {r.text[:500]}")
