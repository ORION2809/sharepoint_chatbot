"""Run this after granting Azure AD permissions to verify they work."""
import msal
import httpx
import base64
import json
import config

print("=" * 60)
print("SharePoint Chatbot - Permission Checker")
print("=" * 60)

# 1. Get token
app = msal.ConfidentialClientApplication(
    client_id=config.AZURE_CLIENT_ID,
    client_credential=config.AZURE_CLIENT_SECRET,
    authority=f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}",
)
result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

if "access_token" not in result:
    print("FAIL: Could not get token")
    print(result.get("error_description", result))
    exit(1)

token = result["access_token"]
print("[OK] Token acquired")

# 2. Check roles in token
parts = token.split(".")
payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
decoded = json.loads(base64.b64decode(payload))
roles = decoded.get("roles", [])
print(f"[INFO] App: {decoded.get('app_displayname', '?')}")
print(f"[INFO] Roles in token: {roles}")

needed = ["Sites.Read.All"]
for r in needed:
    if r in roles:
        print(f"  [OK] {r}")
    else:
        print(f"  [MISSING] {r} <-- You need to grant this!")

if not roles:
    print("\n*** No roles found. Go to Azure Portal and grant permissions. ***")
    print("See instructions below.\n")
    exit(1)

# 3. Test Graph API access
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

print("\n--- Testing SharePoint access ---")
r = httpx.get(
    f"https://graph.microsoft.com/v1.0/sites/{config.SHAREPOINT_HOSTNAME}:/",
    headers=headers,
    timeout=15,
)
print(f"Sites endpoint: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Site: {data.get('displayName', '?')}")
    site_id = data["id"]

    # List drives
    r2 = httpx.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives",
        headers=headers,
        timeout=15,
    )
    if r2.status_code == 200:
        drives = r2.json().get("value", [])
        print(f"  [OK] Found {len(drives)} drive(s)")
        for d in drives:
            print(f"    - {d.get('name', '?')} (id={d['id'][:20]}...)")
    else:
        print(f"  [WARN] Could not list drives: {r2.status_code}")

    print("\n=== ALL CHECKS PASSED! The chatbot should work. ===")
else:
    print(f"  [FAIL] {r.text[:300]}")
    print("\nPermissions may not have propagated yet. Wait 1-2 minutes and retry.")
