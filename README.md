# SharePoint Chatbot

An AI-powered RAG (Retrieval-Augmented Generation) chatbot that lets you ask natural language questions about documents stored across your SharePoint Online sites. It indexes files into a local vector database, retrieves the most relevant chunks per query, and generates grounded answers with clickable source citations.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-orange)
![NVIDIA](https://img.shields.io/badge/NVIDIA-LLM%20%2B%20Vision-76b900)

---

## Features

### Core RAG Pipeline
- **Semantic search** — Documents are chunked (500 tokens, 50 overlap) and embedded into ChromaDB using `all-MiniLM-L6-v2`. Queries retrieve the top-k most relevant chunks via cosine similarity.
- **Grounded answers** — Only indexed document content is used for answers. The LLM is instructed to cite source files and say "I don't know" when context is insufficient.
- **Clickable citations** — Every answer includes source links that open directly in SharePoint.

### File Type Support
| Type | Extensions | Method |
|------|-----------|--------|
| Documents | `.pdf`, `.docx`, `.doc` | PyPDF2, python-docx |
| Spreadsheets | `.xlsx` | openpyxl (all sheets, tab-separated rows) |
| Presentations | `.pptx` | python-pptx (text frames + tables per slide) |
| Web | `.html`, `.htm` | BeautifulSoup4 |
| Plain text | `.txt`, `.csv`, `.md`, `.json` | UTF-8 decode |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.tiff` | NVIDIA Vision API (on-demand) |
| Videos | `.mp4`, `.avi`, `.mov`, `.wmv`, `.mkv`, `.webm` | OpenCV frame extraction + Vision API (on-demand) |

### Optional Vision Analysis
- **Toggle in UI** — "🔍 Analyze images & videos" switch below the input bar
- **Warning** — Amber text warns users: "⚠ May add 10–30 s per media file"
- **On-demand only** — Images and videos are indexed with fast metadata placeholders. Vision API is called only at chat time when the toggle is ON, keeping indexing fast.

### Multi-Site Scanning
- **Index All Sites** — Discovers every SharePoint site accessible to the signed-in user, enumerates all document libraries and folders, and indexes everything.
- **Index Folder** — Scopes indexing to the configured `SHAREPOINT_FOLDER` only.
- **Incremental re-indexing** — Skips files unchanged since the last index (based on `lastModifiedDateTime`).

### Performance
- Connection-pooled HTTP clients (httpx) for SharePoint API calls
- Singleton LLM/Vision clients reused across requests
- GZip response compression
- Background indexing (non-blocking UI)

---

## Quick Start

### Prerequisites

1. **Python 3.10+** — Download from [python.org](https://www.python.org/downloads/). Check **"Add Python to PATH"** during installation.
2. **Azure AD App Registration** — With delegated permissions:
   - `Sites.Read.All`
   - `Files.Read.All`
   - Redirect URI: `http://localhost:8400`
   - Client secret created
3. **NVIDIA API Key** — Free from [build.nvidia.com](https://build.nvidia.com/). Used for LLM (`meta/llama-3.3-70b-instruct`) and Vision (`microsoft/phi-3.5-vision-instruct`).

### Windows (One-Click)

```
1. Copy the project folder to your machine
2. Copy .env.example → .env and fill in your credentials
3. Double-click install.bat    (creates venv, installs deps, runs login)
4. Double-click start.bat      (starts server, opens browser)
```

### Manual Setup (Windows / macOS / Linux)

```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env with your Azure AD + NVIDIA credentials

# 4. Sign in to SharePoint (one-time, opens browser)
python login.py

# 5. Start the server
python main.py
# → Opens at http://127.0.0.1:8000
```

---

## Usage

### 1. Index Your Documents

Click **⚙ Index** in the header to open the index management modal.

| Button | Scope |
|--------|-------|
| **Index All Sites** | Scan every SharePoint site you have access to |
| **Index Folder** | Only the folder specified in `SHAREPOINT_FOLDER` |
| **Clear Index** | Wipe the entire vector store and re-index from scratch |

A progress banner shows real-time status: `[3/25] document.docx`. The header badge displays total indexed files and chunks.

### 2. Ask Questions

Type a question in the input bar and press **Enter** or click **Send**.

Examples:
- "What modules does our product have?"
- "Summarize the legal judgment in the Kaladevi case"
- "What are the API endpoints for the research tab?"

### 3. Analyze Images & Videos (Optional)

Toggle the **🔍 Analyze images & videos** switch below the input bar. When enabled:
- The chatbot will use NVIDIA's Vision API to describe any images or video frames found in relevant search results
- A warning appears: "⚠ May add 10–30 s per media file"
- The typing indicator changes to "Analyzing media & thinking…"

**When to use**: When your question relates to diagrams, architecture images, screenshots, or video content stored in SharePoint.

---

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `AZURE_CLIENT_ID` | ✅ | — | Azure AD app registration client ID |
| `AZURE_CLIENT_SECRET` | ✅ | — | Azure AD app registration client secret |
| `AZURE_TENANT_ID` | ✅ | — | Azure AD tenant ID |
| `SHAREPOINT_HOSTNAME` | ✅ | — | Your SharePoint domain, e.g. `yourcompany.sharepoint.com` |
| `SHAREPOINT_SITE_PATH` | | `""` | Site path, e.g. `sites/engineering` |
| `SHAREPOINT_FOLDER` | | `""` | Subfolder to scope "Index Folder" to |
| `NVIDIA_API_KEY` | ✅ | — | NVIDIA API key from build.nvidia.com |
| `NVIDIA_MODEL` | | `meta/llama-3.3-70b-instruct` | LLM model for text answers |
| `NVIDIA_VISION_MODEL` | | `microsoft/phi-3.5-vision-instruct` | Vision model for image/video analysis |
| `TOP_K_CHUNKS` | | `5` | Number of context chunks retrieved per query |
| `MAX_FILE_SIZE_MB` | | `10` | Maximum file size to process (MB) |

### Azure AD App Registration Setup

1. Go to [Azure Portal](https://portal.azure.com/) → **Azure Active Directory** → **App registrations** → **New registration**
2. Name: e.g. "SharePoint Chatbot"
3. Redirect URI: **Web** → `http://localhost:8400`
4. Under **API permissions**, add **Microsoft Graph** → **Delegated**:
   - `Sites.Read.All`
   - `Files.Read.All`
5. Grant admin consent (or have an admin do it)
6. Under **Certificates & secrets**, create a new **client secret** and copy the value
7. Copy the **Application (client) ID** and **Directory (tenant) ID** from the Overview page

### NVIDIA API Key Setup

1. Go to [build.nvidia.com](https://build.nvidia.com/)
2. Sign up / sign in
3. Navigate to any model page (e.g. Llama 3.3 70B Instruct)
4. Click **"Get API Key"** and copy it

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Web Browser                         │
│                 (templates/index.html)                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Chat UI · Vision Toggle · Index Modal · Sources │   │
│  └──────────────────┬───────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────┘
                      │ HTTP (JSON)
┌─────────────────────┼───────────────────────────────────┐
│              FastAPI  │  (main.py)                       │
│                      ▼                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ /api/chat│  │/api/index│  │  /api/index/status    │  │
│  └────┬─────┘  └────┬─────┘  └──────────────────────┘  │
│       │              │                                   │
│       ▼              ▼                                   │
│  ┌─────────────────────────────────────────────────┐    │
│  │            vector_store.py (ChromaDB)            │    │
│  │  index_file() · query() · stats() · clear()     │    │
│  └────────────┬────────────────────────────────────┘    │
│               │                                          │
│       ┌───────┴────────┐                                │
│       ▼                ▼                                │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │llm_client│   │vision_client │   │sharepoint_client│  │
│  │ (NVIDIA) │   │(NVIDIA Vision│   │ (Graph API)     │  │
│  └──────────┘   └──────────────┘   └────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Request Flow: Chat

1. User sends question (+ `analyze_media` flag) → `POST /api/chat`
2. `vector_store.query()` retrieves top-k chunks from ChromaDB
3. If `analyze_media=true`, `_enrich_media_chunks()` replaces image/video placeholders with Vision API descriptions
4. `llm_client.ask()` sends chunks + question to NVIDIA LLM
5. Response returned with answer + `[{name, url}]` clickable sources

### Request Flow: Indexing

1. `POST /api/index?scope=all` triggers background task
2. `sharepoint_client` discovers all accessible sites → drives → files (recursive)
3. For each extractable file: download → extract text → `chunker.split_into_chunks()`
4. `vector_store.index_file()` embeds chunks and stores with metadata (web_url, site_name, file_id)
5. File-level cache prevents re-indexing unchanged files

---

## Project Structure

```
shrepoint_chatbot/
│
├── main.py                     # FastAPI app — routes, indexing, chat, media enrichment
│                                 - GET  /              → serve UI
│                                 - POST /api/chat      → RAG pipeline
│                                 - POST /api/index     → background indexing
│                                 - GET  /api/index/status → poll progress
│                                 - POST /api/index/clear  → wipe index
│                                 - GET  /api/index/stats  → index statistics
│                                 - GET  /api/files     → debug file listing
│
├── sharepoint_client.py        # Microsoft Graph API client
│                                 - OAuth token management (load, refresh, cache)
│                                 - Site/drive discovery, recursive file listing
│                                 - All-sites scanning with progress callback
│                                 - File search (sanitized OData queries)
│                                 - Download + text extraction for 10+ file types
│                                 - Connection-pooled httpx clients
│
├── vector_store.py             # ChromaDB vector store wrapper
│                                 - Persistent local collection (cosine similarity)
│                                 - Chunk indexing with dedup by lastModifiedDateTime
│                                 - Semantic top-k query returning text + metadata
│                                 - File-level cache in .index_meta.json
│
├── llm_client.py               # NVIDIA LLM client (singleton)
│                                 - System prompt for grounded, cited answers
│                                 - Context assembly with 12K char truncation
│                                 - Temperature 0.2, max 1024 tokens
│
├── vision_client.py            # NVIDIA Vision API client (singleton)
│                                 - Image: base64 encode → describe via phi-3.5-vision
│                                 - Video: OpenCV frame extraction (up to 4 frames)
│                                   → resize → describe each with timestamp
│
├── chunker.py                  # Text chunking engine
│                                 - 500 tokens per chunk, 50 token overlap
│                                 - Paragraph → sentence → word boundary breaking
│                                 - Discards fragments < 30 tokens
│
├── config.py                   # Environment config loader
│                                 - Validates required vars at startup
│                                 - Provides typed constants for all modules
│
├── login.py                    # One-time OAuth2 login script
│                                 - Starts local HTTP server on port 8400
│                                 - Opens browser for Microsoft sign-in
│                                 - Exchanges auth code for access + refresh tokens
│                                 - Caches tokens in .token_cache.json
│
├── templates/
│   └── index.html              # Chat UI (single-page, vanilla JS)
│                                 - Gradient header with index badge
│                                 - Message bubbles with fade-in animation
│                                 - Vision toggle + warning
│                                 - Index modal with stats + progress banner
│                                 - Clickable source citation links
│                                 - XSS-safe rendering
│
├── requirements.txt            # 16 Python dependencies
├── install.bat                 # Windows: one-click setup
├── start.bat                   # Windows: one-click launcher
├── .env.example                # Credential template with all variables
├── .env                        # Actual credentials (git-ignored)
├── .token_cache.json           # OAuth tokens (git-ignored)
├── .chroma_db/                 # ChromaDB persistent data (git-ignored)
├── .index_meta.json            # File cache metadata (git-ignored)
├── .gitignore                  # Excludes secrets, venv, cache, pycache
├── README.md                   # This file
└── IMPLEMENTATION_SUMMARY.md   # Technical deep-dive
```

---

## API Reference

### `POST /api/chat`

Ask a question about indexed SharePoint documents.

**Request:**
```json
{
  "question": "What modules does LegalGenie have?",
  "analyze_media": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `question` | string | *(required)* | Natural language question |
| `analyze_media` | boolean | `false` | Enable AI vision for images/videos in results |

**Response (200):**
```json
{
  "answer": "According to 'MVP Implementation.docx', LegalGenie has 5 modules: Research, Contracts, Drafting, Litigation, and Compliance.",
  "sources": [
    {
      "name": "MVP Implementation.docx",
      "url": "https://yourcompany.sharepoint.com/sites/team/Shared%20Documents/MVP%20Implementation.docx"
    }
  ]
}
```

**Errors:** `400` (empty question), `502` (SharePoint or LLM error)

### `POST /api/index?scope=all|folder`

Start background document indexing.

**Query params:** `scope=all` (default) or `scope=folder`

**Response:** `{"status": "started", "scope": "all"}`

**Error:** `409` if indexing already in progress

### `GET /api/index/status`

Poll indexing progress.

**Response:**
```json
{
  "running": true,
  "progress": "[3/25] document.docx",
  "last_result": null,
  "started_at": 1712500000.0
}
```

### `GET /api/index/stats`

Return index statistics.

**Response:**
```json
{
  "total_chunks": 142,
  "indexed_files": 8,
  "files": {
    "abc123": { "filename": "document.docx", "chunks": 23 }
  }
}
```

### `POST /api/index/clear`

Wipe the entire vector store. Requires re-indexing.

### `GET /api/health`

Health check. Returns `{"status": "ok"}`.

### `GET /api/files?scope=all|folder`

Debug endpoint — lists files visible to the app.

---

## Distributing to Coworkers

### What to Share

Zip the project folder **excluding** these (they're auto-generated or contain secrets):
- `venv/`
- `.chroma_db/`
- `.env`
- `.token_cache.json`
- `.index_meta.json`
- `__pycache__/`

### What Each User Needs

1. **Python 3.10+** installed with "Add to PATH" checked
2. **Their own `.env`** — copy `.env.example` and fill in credentials (Azure AD app + NVIDIA key)
3. **Run `install.bat`** — creates venv, installs deps, runs browser login
4. **Run `start.bat`** — launches the chatbot

Each user authenticates with their own Microsoft account and sees only the SharePoint sites they have access to.

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `Not authenticated! Run 'python login.py'` | Token expired. Re-run `python login.py` to refresh |
| `No drives found on SharePoint site` | Check `SHAREPOINT_HOSTNAME` and `SHAREPOINT_SITE_PATH` in `.env` |
| `LLM request failed` | Verify `NVIDIA_API_KEY` is valid. Check [status.nvidia.com](https://status.nvidia.com/) |
| `chromadb` import error | Run `pip install chromadb>=0.5.0` (requires C++ build tools on some systems) |
| Index shows 0 files | Ensure the authenticated user has read access to the target SharePoint site |
| Vision toggle is slow | Expected — each image/video requires a separate NVIDIA API call. Use only when needed. |
| Port 8000 already in use | Kill the existing process or change the port in `main.py` |
| `install.bat` says Python not found | Install Python and ensure "Add to PATH" was checked, then restart the terminal |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.115.0 | Web framework |
| uvicorn | 0.30.6 | ASGI server |
| httpx | 0.27.2 | HTTP client (connection-pooled) |
| python-dotenv | 1.0.1 | `.env` file loading |
| openai | 1.51.0 | OpenAI-compatible SDK for NVIDIA API |
| python-docx | 1.1.2 | Word document text extraction |
| PyPDF2 | 3.0.1 | PDF text extraction |
| beautifulsoup4 | 4.12.3 | HTML text extraction |
| jinja2 | 3.1.4 | Template rendering |
| python-multipart | 0.0.12 | Form data parsing |
| msal | 1.31.0 | Microsoft auth library |
| chromadb | ≥0.5.0 | Vector database with built-in embeddings |
| openpyxl | 3.1.5 | Excel file extraction |
| python-pptx | 1.0.2 | PowerPoint file extraction |
| opencv-python-headless | 4.10.0.84 | Video frame extraction |
| Pillow | ≥10.0.0 | Image processing |

---

## License

Internal use only. Not licensed for public distribution.
