# SharePoint Chatbot — Packaging & Distribution Guide

## Overview

This document describes how to package and distribute the SharePoint Chatbot as an installer for company employees. Three distribution methods are available, from simplest to most polished.

---

## Distribution Methods

| Method | Complexity | Best For |
|--------|-----------|----------|
| **ZIP + Setup Wizard** | Low | Small teams, quick internal sharing |
| **Pre-filled ZIP** | Low | IT-managed distribution (credentials baked in) |
| **Inno Setup EXE** | Medium | Professional distribution, large organizations |

---

## Method 1: ZIP + Setup Wizard (Recommended)

The simplest approach. Build a ZIP file, share it, employees extract and run.

### IT Admin: Build the Package

```bash
# Basic ZIP (employees enter credentials via setup wizard)
python build_installer.py --zip

# Pre-fill with company credentials (employees only need to sign in)
python build_installer.py --zip --prefill
```

The `--prefill` flag prompts for company-wide values:
- Azure AD Client ID, Secret, Tenant ID
- SharePoint Hostname
- NVIDIA API Key

These are baked into the ZIP's `.env` so employees never see them.

### Output

```
dist/
  SharePointChatbot_YYYYMMDD.zip    # Distributable package
```

### Employee Experience

**With pre-filled credentials:**
1. Extract the ZIP
2. Double-click `install.bat`
3. Setup Wizard opens → installs dependencies → opens browser for Office 365 sign-in
4. Sign in with their work email
5. Double-click `start.bat` to launch

**Without pre-filled credentials:**
1. Extract the ZIP
2. Double-click `install.bat`
3. Setup Wizard opens → enters credentials from IT → signs in
4. Double-click `start.bat` to launch

---

## Method 2: Inno Setup EXE Installer

Creates a professional Windows installer (`SharePointChatbot_Setup_1.0.0.exe`) with:
- Install location chooser
- Start Menu and Desktop shortcuts
- Automatic Python detection
- Built-in uninstaller (Add/Remove Programs)
- Post-install setup wizard launch

### Prerequisites

1. Install [Inno Setup 6+](https://jrsoftware.org/isinfo.php) on the build machine
2. (Optional) Pre-fill `.env` with company credentials

### Build Steps

```bash
# 1. (Optional) Pre-fill .env with company credentials
python build_installer.py --prefill --folder

# 2. Open installer.iss in Inno Setup Compiler
#    OR compile from command line:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### Output

```
dist/
  SharePointChatbot_Setup_1.0.0.exe   # Windows installer
```

### Employee Experience

1. Double-click `SharePointChatbot_Setup_1.0.0.exe`
2. Follow the install wizard (choose location, shortcuts)
3. Setup Wizard auto-launches → installs dependencies → browser sign-in
4. Click "SharePoint Chatbot" from Desktop or Start Menu

### Customizing the Inno Setup Script

Edit `installer.iss` to change:
- `MyAppName` — Application display name
- `MyAppVersion` — Version number
- `MyAppPublisher` — Company name
- `DefaultDirName` — Default install path
- `AppId` — Unique GUID (generate a new one for your company)

---

## Method 3: Headless / CLI Install

For scripted deployments or users comfortable with the command line:

```bash
install.bat --headless
```

This skips the GUI wizard and runs the traditional CLI install flow.

---

## Architecture

### Files Created for Packaging

| File | Purpose |
|------|---------|
| `setup_wizard.py` | Tkinter GUI wizard — deps install, config, OAuth login, desktop shortcut |
| `build_installer.py` | Build script — creates distributable ZIP or folder with optional credential pre-fill |
| `installer.iss` | Inno Setup script — generates professional Windows .exe installer |
| `install.bat` | Enhanced — launches GUI wizard by default, falls back to CLI with `--headless` |
| `start.bat` | Enhanced — auto-prompts login if not signed in, better error messages |
| `uninstall.bat` | Clean removal — venv, cache, tokens, config, shortcuts |

### Setup Wizard Flow

```
┌─────────────────────────────────────────────────┐
│  Step 1: Welcome                                │
│  Shows status checks (Python, venv, .env, auth) │
│  [Start Setup →]                                │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│  Step 2: Install Dependencies                   │
│  Creates venv, pip install requirements.txt     │
│  Shows progress log in real-time                │
│  [Next → Configure]                             │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│  Step 3: Configuration                          │
│  Pre-filled fields if IT baked in credentials   │
│  Employee fills in remaining fields if needed   │
│  [Save & Sign In →]                             │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│  Step 4: Sign In                                │
│  Opens browser for Office 365 OAuth login       │
│  Runs login.py, captures output, shows status   │
│  [Next → Finish]                                │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│  Step 5: Complete                               │
│  Summary of what to do next                     │
│  [✓] Create desktop shortcut                    │
│  [Launch Chatbot Now]   [Close]                 │
└─────────────────────────────────────────────────┘
```

### Build Script Flow

```
python build_installer.py
    │
    ├── --prefill?  →  Prompt for company credentials
    │
    ├── Copy core files to staging dir (dist/SharePointChatbot_YYYYMMDD/)
    │   ├── main.py, sharepoint_client.py, vector_store.py, ...
    │   ├── setup_wizard.py, install.bat, start.bat, uninstall.bat
    │   ├── requirements.txt, templates/
    │   └── .env (pre-filled) or .env.example
    │
    ├── Exclude: tests, venv, .chroma_db, __pycache__, .git
    │
    └── --zip?  →  Compress to .zip  →  Remove staging dir
```

---

## What Gets Distributed

### Included in Package

```
SharePointChatbot/
├── main.py                     # FastAPI app
├── sharepoint_client.py        # SharePoint Graph API client
├── vector_store.py             # ChromaDB vector store
├── llm_client.py               # NVIDIA LLM client
├── vision_client.py            # NVIDIA Vision client
├── chunker.py                  # Text chunker
├── config.py                   # Config loader
├── login.py                    # OAuth login script
├── setup_wizard.py             # GUI setup wizard
├── requirements.txt            # Python dependencies
├── install.bat                 # One-click installer (launches wizard)
├── start.bat                   # One-click launcher
├── uninstall.bat               # Clean uninstaller
├── .env                        # Pre-filled config (if --prefill used)
├── .env.example                # Config template (if no --prefill)
├── README.md                   # User documentation
├── IMPLEMENTATION_SUMMARY.md   # Technical details
├── PACKAGING_GUIDE.md          # This document
├── installer.iss               # Inno Setup script (for EXE builds)
└── templates/
    └── index.html              # Chat UI
```

### Excluded from Package

- `venv/` — Created on each machine during install
- `.chroma_db/` — Created during first index
- `.token_cache.json` — Created per-user during sign-in
- `.index_meta.json` — Created during first index
- `__pycache__/` — Python bytecode cache
- `test_*.py`, `_test_*.py` — Test scripts
- `build_installer.py` — Only needed on the build machine
- `.git/` — Version control

---

## Security Considerations

### Credential Handling

| Credential | Scope | Distribution |
|-----------|-------|-------------|
| Azure Client ID | Company-wide | Safe to embed in package |
| Azure Client Secret | Company-wide | Embed in `.env` only if distributed via secure channel |
| Azure Tenant ID | Company-wide | Safe to embed |
| NVIDIA API Key | Company-wide | Embed only if org allows; otherwise employees enter via wizard |
| OAuth Token | Per-user | Never distributed — generated during sign-in |

### Recommendations

1. **Secure distribution channel** — Share the ZIP/EXE via SharePoint, internal file share, or Intune. Never email the installer with embedded secrets.
2. **Rotate secrets** — If a client secret is compromised, rotate it in Azure AD and redistribute the package.
3. **Per-user tokens** — Each employee signs in with their own Office 365 account. The app acts on behalf of the signed-in user, so permissions are scoped to what that user can access.
4. **No admin rights needed** — The Inno Setup installer supports per-user install (no UAC prompt).

---

## Versioning & Updates

### Updating the Application

1. Make code changes
2. Update version in `installer.iss` (`MyAppVersion`)
3. Rebuild: `python build_installer.py --zip --prefill`
4. Distribute the new ZIP/EXE

### Employee Update Process

Employees can update by:
1. Extracting the new ZIP over the existing folder (overwrite files)
2. Running `install.bat` again (installs any new dependencies)
3. Their `.token_cache.json` and `.chroma_db/` are preserved

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Python is not installed" | Install Python 3.10+ from python.org, check "Add to PATH" |
| Setup wizard won't open | Run `python setup_wizard.py` from command line to see errors |
| Sign-in fails | Check Azure AD app registration has `http://localhost:8400` as redirect URI |
| "Missing required env var" | Re-run `install.bat` or manually edit `.env` |
| Port 8000 already in use | Another app is using port 8000. Close it or change the port in `start.bat` |
| ChromaDB errors | Delete `.chroma_db/` folder and re-index |

---

## Quick Reference

### For IT Admins

```bash
# Build pre-configured package for employees
python build_installer.py --zip --prefill

# Build Inno Setup EXE (requires Inno Setup 6 installed)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### For Employees

```
1. Extract SharePointChatbot_YYYYMMDD.zip
2. Double-click install.bat
3. Sign in with your Office 365 email
4. Double-click start.bat
```
