"""Check actual permission assignments on the service principal."""
import httpx
import config

# Get token (we know this works for some SP queries)
token_url = f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/oauth2/v2.0/token"
data = {
    "client_id": config.AZURE_CLIENT_ID,
    "client_secret": config.AZURE_CLIENT_SECRET,
    "scope": "https://graph.microsoft.com/.default",
    "grant_type": "client_credentials",
}
r = httpx.post(token_url, data=data, timeout=15)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

SP_ID = "8bf6164a-804b-4856-aebf-42f013b70973"

# Check app role assignments (actual consented permissions)
print("--- App Role Assignments (actual admin-consented perms) ---")
r1 = httpx.get(
    f"https://graph.microsoft.com/v1.0/servicePrincipals/{SP_ID}/appRoleAssignments",
    headers=headers,
    timeout=15,
)
print(f"Status: {r1.status_code}")
if r1.status_code == 200:
    assignments = r1.json().get("value", [])
    if not assignments:
        print("  NO app role assignments found!")
        print("  This means admin consent was NOT actually granted.")
    for a in assignments:
        print(f"  Resource: {a.get('resourceDisplayName', '?')}")
        print(f"  Role ID: {a.get('appRoleId', '?')}")
        print()
else:
    print("  Error:", r1.text[:300])

# Check oauth2PermissionGrants (delegated permissions)
print("--- OAuth2 Delegated Permission Grants ---")
r2 = httpx.get(
    f"https://graph.microsoft.com/v1.0/servicePrincipals/{SP_ID}/oauth2PermissionGrants",
    headers=headers,
    timeout=15,
)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    grants = r2.json().get("value", [])
    if not grants:
        print("  No delegated permission grants found.")
    for g in grants:
        print(f"  Scope: {g.get('scope', '?')}")
        print(f"  Resource: {g.get('resourceId', '?')}")
        print(f"  ConsentType: {g.get('consentType', '?')}")
        print()
else:
    print("  Error:", r2.text[:300])

# List permissions defined on app registration
print("--- App Registration Required Resource Access ---")
r3 = httpx.get(
    f"https://graph.microsoft.com/v1.0/applications?$filter=appId eq '{config.AZURE_CLIENT_ID}'&$select=requiredResourceAccess,displayName",
    headers=headers,
    timeout=15,
)
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    apps = r3.json().get("value", [])
    if apps:
        rra = apps[0].get("requiredResourceAccess", [])
        for resource in rra:
            res_id = resource.get("resourceAppId", "?")
            access = resource.get("resourceAccess", [])
            print(f"  Resource App: {res_id}")
            for a in access:
                ptype = "Application" if a.get("type") == "Role" else "Delegated"
                print(f"    - {a.get('id', '?')} ({ptype})")
else:
    print("  Error:", r3.text[:300])
