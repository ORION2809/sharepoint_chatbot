"""FastAPI application — SharePoint Chatbot with chunked RAG pipeline."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from sharepoint_client import SharePointClient
from vector_store import VectorStore
from llm_client import ask
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SharePoint Chatbot")
app.add_middleware(GZipMiddleware, minimum_size=500)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

sp = SharePointClient()
vs = VectorStore()

# ── Helpers ─────────────────────────────────────────────────────────────
_drive_id: str | None = None
_folder_path: str = config.SHAREPOINT_FOLDER

# ── Media file extensions (image + video) ──────────────────────────────
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff")
VIDEO_EXTS = (".mp4", ".avi", ".mov", ".wmv", ".mkv", ".webm")
MEDIA_EXTS = IMAGE_EXTS + VIDEO_EXTS

EXTRACTABLE_EXTS = (
    ".txt", ".pdf", ".docx", ".doc", ".csv", ".md",
    ".html", ".htm", ".json",
    ".xlsx", ".pptx",
) + MEDIA_EXTS
MAX_FILE_SIZE = config.MAX_FILE_SIZE_MB * 1024 * 1024


def _get_drive_id() -> str:
    global _drive_id
    if _drive_id:
        return _drive_id
    drives = sp.list_drives()
    if not drives:
        raise RuntimeError("No drives found on SharePoint site")
    _drive_id = drives[0]["id"]
    return _drive_id


def _is_extractable(item: dict[str, Any]) -> bool:
    name = item.get("name", "").lower()
    size = item.get("size", 0)
    return (
        any(name.endswith(ext) for ext in EXTRACTABLE_EXTS)
        and 0 < size <= MAX_FILE_SIZE
    )


# ── Indexing state (shared across requests) ─────────────────────────────
_index_status: dict[str, Any] = {
    "running": False,
    "progress": "",
    "last_result": None,
    "started_at": None,
}


def _run_index(scope: str) -> None:
    """Background task: scan SharePoint and index documents into ChromaDB."""
    _index_status["running"] = True
    _index_status["started_at"] = time.time()
    _index_status["progress"] = "Discovering files…"

    try:
        if scope == "folder":
            drive_id = _get_drive_id()
            all_files = sp.list_all_files_recursive(
                drive_id, _folder_path, depth=3,
            )
            # Tag with site name for metadata
            for f in all_files:
                f.setdefault("_site_name", config.SHAREPOINT_SITE_PATH)
        else:
            # Scan every site the user can reach
            def _progress(msg: str) -> None:
                _index_status["progress"] = msg
                logger.info(msg)

            all_files = sp.list_all_accessible_files(depth=3, on_progress=_progress)

        extractable = [f for f in all_files if _is_extractable(f)]
        _index_status["progress"] = (
            f"Found {len(extractable)} extractable files out of {len(all_files)} total. Indexing…"
        )
        logger.info("Indexable files: %d / %d total", len(extractable), len(all_files))

        indexed_chunks = 0
        skipped = 0
        failed = 0

        for i, item in enumerate(extractable):
            name = item.get("name", "unknown")
            file_id = item.get("id", name)
            last_modified = item.get("lastModifiedDateTime", "")
            site_name = item.get("_site_name", "")

            _index_status["progress"] = (
                f"[{i + 1}/{len(extractable)}] {name}"
            )

            # Cache check — skip if unchanged
            if vs.is_current(file_id, last_modified):
                skipped += 1
                continue

            text = sp.extract_text(item)
            if not text or text.startswith("[Could not"):
                failed += 1
                continue

            web_url = item.get("webUrl", "")
            count = vs.index_file(file_id, name, text, last_modified, site_name, web_url)
            indexed_chunks += count

        elapsed = round(time.time() - _index_status["started_at"], 1)
        result = {
            "files_scanned": len(extractable),
            "chunks_indexed": indexed_chunks,
            "files_skipped_cached": skipped,
            "files_failed": failed,
            "total_chunks_in_store": vs.stats()["total_chunks"],
            "total_indexed_files": vs.stats()["indexed_files"],
            "elapsed_seconds": elapsed,
        }
        _index_status["last_result"] = result
        _index_status["progress"] = "Done"
        logger.info("Indexing complete: %s", result)

    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        _index_status["progress"] = f"Error: {exc}"
        _index_status["last_result"] = {"error": str(exc)}
    finally:
        _index_status["running"] = False


# ── Models ──────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    analyze_media: bool = False


class SourceInfo(BaseModel):
    name: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]


# ── Routes ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── Indexing endpoints ──────────────────────────────────────────────────
@app.post("/api/index")
async def start_indexing(
    background_tasks: BackgroundTasks,
    scope: str = Query("all", pattern="^(all|folder)$"),
):
    """Trigger async document indexing.

    scope=all   → scan every SharePoint site the user can access
    scope=folder → only the configured SHAREPOINT_FOLDER
    """
    if _index_status["running"]:
        raise HTTPException(status_code=409, detail="Indexing already in progress")
    background_tasks.add_task(_run_index, scope)
    return {"status": "started", "scope": scope}


@app.get("/api/index/status")
async def index_status():
    return _index_status


@app.post("/api/index/clear")
async def clear_index():
    """Wipe the entire vector store."""
    if _index_status["running"]:
        raise HTTPException(409, "Cannot clear while indexing is running")
    vs.clear()
    return {"status": "cleared"}


# ── Chat endpoint (chunk-based RAG) ────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    analyze_media = body.analyze_media
    logger.info("Question: %s (analyze_media=%s)", question, analyze_media)

    # 1. Query vector store for the most relevant chunks
    chunks = vs.query(question, top_k=config.TOP_K_CHUNKS)

    if chunks:
        # Build context from top-k chunks
        context_chunks = [
            {"filename": c["filename"], "text": c["text"]}
            for c in chunks
        ]
        # Deduplicate sources preserving order
        seen_sources: dict[str, str] = {}
        for c in chunks:
            fname = c["filename"]
            if fname not in seen_sources:
                seen_sources[fname] = c.get("web_url", "")
        source_list = [
            SourceInfo(name=name, url=url)
            for name, url in seen_sources.items()
        ]

        # On-demand vision: if toggle is ON and media chunks are shallow metadata,
        # re-describe them via the vision API now
        if analyze_media:
            context_chunks = _enrich_media_chunks(context_chunks, chunks)

        logger.info(
            "Vector search returned %d chunks from: %s (distances: %s)",
            len(chunks),
            list(seen_sources.keys()),
            [round(c.get("distance", 0), 4) for c in chunks],
        )
    else:
        # Fallback: direct extraction (index not built yet)
        logger.warning("Vector store empty — falling back to direct file extraction")
        context_chunks, source_list = _fallback_extract(question)

    # 2. Call LLM with top chunks + question
    try:
        answer = ask(question, context_chunks)
    except Exception as exc:
        logger.error("LLM error: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    return ChatResponse(answer=answer, sources=source_list)


def _enrich_media_chunks(
    context_chunks: list[dict[str, str]],
    raw_chunks: list[dict],
) -> list[dict[str, str]]:
    """Replace shallow media placeholders with vision-API descriptions (on-demand).

    Only processes chunks whose text starts with ``[Image file:`` or ``[Video file:``.
    """
    enriched = list(context_chunks)
    for i, chunk in enumerate(enriched):
        text = chunk.get("text", "")
        if not (text.startswith("[Image file:") or text.startswith("[Video file:")):
            continue

        # Find matching raw chunk to get the filename
        filename = chunk.get("filename", "")
        if not filename:
            continue

        try:
            # Re-download and re-extract with vision enabled
            raw_meta = raw_chunks[i] if i < len(raw_chunks) else None
            web_url = raw_meta.get("web_url", "") if raw_meta else ""

            # Search for the file on SharePoint and re-extract with vision
            search_results = sp.search_files(filename)
            target = next(
                (f for f in search_results if f.get("name", "") == filename),
                None,
            )
            if target is None:
                logger.info("Could not find %s for vision enrichment", filename)
                continue

            vision_text = sp.extract_text(target, use_vision=True)
            if vision_text and not vision_text.startswith("[Could not"):
                enriched[i] = {**chunk, "text": vision_text}
                logger.info("Enriched media chunk: %s", filename)
        except Exception as exc:
            logger.warning("Vision enrichment failed for %s: %s", filename, exc)

    return enriched


def _fallback_extract(question: str) -> tuple[list[dict[str, str]], list[SourceInfo]]:
    """Legacy path: download & extract files directly when no index exists."""
    try:
        search_results = sp.search_files(question)
    except Exception:
        search_results = []

    try:
        drive_id = _get_drive_id()
        folder_files = sp.list_all_files_recursive(drive_id, _folder_path, depth=3)
        seen = {item.get("id") for item in search_results}
        for f in folder_files:
            if f.get("id") not in seen:
                search_results.append(f)
    except Exception:
        pass

    readable = [item for item in search_results if _is_extractable(item)]

    context: list[dict[str, str]] = []
    sources: list[SourceInfo] = []
    for item in readable[:8]:
        name = item.get("name", "unknown")
        text = sp.extract_text(item)
        if text and not text.startswith("[Could not"):
            context.append({"filename": name, "text": text})
            sources.append(SourceInfo(name=name, url=item.get("webUrl", "")))
    return context, sources


# ── Debug endpoints ─────────────────────────────────────────────────────
@app.get("/api/files")
async def list_files(scope: str = Query("folder", pattern="^(all|folder)$")):
    """List files visible to the app."""
    try:
        if scope == "all":
            files = sp.list_all_accessible_files(depth=3)
        else:
            drive_id = _get_drive_id()
            files = sp.list_all_files_recursive(drive_id, _folder_path, depth=3)
        return {
            "scope": scope,
            "total": len(files),
            "files": [
                {
                    "name": f.get("name", "?"),
                    "size": f.get("size", 0),
                    "site": f.get("_site_name", ""),
                }
                for f in files
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/index/stats")
async def index_stats():
    """Return vector store statistics."""
    return vs.stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
