"""Initial auth and SharePoint connectivity test."""
from sharepoint_client import SharePointClient

sp = SharePointClient()
print("Initiating auth...")
token = sp._get_token()
print("Token acquired! Length:", len(token))
print()

# Test site access
try:
    site_id = sp.get_site_id()
    print("Site ID:", site_id)
except Exception as e:
    print("Site error:", e)
    exit(1)

# Test drive listing
try:
    drives = sp.list_drives()
    print("Drives found:", len(drives))
    for d in drives:
        print("  -", d.get("name", "?"))
except Exception as e:
    print("Drive error:", e)
    exit(1)

# Test file listing
if drives:
    try:
        files = sp.list_all_files_recursive(drives[0]["id"], depth=2)
        print(f"\nFiles in '{drives[0].get('name', '?')}':")
        for f in files[:10]:
            print("  -", f.get("name", "?"))
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
    except Exception as e:
        print("File listing error:", e)

print("\n=== SharePoint connection is WORKING! ===")
