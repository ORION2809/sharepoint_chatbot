# SharePoint Chatbot

An AI-powered chatbot that lets you ask natural language questions about documents stored in your company's SharePoint — and get grounded, cited answers instantly.

It indexes your SharePoint files into a local vector database once, then at query time retrieves the most relevant document sections and passes them to an LLM to produce accurate answers with clickable source links.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-orange)
![NVIDIA](https://img.shields.io/badge/NVIDIA-LLM%20%2B%20Vision-76b900)

---

## Table of Contents

1. [What You Need Before Starting](#1-what-you-need-before-starting)
2. [Employee Quick Start (Windows)](#2-employee-quick-start-windows)
3. [Manual Setup (All Platforms)](#3-manual-setup-all-platforms)
4. [Filling In Your Credentials](#4-filling-in-your-credentials)
5. [Using the Chatbot](#5-using-the-chatbot)
6. [Re-running and Daily Use](#6-re-running-and-daily-use)
7. [Configuration Reference](#7-configuration-reference)
8. [Admin: Azure AD App Registration](#8-admin-azure-ad-app-registration)
9. [Admin: Getting an NVIDIA API Key](#9-admin-getting-an-nvidia-api-key)
10. [Admin: Distributing to Coworkers](#10-admin-distributing-to-coworkers)
11. [Troubleshooting](#11-troubleshooting)
12. [Architecture Overview](#12-architecture-overview)
13. [API Reference](#13-api-reference)

---

## 1. What You Need Before Starting

Before you run anything, make sure you have:

| Requirement | Where to Get It | Notes |
|-------------|----------------|-------|
| **Python 3.10+** | [python.org/downloads](https://www.python.org/downloads/) | During install, check **"Add Python to PATH"** |
| **Azure AD credentials** | Your IT admin / Azure Portal | Client ID, Client Secret, Tenant ID |
| **NVIDIA API Key** | [build.nvidia.com](https://build.nvidia.com/) | Free tier available |
| **SharePoint hostname** | Your company's SharePoint URL | e.g. `yourcompany.sharepoint.com` |

> **If you are an employee** being set up by your IT team, ask them for the pre-filled `.env` file. You only need Python installed on your machine.

---

## 2. Employee Quick Start (Windows)

If you received the project zip from IT, follow these steps exactly:

### Step 1 — Install Python (one-time)

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3.x installer
3. Run it — **tick the "Add Python to PATH" checkbox** before clicking Install
4. Click **Install Now**

### Step 2 — Extract the ZIP

Right-click the ZIP file  **Extract All**  choose a folder (e.g. `C:\SharePointChatbot`)

### Step 3 — Fill in Credentials

1. Inside the extracted folder, find `.env.example`
2. Copy it and rename the copy to `.env` (remove the `.example` part)
3. Open `.env` with Notepad and fill in each value (see [Section 4](#4-filling-in-your-credentials))

> If your IT admin gave you a pre-filled `.env` file, just drop it in the folder — skip this step.

### Step 4 — Run the Installer (one-time)

Double-click **`install.bat`**

A setup wizard will open. It will:
- Create a Python virtual environment
- Install all required packages automatically
- Open a browser window for you to sign in with your Office 365 account
- Confirm setup is complete

If a plain black terminal opens instead, that is normal — follow the on-screen prompts.

### Step 5 — Start the Chatbot

Double-click **`start.bat`**

A browser window will open at `http://127.0.0.1:8000` with the chat interface.

> Run `start.bat` every time you want to use the chatbot.

---

## 3. Manual Setup (All Platforms)

Use this if you are on macOS/Linux, or prefer the command line.

```bash
# Clone or extract the project
cd sharepoint_chatbot

# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Set up your credentials (see Section 4)
cp .env.example .env
# Edit .env with your values

# Sign in to SharePoint (one-time — opens a browser)
python login.py

# Start the server
python main.py
```

The chatbot will be available at **http://127.0.0.1:8000**

---

## 4. Filling In Your Credentials

Open the `.env` file (use Notepad or any text editor). Edit each line:

```
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here
AZURE_TENANT_ID=your-tenant-id-here
SHAREPOINT_HOSTNAME=yourcompany.sharepoint.com
SHAREPOINT_SITE_PATH=sites/yoursite
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxx
```

### Where to Find Each Value

| Variable | Where to Find It |
|----------|----------------|
| `AZURE_CLIENT_ID` | Azure Portal  App registrations  your app  **Application (client) ID** |
| `AZURE_CLIENT_SECRET` | Azure Portal  App registrations  Certificates & secrets  **Value** |
| `AZURE_TENANT_ID` | Azure Portal  App registrations  your app  **Directory (tenant) ID** |
| `SHAREPOINT_HOSTNAME` | Your SharePoint URL, e.g. `acme.sharepoint.com` |
| `SHAREPOINT_SITE_PATH` | Path after the hostname, e.g. `sites/legal` (leave blank for root site) |
| `SHAREPOINT_FOLDER` | A subfolder to index, e.g. `Shared Documents/Contracts` (optional) |
| `NVIDIA_API_KEY` | [build.nvidia.com](https://build.nvidia.com/)  any model page  **Get API Key** |

> **Never share your `.env` file.** It contains secret credentials. The `.gitignore` ensures it is never committed to Git.

---

## 5. Using the Chatbot

### Step 1 — Index Your Documents (First Time)

Before asking questions, the chatbot must read and index your SharePoint documents.

1. Open `http://127.0.0.1:8000` in your browser
2. Click the **Index** button in the top-right header
3. Choose an option:
   - **Index All Sites** — scans every SharePoint site your account can access
   - **Index Folder** — scans only the folder set in `SHAREPOINT_FOLDER`
4. Watch the progress bar: `[3/25] Contracts_2024.pdf` — it updates in real time
5. When the header shows a count like `12 files  143 chunks`, indexing is done

> Indexing is incremental — re-running it only processes new or changed files.

### Step 2 — Ask a Question

Type your question in the input bar at the bottom and press **Enter** or click **Send**.

**Good examples:**
```
What are the payment terms in our standard contract?
Summarize the Q3 2024 board meeting minutes
Which employees are listed as signatories in the MOU?
What does the IT policy say about personal device usage?
What are the project milestones for the Apex initiative?
```

Each answer includes **clickable source links** that open the original file in SharePoint.

### Step 3 — Analyze Images and Videos (Optional)

If your question is about a diagram, screenshot, chart, or video in SharePoint:

1. Toggle on **Analyze images & videos** below the input bar
2. Ask your question — the chatbot will use NVIDIA Vision AI to describe relevant images/video frames

> This adds 10–30 seconds per media file. Keep it off for text-only questions.

---

## 6. Re-running and Daily Use

| Task | How |
|------|-----|
| Start the chatbot | Double-click `start.bat` (Windows) or run `python main.py` |
| Stop the chatbot | Close the terminal window or press `Ctrl+C` |
| Re-index after new files are added | Click Index  Index All Sites in the UI |
| Re-login if your session expires | Run `install.bat` again or `python login.py` |
| Clear and rebuild the index | Click Index  Clear Index, then re-index |

You only need to re-run `login.py` if you see:
```
Not authenticated! Run 'python login.py' first.
```

---

## 7. Configuration Reference

All options live in the `.env` file. Optional variables have defaults.

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `AZURE_CLIENT_ID` | Yes | — | Azure AD app Client ID |
| `AZURE_CLIENT_SECRET` | Yes | — | Azure AD app Client Secret |
| `AZURE_TENANT_ID` | Yes | — | Azure AD Tenant ID |
| `SHAREPOINT_HOSTNAME` | Yes | — | Your SharePoint domain, e.g. `acme.sharepoint.com` |
| `SHAREPOINT_SITE_PATH` | No | `""` | Site path, e.g. `sites/legal` |
| `SHAREPOINT_FOLDER` | No | `""` | Subfolder to scope "Index Folder" |
| `NVIDIA_API_KEY` | Yes | — | NVIDIA API key |
| `NVIDIA_MODEL` | No | `meta/llama-3.3-70b-instruct` | LLM model for answering |
| `NVIDIA_VISION_MODEL` | No | `microsoft/phi-3.5-vision-instruct` | Vision model for media |
| `TOP_K_CHUNKS` | No | `5` | Document chunks retrieved per query |
| `MAX_FILE_SIZE_MB` | No | `10` | Max file size to process (MB) |

---

## 8. Admin: Azure AD App Registration

> Do this once for your organisation. All users share the same app registration.

1. Go to [Azure Portal](https://portal.azure.com/)  **Azure Active Directory**  **App registrations**  **New registration**
2. **Name**: `SharePoint Chatbot`
3. **Supported account types**: Accounts in this organizational directory only
4. **Redirect URI**: Platform = `Web`, URI = `http://localhost:8400`
5. Click **Register**
6. On the **Overview** page, copy:
   - **Application (client) ID**  `AZURE_CLIENT_ID`
   - **Directory (tenant) ID**  `AZURE_TENANT_ID`
7. Go to **Certificates & secrets**  **New client secret**
   - Set expiry to 24 months
   - Copy the **Value** immediately (shown only once)  `AZURE_CLIENT_SECRET`
8. Go to **API permissions**  **Add a permission**  **Microsoft Graph**  **Delegated**:
   - Add `Sites.Read.All`
   - Add `Files.Read.All`
9. Click **Grant admin consent for [your org]**

---

## 9. Admin: Getting an NVIDIA API Key

1. Go to [build.nvidia.com](https://build.nvidia.com/)
2. Create a free account
3. Open any model page (e.g. Llama 3.3 70B Instruct)
4. Click **Get API Key**
5. Copy the key (starts with `nvapi-`)  `NVIDIA_API_KEY`

---

## 10. Admin: Distributing to Coworkers

### Option A — Share the ZIP (each user fills their own `.env`)

```bash
python build_installer.py --zip
```

Creates `dist/SharePointChatbot_YYYYMMDD.zip`. Share this ZIP. Each user must add their own `.env` before running `install.bat`.

### Option B — Pre-fill credentials for users

```bash
python build_installer.py --zip --prefill
```

Prompts you for credentials and bakes them into the ZIP. Users just extract and double-click `install.bat`.

### Option C — Windows `.exe` installer

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Run: `iscc installer.iss`
3. Distribute `SharePointChatbot_Setup.exe`

### What Each User Needs

- Python 3.10+ installed with "Add to PATH"
- A Microsoft account with access to the SharePoint site
- The `.env` file (pre-filled by IT or self-filled)

### Uninstalling

Double-click `uninstall.bat` to cleanly remove the virtual environment, index, tokens, and shortcuts.

---

## 11. Troubleshooting

| Problem | Solution |
|---------|---------|
| `Not authenticated! Run 'python login.py'` | Token expired. Re-run `install.bat` or `python login.py` |
| `No drives found on SharePoint site` | Check `SHAREPOINT_HOSTNAME` and `SHAREPOINT_SITE_PATH` in `.env` |
| `LLM request failed` / no answer | Verify `NVIDIA_API_KEY` at [build.nvidia.com](https://build.nvidia.com/) |
| Index shows 0 files after indexing | Ensure your Microsoft account has read access to the SharePoint site |
| `chromadb` import error on Windows | Install [Visual C++ Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe) and retry |
| Browser does not open during login | Manually copy-paste the URL printed in the terminal |
| Port 8000 already in use | Run `netstat -ano | findstr :8000`, then `taskkill /PID <pid> /F` |
| `install.bat` says Python not found | Re-install Python, tick "Add Python to PATH", restart your PC |
| Vision toggle is very slow | Expected — each media file adds an extra API call. Turn off for text-only questions |
| Permission denied writing `.env` | Extract the ZIP to a user-owned folder, not `C:\Program Files` |

---

## 12. Architecture Overview

```
User Browser (index.html)
    
      HTTP/JSON
    
FastAPI Server (main.py)
    
     POST /api/chat  ChromaDB query (top-k chunks)
                       (optional) NVIDIA Vision API
                       NVIDIA LLM  answer + sources
    
     POST /api/index  SharePoint Graph API (discover files)
                         Download + extract text
                         Chunk  embed  store in ChromaDB

External Services:
  Microsoft Graph API    SharePoint file access (OAuth 2.0 delegated)
  NVIDIA LLM API         meta/llama-3.3-70b-instruct
  NVIDIA Vision API      microsoft/phi-3.5-vision-instruct
```

### Supported File Types

| Format | Extensions |
|--------|-----------|
| Word documents | `.docx` |
| PDFs | `.pdf` |
| Excel spreadsheets | `.xlsx` |
| PowerPoint | `.pptx` |
| Web pages | `.html`, `.htm` |
| Plain text | `.txt`, `.csv`, `.md`, `.json` |
| Images (vision, on-demand) | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.tiff` |
| Videos (vision, on-demand) | `.mp4`, `.avi`, `.mov`, `.wmv`, `.mkv`, `.webm` |

---

## 13. API Reference

The chatbot exposes a REST API for programmatic use.

### `POST /api/chat`

**Request:**
```json
{
  "question": "What are the payment terms in our standard contract?",
  "analyze_media": false
}
```

**Response (200):**
```json
{
  "answer": "According to Standard_Contract_2024.docx, payment terms are Net 30 days...",
  "sources": [
    {
      "name": "Standard_Contract_2024.docx",
      "url": "https://acme.sharepoint.com/sites/legal/Shared%20Documents/Standard_Contract_2024.docx"
    }
  ]
}
```

**Errors:** `400` (empty question), `502` (upstream error)

### `POST /api/index?scope=all|folder`

Start background indexing. Returns `{"status": "started"}`. Error `409` if already running.

### `GET /api/index/status`

Poll progress: `{"running": true, "progress": "[7/42] file.docx", ...}`

### `GET /api/index/stats`

Returns total chunks, file count, and per-file chunk counts.

### `POST /api/index/clear`

Wipes the entire index. Requires re-indexing afterward.

### `GET /api/health`

Returns `{"status": "ok"}`.

---

## Project Structure

```
sharepoint_chatbot/
 main.py                  # FastAPI server — all routes and RAG pipeline
 sharepoint_client.py     # Microsoft Graph API — auth, file listing, extraction
 vector_store.py          # ChromaDB wrapper — indexing and querying
 llm_client.py            # NVIDIA LLM client
 vision_client.py         # NVIDIA Vision client — image and video description
 chunker.py               # Text chunker (500 tokens, 50 overlap)
 config.py                # .env loader and validation
 login.py                 # One-time OAuth2 browser login
 setup_wizard.py          # GUI setup wizard for employees
 build_installer.py       # Build distributable ZIP
 installer.iss            # Inno Setup script for .exe installer
 uninstall.bat            # Clean uninstall
 install.bat              # Windows one-click setup
 start.bat                # Windows one-click launcher
 templates/
    index.html           # Chat UI
 requirements.txt         # Python dependencies
 .env.example             # Credential template
 IMPLEMENTATION_SUMMARY.md  # Technical deep-dive for developers
```

---

## License

Internal use only. Not for public distribution.

