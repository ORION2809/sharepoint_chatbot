"""Deep auth diagnostic for SharePoint."""
import httpx
import base64
import json
import config

print("=" * 60)
print("Deep Auth Diagnostic")
print("=" * 60)

# Test 1: v1 endpoint with SharePoint resource
print("\n--- Test 1: v1 OAuth with SharePoint resource ---")
token_url_v1 = f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/oauth2/token"
data_v1 = {
    "client_id": config.AZURE_CLIENT_ID,
    "client_secret": config.AZURE_CLIENT_SECRET,
    "resource": f"https://{config.SHAREPOINT_HOSTNAME}",
    "grant_type": "client_credentials",
}
r1 = httpx.post(token_url_v1, data=data_v1, timeout=15)
print(f"Status: {r1.status_code}")
if r1.status_code == 200:
    t1 = r1.json()["access_token"]
    parts = t1.split(".")
    payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
    decoded = json.loads(base64.b64decode(payload))
    print("Roles:", decoded.get("roles", []))
    print("Aud:", decoded.get("aud", "?"))
    
    # Try SharePoint API with this token
    headers = {
        "Authorization": f"Bearer {t1}",
        "Accept": "application/json;odata=verbose",
    }
    r1b = httpx.get(f"https://{config.SHAREPOINT_HOSTNAME}/_api/web", headers=headers, timeout=15)
    print(f"/_api/web: {r1b.status_code}")
    if r1b.status_code == 200:
        d = r1b.json().get("d", r1b.json())
        print("Site Title:", d.get("Title", "?"))
    else:
        print("Body:", r1b.text[:300])
else:
    err = r1.json()
    print("Error:", err.get("error_description", err)[:300])

# Test 2: v1 endpoint with Graph resource
print("\n--- Test 2: v1 OAuth with Graph resource ---")
data_v1g = {
    "client_id": config.AZURE_CLIENT_ID,
    "client_secret": config.AZURE_CLIENT_SECRET,
    "resource": "https://graph.microsoft.com",
    "grant_type": "client_credentials",
}
r2 = httpx.post(token_url_v1, data=data_v1g, timeout=15)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    t2 = r2.json()["access_token"]
    parts = t2.split(".")
    payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
    decoded = json.loads(base64.b64decode(payload))
    print("Roles:", decoded.get("roles", []))

    headers2 = {"Authorization": f"Bearer {t2}", "Accept": "application/json"}
    r2b = httpx.get("https://graph.microsoft.com/v1.0/sites/root", headers=headers2, timeout=15)
    print(f"/sites/root: {r2b.status_code}")
    if r2b.status_code == 200:
        print("Site:", r2b.json().get("displayName", "?"))
    else:
        print("Body:", r2b.text[:300])

# Test 3: Try with Sites.Selected scope (sometimes required)
print("\n--- Test 3: Check enterprise app service principal ---")
# This might fail without admin permissions, but worth trying
if r2.status_code == 200:
    t2 = r2.json()["access_token"]
    headers3 = {"Authorization": f"Bearer {t2}", "Accept": "application/json"}
    r3 = httpx.get(
        f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{config.AZURE_CLIENT_ID}'",
        headers=headers3,
        timeout=15,
    )
    print(f"Service principal lookup: {r3.status_code}")
    if r3.status_code == 200:
        sps = r3.json().get("value", [])
        if sps:
            sp = sps[0]
            print("SP displayName:", sp.get("displayName", "?"))
            print("SP id:", sp.get("id", "?"))
        else:
            print("No service principal found")

# Print admin consent URL for the user
print("\n" + "=" * 60)
print("ADMIN CONSENT URL - Open this in browser and approve:")
print("=" * 60)
consent_url = (
    f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/adminconsent"
    f"?client_id={config.AZURE_CLIENT_ID}"
)
print(consent_url)
print()
print(
    "After approving, wait 2 minutes and run: python check_permissions.py"
)
