# SharePoint Chatbot — Implementation Summary

## 1. Project Overview

The SharePoint Chatbot is a **Retrieval-Augmented Generation (RAG)** application that allows users to ask natural language questions about documents stored across SharePoint Online sites. The system indexes documents into a local vector database (ChromaDB), retrieves semantically relevant chunks at query time, and sends them alongside the user's question to an LLM to produce grounded, cited answers.

### Core Data Flow

```
User Question  ──►  FastAPI Backend (/api/chat)
                          │
                          ▼
                    ChromaDB Vector Store
                    (top-k semantic search)
                          │
                          ▼
                    Relevant Chunks + Metadata
                          │
                          ├──► [If analyze_media ON]
                          │        Download media → NVIDIA Vision API
                          │        → Rich description replaces placeholder
                          │
                          ▼
                    NVIDIA LLM (meta/llama-3.3-70b-instruct)
                          │
                          ▼
                    Answer + Clickable Source Citations → User
```

### Indexing Flow (background task)

```
POST /api/index?scope=all
    │
    ▼
Discover sites → Enumerate drives → Recursive file listing
    │
    ▼
For each file: Download → Extract text → Chunk (500 tokens, 50 overlap)
    │
    ▼
Embed chunks (all-MiniLM-L6-v2) → Store in ChromaDB
    │
    ▼
Cache file metadata (lastModifiedDateTime) → Skip unchanged on re-index
```

---

## 2. Architecture & Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Framework** | FastAPI 0.115 + Uvicorn 0.30 | Async HTTP server with GZip compression |
| **Template Engine** | Jinja2 3.1 | Server-side HTML rendering for chat UI |
| **Auth** | OAuth 2.0 Authorization Code Flow | Delegated access to SharePoint on behalf of a signed-in user |
| **SharePoint Access** | Microsoft Graph API v1.0 | Site discovery, drive listing, file search, content download |
| **HTTP Client** | httpx 0.27 (connection-pooled) | All outbound HTTP with persistent clients |
| **Vector Database** | ChromaDB ≥0.5 (local persistent) | Chunk storage + cosine similarity search |
| **Embeddings** | all-MiniLM-L6-v2 (via ChromaDB) | Semantic embedding for document chunks |
| **LLM** | NVIDIA API (OpenAI-compatible) | `meta/llama-3.3-70b-instruct` via `integrate.api.nvidia.com/v1` |
| **Vision Model** | NVIDIA Vision API | `microsoft/phi-3.5-vision-instruct` for image/video description |
| **LLM SDK** | openai 1.51 (Python) | OpenAI-compatible client (singleton, connection-pooled) |
| **Text Extraction** | python-docx, PyPDF2, BeautifulSoup4, openpyxl, python-pptx | Parse DOCX, PDF, HTML, XLSX, PPTX |
| **Vision Processing** | opencv-python-headless, Pillow | Video frame extraction, image handling |
| **Chunking** | Custom (`chunker.py`) | 500-token chunks, 50-token overlap, paragraph→sentence→word boundary breaking |
| **Config** | python-dotenv | Load secrets from `.env` file |
| **Runtime** | Python 3.10+ | Local development runtime |

### Project Structure

```
shrepoint_chatbot/
├── main.py                     # FastAPI app — routes, indexing, chat, media enrichment
├── sharepoint_client.py        # Graph API client — auth, search, download, text extraction
├── vector_store.py             # ChromaDB wrapper — indexing, querying, caching, stats
├── llm_client.py               # NVIDIA LLM integration (singleton client)
├── vision_client.py            # NVIDIA Vision API — image description, video frame analysis
├── chunker.py                  # Text chunking (500 tokens, 50 overlap)
├── config.py                   # Environment config loader with validation
├── login.py                    # One-time browser-based OAuth login
├── templates/
│   └── index.html              # Chat UI with vision toggle, index modal
├── requirements.txt            # 16 Python dependencies
├── install.bat                 # One-click Windows installer
├── start.bat                   # One-click Windows launcher
├── .env.example                # Credential template
├── .env                        # Secrets & config (not committed)
├── .token_cache.json           # OAuth tokens (auto-generated)
├── .chroma_db/                 # ChromaDB persistent storage
├── .index_meta.json            # File-level cache metadata
├── .gitignore                  # Excludes secrets, venv, cache
├── README.md                   # User-facing documentation
└── IMPLEMENTATION_SUMMARY.md   # This document
```

---

## 3. Authentication Flow

### Why Delegated Auth?

The Azure AD app registration has **delegated** permissions (`Sites.Read.All`, `Files.Read.All`) rather than application-level permissions. This means the app acts on behalf of a signed-in user. The authorization code flow was selected because the app is registered as a **confidential client** (has a client secret).

### Login Process (`login.py`)

1. **Check existing token** — If `.token_cache.json` exists and contains a valid refresh token, attempt a silent refresh. If successful, skip browser login.
2. **Build authorization URL** — Constructs the Azure AD `/authorize` endpoint URL with `client_id`, `response_type=code`, `redirect_uri=http://localhost:8400`, and scopes `Sites.Read.All Files.Read.All offline_access`.
3. **Start local HTTP server** — Binds to `localhost:8400` before opening the browser.
4. **Browser sign-in** — Opens the Azure AD login page. User authenticates with their Microsoft account.
5. **Receive callback** — Azure AD redirects to `http://localhost:8400?code=...`. The local handler captures the authorization code.
6. **Exchange code for tokens** — POSTs to `/oauth2/v2.0/token` with the auth code and client secret. Receives `access_token` + `refresh_token`.
7. **Persist tokens** — Saves both tokens to `.token_cache.json`.
8. **Verify access** — Makes a test Graph API call to confirm the token works.

### Token Lifecycle at Runtime

| Event | Action |
|-------|--------|
| Server starts | `SharePointClient.__init__()` loads tokens from `.token_cache.json` |
| API call succeeds | Use cached `access_token` |
| API call returns 401 | Clear `access_token`, call `_do_refresh()` using `refresh_token`, retry |
| Refresh succeeds | Save new tokens to cache file |
| Refresh fails | Raise error — user must run `python login.py` again |

### Azure AD Configuration Requirements

- **App Registration**: Registered in Azure AD tenant
- **Redirect URI**: `http://localhost:8400` (Web platform)
- **API Permissions**: Delegated — `Sites.Read.All`, `Files.Read.All`
- **Client Secret**: Required (confidential client)

---

## 4. SharePoint Client (`sharepoint_client.py`)

The `SharePointClient` class encapsulates all Microsoft Graph API interactions using **connection-pooled httpx clients** (two persistent instances: one for API calls, one for downloads).

### 4.1 Site & Drive Discovery

```
GET /v1.0/sites/{hostname}:/{sitePath}   →  Site ID
GET /v1.0/sites/{siteId}/drives          →  List of document libraries (drives)
GET /v1.0/sites?search=*&$top=100        →  All accessible sites (all-sites scan)
```

The site ID is resolved once from the configured hostname and site path, then cached in memory.

### 4.2 File Listing

```
GET /v1.0/drives/{driveId}/root:/{folderPath}:/children?$top=200
```

`list_all_files_recursive()` walks the folder tree up to a configurable depth (default 3), collecting all file items and recursing into subfolders. Supports OData pagination via `@odata.nextLink`.

### 4.3 All-Sites Scanning

`list_all_accessible_files()` enumerates every SharePoint site the signed-in user can access, iterates their document libraries, and recursively lists files. Each file is tagged with `_site_name` for metadata. Includes a progress callback for UI status updates.

### 4.4 Text Extraction Pipeline

| File Extension | Extraction Method |
|---------------|-------------------|
| `.txt`, `.csv`, `.md` | UTF-8 decode |
| `.pdf` | `PyPDF2.PdfReader` — extract text from each page |
| `.docx` | `python-docx` — join paragraph text |
| `.html`, `.htm` | `BeautifulSoup4` — `get_text()` with newline separator |
| `.xlsx` | `openpyxl` — iterate sheets and rows as tab-separated text |
| `.pptx` | `python-pptx` — extract text frames and table cells per slide |
| `.png`, `.jpg`, etc. | **With vision:** NVIDIA Vision API description. **Without:** metadata placeholder `[Image file: name \| size: N bytes]` |
| `.mp4`, `.avi`, etc. | **With vision:** Frame extraction + Vision API. **Without:** metadata placeholder `[Video file: name \| size: N bytes]` |
| Other | Attempt UTF-8 decode as fallback |

The `use_vision` parameter controls whether images/videos are sent to the Vision API (expensive) or stored as lightweight metadata placeholders (fast, used during indexing).

---

## 5. Vector Store (`vector_store.py`)

### Architecture

- **ChromaDB persistent client** stored in `.chroma_db/` directory
- **Cosine similarity** metric for nearest-neighbor search
- **Default embeddings**: `all-MiniLM-L6-v2` (via ChromaDB's built-in sentence-transformers)
- **File-level cache**: `.index_meta.json` tracks `file_id → {last_modified, filename, chunks}` to skip unchanged files on re-index

### Operations

| Method | Purpose |
|--------|---------|
| `index_file()` | Chunk text → embed → store. Removes stale chunks first. Skips if `lastModifiedDateTime` unchanged. |
| `query()` | Semantic search for top-k chunks. Returns text, filename, site_name, web_url, distance. |
| `is_current()` | Check if a file is already indexed at its current version |
| `stats()` | Return total chunks, indexed files, per-file chunk counts |
| `clear()` | Wipe entire collection and metadata cache |

### Chunk Metadata Schema

Each chunk stored in ChromaDB carries:
```json
{
  "file_id": "abc123",
  "filename": "document.docx",
  "site_name": "Sales Team",
  "web_url": "https://company.sharepoint.com/sites/sales/document.docx",
  "chunk_index": 0,
  "total_chunks": 5,
  "last_modified": "2026-03-15T14:30:00Z"
}
```

---

## 6. Chat Endpoint (`POST /api/chat`)

### RAG Pipeline

**Step 1 — Semantic Search**
```python
chunks = vs.query(question, top_k=config.TOP_K_CHUNKS)
```
Queries ChromaDB for the 5 most semantically similar chunks to the user's question.

**Step 2 — Build Context**
Assembles `context_chunks` from the top-k results. Deduplicates sources preserving order, extracting `web_url` for clickable citation links.

**Step 3 — Optional Vision Enrichment**
If `analyze_media=True` (user toggled ON), `_enrich_media_chunks()` scans context for placeholder chunks (`[Image file: ...]` or `[Video file: ...]`), re-downloads the file from SharePoint, sends it through the Vision API, and replaces the placeholder with the rich description.

**Step 4 — LLM Completion**
```python
answer = ask(question, context_chunks)
```
Sends context + question to NVIDIA LLM. Returns the answer with source citations.

**Step 5 — Fallback**
If the vector store is empty (not yet indexed), falls back to legacy direct-extraction: searches SharePoint, downloads files, extracts text inline.

### Response Format

```json
{
  "answer": "According to 'document.docx', the system has 5 modules...",
  "sources": [
    { "name": "document.docx", "url": "https://company.sharepoint.com/.../document.docx" }
  ]
}
```

---

## 7. LLM Integration (`llm_client.py`)

### Configuration

| Parameter | Value |
|-----------|-------|
| **Provider** | NVIDIA API (`integrate.api.nvidia.com/v1`) |
| **Model** | `meta/llama-3.3-70b-instruct` |
| **Temperature** | 0.2 (low for factual accuracy) |
| **Max Tokens** | 1,024 |
| **Context Limit** | 12,000 characters |
| **Client** | Singleton `OpenAI` instance (connection-pooled) |

### System Prompt

```
You are a helpful assistant that answers questions about documents stored in SharePoint.
Use ONLY the provided document context to answer.
If the context does not contain the answer, say so clearly.
Cite the source file name when possible.
```

### Context Assembly

Document text is formatted as filename-tagged blocks, truncated at 12K chars with a `[...truncated]` marker to prevent oversized LLM payloads.

---

## 8. Vision Integration (`vision_client.py`)

### Image Description

- Encodes the raw image bytes as a base64 data URL
- Sends to `microsoft/phi-3.5-vision-instruct` with a prompt requesting thorough description of all visible text, diagrams, charts, and labels
- Returns `[Image: filename]\n{description}`

### Video Description

- Writes raw video bytes to a temp file
- Opens with OpenCV, calculates total frames and duration
- Extracts up to 4 evenly-spaced key frames
- Resizes frames >768px for API limits
- Describes each frame individually with timestamp
- Returns `[Video: filename | duration: Xs | N key frames]\n{per-frame descriptions}`

### On-Demand Architecture

Vision is **never called during indexing** — media files are indexed with lightweight metadata placeholders. Vision is only invoked at chat time when the user explicitly enables the "Analyze images & videos" toggle. This keeps indexing fast while allowing rich media understanding on demand.

---

## 9. Web UI (`templates/index.html`)

### Design

- **Gradient header** with SharePoint branding (linear gradient `#0078d4` → `#005a9e`)
- **CSS custom properties** for consistent theming (`--primary`, `--bg`, `--surface`, etc.)
- **Animated message bubbles** with fade-in and slide-up transitions
- **Animated typing indicator** with bouncing dots
- **Modal dialog** with backdrop blur for index management
- **Responsive flexbox layout** adapting to screen sizes

### Features

| Feature | Implementation |
|---------|---------------|
| **Chat messages** | User (blue gradient, right), bot (white card, left), error (red border) |
| **Clickable citations** | Each source is an `<a>` tag linking to the SharePoint `webUrl` |
| **Vision toggle** | Toggle switch below input bar — "🔍 Analyze images & videos" |
| **Vision warning** | Amber text "⚠ May add 10–30 s per media file" when toggle is ON |
| **Dynamic typing text** | Changes to "Analyzing media & thinking…" when vision is active |
| **Index modal** | Shows stats (files, chunks), buttons for Index Folder / Index All Sites / Clear |
| **Progress banner** | Real-time progress bar with `[X/Y]` pattern during indexing (polls every 2s) |
| **Index badge** | Header shows "N files · N chunks" count |
| **XSS prevention** | All user text escaped via DOM `textContent` / `escapeHtml()` / `escapeAttr()` |

---

## 10. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Serve chat UI |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/chat` | Ask a question (RAG pipeline) |
| `POST` | `/api/index?scope=all\|folder` | Start background indexing |
| `GET` | `/api/index/status` | Poll indexing progress |
| `POST` | `/api/index/clear` | Wipe the vector store |
| `GET` | `/api/index/stats` | Return index statistics |
| `GET` | `/api/files?scope=all\|folder` | Debug: list accessible files |

### `POST /api/chat`

**Request:**
```json
{
  "question": "What modules does LegalGenie have?",
  "analyze_media": false
}
```

**Response (200):**
```json
{
  "answer": "According to 'MVP Implementation.docx', LegalGenie has 5 modules...",
  "sources": [
    { "name": "MVP Implementation.docx", "url": "https://bluevoirus.sharepoint.com/..." }
  ]
}
```

**Error Responses:**
- `400` — Empty question
- `502` — SharePoint or LLM error

---

## 11. Performance Optimizations

| Optimization | Detail |
|-------------|--------|
| **httpx connection pooling** | `SharePointClient` reuses two persistent `httpx.Client` instances instead of creating a new connection per request |
| **LLM client singleton** | Both `llm_client.py` and `vision_client.py` maintain a single `OpenAI` client across all requests |
| **GZip compression** | `GZipMiddleware` compresses responses >500 bytes |
| **Incremental re-indexing** | Files are skipped if `lastModifiedDateTime` hasn't changed since last index |
| **Background indexing** | Indexing runs as a FastAPI `BackgroundTask`, doesn't block the UI |
| **Lazy vision import** | `vision_client` is only imported when `use_vision=True` — no overhead for text-only workflows |
| **Chunk-based context** | Only top-k relevant chunks (not entire documents) are sent to the LLM |
| **On-demand vision** | Media files are indexed with fast metadata; vision API is called only when the user requests it |

---

## 12. Packaging & Distribution

### For Windows Coworkers

1. **`install.bat`** — One-click setup: creates virtual environment, installs all 16 dependencies, validates `.env`, runs OAuth login
2. **`start.bat`** — One-click launch: activates venv, starts Uvicorn, auto-opens browser at `http://127.0.0.1:8000`
3. **`.env.example`** — Template with all required/optional variables documented

### Distribution Steps

1. Zip the project folder (excluding `venv/`, `.chroma_db/`, `.env`, `.token_cache.json`, `__pycache__/`)
2. Share the zip with coworkers
3. Each user: extract → fill `.env` → double-click `install.bat` → double-click `start.bat`

---

## 13. Configuration Reference (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_CLIENT_ID` | Yes | — | Azure AD app registration client ID |
| `AZURE_CLIENT_SECRET` | Yes | — | Azure AD app registration client secret |
| `AZURE_TENANT_ID` | Yes | — | Azure AD tenant ID |
| `SHAREPOINT_HOSTNAME` | Yes | — | e.g. `yourcompany.sharepoint.com` |
| `SHAREPOINT_SITE_PATH` | No | `""` | e.g. `sites/yoursite` |
| `SHAREPOINT_FOLDER` | No | `""` | Subfolder path within the document library |
| `NVIDIA_API_KEY` | Yes | — | NVIDIA API key for LLM + Vision access |
| `NVIDIA_MODEL` | No | `meta/llama-3.3-70b-instruct` | LLM model identifier |
| `NVIDIA_VISION_MODEL` | No | `microsoft/phi-3.5-vision-instruct` | Vision model identifier |
| `TOP_K_CHUNKS` | No | `5` | Number of context chunks per query |
| `MAX_FILE_SIZE_MB` | No | `10` | Max file size to process (MB) |

---

## 14. Known Limitations & Future Improvements

### Current Limitations

1. **Single-user auth** — The token cache stores one user's tokens. Multi-user support would require per-session token management.
2. **No streaming** — LLM responses are returned in full after completion. No Server-Sent Events for progressive display.
3. **Context window ceiling** — The 12K character limit means only a portion of very large documents reaches the LLM.
4. **No conversation memory** — Each question is independent; no multi-turn context is maintained.
5. **Local vector store** — ChromaDB runs in-process; not suitable for multi-server deployments.

### Potential Improvements

1. **Streaming responses** — Use Server-Sent Events to stream LLM output token-by-token for better UX.
2. **Multi-user support** — Store tokens per session/user and support concurrent users.
3. **Webhook-based sync** — Use SharePoint change notifications to keep the index automatically up-to-date.
4. **Conversation memory** — Maintain chat history context across turns for follow-up questions.
5. **Hosted vector store** — Migrate to Pinecone, Weaviate, or ChromaDB server for multi-instance deployments.
6. **OCR integration** — Add Tesseract or Azure AI Vision for text extraction from scanned PDFs.

---

## 15. Dependencies

```
fastapi==0.115.0          # Web framework
uvicorn==0.30.6           # ASGI server
httpx==0.27.2             # HTTP client (connection-pooled)
python-dotenv==1.0.1      # .env file loading
openai==1.51.0            # OpenAI-compatible SDK for NVIDIA API
python-docx==1.1.2        # DOCX text extraction
PyPDF2==3.0.1             # PDF text extraction
beautifulsoup4==4.12.3    # HTML text extraction
jinja2==3.1.4             # Template rendering
python-multipart==0.0.12  # Form data parsing
msal==1.31.0              # Microsoft auth (used by legacy test scripts)
chromadb>=0.5.0           # Vector database with built-in embeddings
openpyxl==3.1.5           # Excel file extraction
python-pptx==1.0.2        # PowerPoint file extraction
opencv-python-headless==4.10.0.84  # Video frame extraction
Pillow>=10.0.0            # Image processing
```
