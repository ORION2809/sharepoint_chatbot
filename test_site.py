"""Test site/bluevoir access and list files in LegalGenie/MVP Implementation."""
from sharepoint_client import SharePointClient

sp = SharePointClient()

# 1. Resolve site
print("--- Resolving site ---")
try:
    site_id = sp.get_site_id()
    print("Site ID:", site_id)
except Exception as e:
    print("ERROR:", e)
    exit(1)

# 2. List drives
print("\n--- Drives ---")
drives = sp.list_drives()
for d in drives:
    print(f"  Drive: {d.get('name', '?')}  (id={d['id'][:30]}...)")

# 3. Find "Shared Documents" / "Documents" drive
target_drive = None
for d in drives:
    if d.get("name", "").lower() in ("documents", "shared documents"):
        target_drive = d
        break
if not target_drive and drives:
    target_drive = drives[0]

if not target_drive:
    print("No drives found!")
    exit(1)

drive_id = target_drive["id"]
print(f"\nUsing drive: {target_drive.get('name', '?')}")

# 4. List root
print("\n--- Root items ---")
root_items = sp.list_files(drive_id)
for item in root_items:
    kind = "folder" if "folder" in item else "file"
    print(f"  [{kind}] {item.get('name', '?')}")

# 5. Try LegalGenie folder
print("\n--- LegalGenie folder ---")
try:
    lg_items = sp.list_files(drive_id, "LegalGenie")
    for item in lg_items:
        kind = "folder" if "folder" in item else "file"
        print(f"  [{kind}] {item.get('name', '?')}")
except Exception as e:
    print(f"  Error: {e}")

# 6. Try LegalGenie/MVP Implementation
print("\n--- LegalGenie/MVP Implementation ---")
try:
    mvp_items = sp.list_files(drive_id, "LegalGenie/MVP Implementation")
    for item in mvp_items:
        kind = "folder" if "folder" in item else "file"
        size = item.get("size", "?")
        print(f"  [{kind}] {item.get('name', '?')}  ({size} bytes)")
except Exception as e:
    print(f"  Error: {e}")

# 7. Recursive listing
print("\n--- All files (recursive, depth=3) ---")
try:
    all_files = sp.list_all_files_recursive(drive_id, "LegalGenie/MVP Implementation", depth=3)
    print(f"Total files: {len(all_files)}")
    for f in all_files:
        print(f"  - {f.get('name', '?')}  ({f.get('size', '?')} bytes)")
except Exception as e:
    print(f"  Error: {e}")
