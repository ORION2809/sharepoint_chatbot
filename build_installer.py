"""
Build Installer — Package the SharePoint Chatbot for distribution.

Creates a distributable ZIP or folder that IT admins can pre-configure
with company credentials before distributing to employees.

Modes:
  --zip         Create a .zip file (default)
  --folder      Create a distributable folder only
  --prefill     Pre-fill .env with company credentials interactively
  --output DIR  Output directory (default: ./dist/)

Usage:
  python build_installer.py --zip
  python build_installer.py --zip --prefill
  python build_installer.py --folder --output C:\\Releases
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DEFAULT_OUTPUT = BASE_DIR / "dist"

# Files/dirs to EXCLUDE from the distribution
EXCLUDE_PATTERNS = {
    ".env",
    ".token_cache.json",
    "__pycache__",
    "venv",
    ".venv",
    ".chroma_db",
    ".index_meta.json",
    "dist",
    "build",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
    # Test/debug files — exclude from distribution
    "_check_size.py",
    "_e2e_test.py",
    "_reindex.py",
    "_test_full.py",
    "_test_vision.py",
    "check_permissions.py",
    "test_auth.py",
    "test_connect.py",
    "test_deep_auth.py",
    "test_permissions_detail.py",
    "test_queries.py",
    "test_sharepoint.py",
    "test_site.py",
    "build_installer.py",
}

# Core files to INCLUDE (explicit list for safety)
INCLUDE_FILES = [
    "main.py",
    "sharepoint_client.py",
    "vector_store.py",
    "llm_client.py",
    "vision_client.py",
    "chunker.py",
    "config.py",
    "login.py",
    "setup_wizard.py",
    "requirements.txt",
    "install.bat",
    "start.bat",
    "uninstall.bat",
    ".env.example",
    ".gitignore",
    "README.md",
    "IMPLEMENTATION_SUMMARY.md",
    "PACKAGING_GUIDE.md",
    "installer.iss",
]

INCLUDE_DIRS = [
    "templates",
]


def _should_exclude(name: str) -> bool:
    """Check if a file or directory name should be excluded."""
    if name in EXCLUDE_PATTERNS:
        return True
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*") and name.endswith(pattern[1:]):
            return True
    return False


def _prompt_credentials() -> dict[str, str]:
    """Interactively gather company-wide credentials for pre-filling."""
    print()
    print("=" * 60)
    print("  PRE-FILL COMPANY CONFIGURATION")
    print("=" * 60)
    print()
    print("  Enter the company-wide values to embed in the installer.")
    print("  Employees won't need to enter these — only sign in.")
    print()

    fields = [
        ("AZURE_CLIENT_ID", "Azure AD Client ID"),
        ("AZURE_CLIENT_SECRET", "Azure AD Client Secret"),
        ("AZURE_TENANT_ID", "Azure AD Tenant ID"),
        ("SHAREPOINT_HOSTNAME", "SharePoint Hostname (e.g. company.sharepoint.com)"),
        ("SHAREPOINT_SITE_PATH", "Site Path (e.g. sites/yoursite, or blank)"),
        ("NVIDIA_API_KEY", "NVIDIA API Key"),
    ]

    values: dict[str, str] = {}
    for key, label in fields:
        value = input(f"  {label}: ").strip()
        if value:
            values[key] = value

    return values


def _write_prefilled_env(target_dir: Path, credentials: dict[str, str]) -> None:
    """Write a pre-filled .env file into the distribution."""
    lines = [
        "# SharePoint Chatbot Configuration",
        "# Pre-configured by IT admin",
        "",
        "# -- Azure AD / SharePoint ------------------------------------------",
        f"AZURE_CLIENT_ID={credentials.get('AZURE_CLIENT_ID', 'your-app-client-id')}",
        f"AZURE_CLIENT_SECRET={credentials.get('AZURE_CLIENT_SECRET', 'your-app-client-secret')}",
        f"AZURE_TENANT_ID={credentials.get('AZURE_TENANT_ID', 'your-tenant-id')}",
        "",
        f"SHAREPOINT_HOSTNAME={credentials.get('SHAREPOINT_HOSTNAME', 'yourcompany.sharepoint.com')}",
        f"SHAREPOINT_SITE_PATH={credentials.get('SHAREPOINT_SITE_PATH', '')}",
        "SHAREPOINT_FOLDER=",
        "",
        "# -- NVIDIA API -----------------------------------------------------",
        f"NVIDIA_API_KEY={credentials.get('NVIDIA_API_KEY', 'your-nvidia-api-key')}",
        "NVIDIA_MODEL=meta/llama-3.3-70b-instruct",
        "NVIDIA_VISION_MODEL=microsoft/phi-3.5-vision-instruct",
        "",
        "# -- RAG tuning (optional) ------------------------------------------",
        "TOP_K_CHUNKS=5",
        "MAX_FILE_SIZE_MB=10",
    ]
    (target_dir / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(
    output_dir: Path,
    create_zip: bool = True,
    credentials: dict[str, str] | None = None,
) -> Path:
    """Build the distributable package."""
    timestamp = datetime.now().strftime("%Y%m%d")
    pkg_name = f"SharePointChatbot_{timestamp}"
    staging_dir = output_dir / pkg_name

    print(f"\n  Building package: {pkg_name}")
    print(f"  Output: {output_dir}")
    print()

    # Clean staging
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Copy core files
    copied = 0
    for filename in INCLUDE_FILES:
        src = BASE_DIR / filename
        if src.exists():
            shutil.copy2(src, staging_dir / filename)
            copied += 1
            print(f"  + {filename}")
        else:
            print(f"  - {filename} (not found, skipping)")

    # Copy directories
    for dirname in INCLUDE_DIRS:
        src = BASE_DIR / dirname
        if src.is_dir():
            shutil.copytree(src, staging_dir / dirname)
            print(f"  + {dirname}/")

    # Pre-fill .env if credentials provided
    if credentials:
        _write_prefilled_env(staging_dir, credentials)
        print("  + .env (pre-filled with company config)")
    else:
        # Copy .env.example as-is
        example = BASE_DIR / ".env.example"
        if example.exists():
            shutil.copy2(example, staging_dir / ".env.example")

    print(f"\n  {copied} files copied to staging directory.")

    if create_zip:
        zip_path = output_dir / f"{pkg_name}.zip"
        print(f"\n  Creating ZIP: {zip_path}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(staging_dir):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not _should_exclude(d)]
                for file in files:
                    if _should_exclude(file):
                        continue
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(output_dir)
                    zf.write(file_path, arcname)

        # Clean up staging dir after zipping
        shutil.rmtree(staging_dir)
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"  Package created: {zip_path} ({size_mb:.1f} MB)")
        return zip_path
    else:
        print(f"  Package folder: {staging_dir}")
        return staging_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SharePoint Chatbot installer package")
    parser.add_argument("--zip", action="store_true", default=True, help="Create ZIP archive (default)")
    parser.add_argument("--folder", action="store_true", help="Create folder only (no ZIP)")
    parser.add_argument("--prefill", action="store_true", help="Pre-fill .env with company credentials")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    credentials = None
    if args.prefill:
        credentials = _prompt_credentials()

    create_zip = not args.folder

    result = build(output_dir, create_zip=create_zip, credentials=credentials)

    print()
    print("=" * 60)
    print("  BUILD COMPLETE")
    print("=" * 60)
    print()
    print(f"  Output: {result}")
    print()
    if credentials:
        print("  The package includes pre-filled company credentials.")
        print("  Employees only need to:")
        print("    1. Extract the ZIP")
        print("    2. Double-click install.bat")
        print("    3. Sign in with their Office 365 email")
        print("    4. Double-click start.bat")
    else:
        print("  Employees will need to:")
        print("    1. Extract the ZIP")
        print("    2. Fill in .env with credentials from IT")
        print("    3. Double-click install.bat")
        print("    4. Sign in with their Office 365 email")
        print("    5. Double-click start.bat")
    print()


if __name__ == "__main__":
    main()
