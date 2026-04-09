"""Local vector store using ChromaDB for chunk indexing and retrieval.

Provides:
- Chunked document indexing with deduplication via lastModifiedDateTime
- Semantic similarity search (top-k)
- File-level cache to skip unchanged documents
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import chromadb

from chunker import split_into_chunks

logger = logging.getLogger(__name__)

_DB_DIR = Path(__file__).parent / ".chroma_db"
_META_FILE = Path(__file__).parent / ".index_meta.json"
_COLLECTION_NAME = "sharepoint_chunks"


class VectorStore:
    """Thin wrapper around a ChromaDB persistent collection."""

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=str(_DB_DIR))
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        # file_id → {"last_modified": ..., "filename": ...}
        self._file_meta: dict[str, dict[str, str]] = {}
        self._load_meta()

    # ── Meta / cache persistence ────────────────────────────────────────
    def _load_meta(self) -> None:
        if _META_FILE.exists():
            try:
                self._file_meta = json.loads(_META_FILE.read_text())
            except Exception:
                self._file_meta = {}

    def _save_meta(self) -> None:
        _META_FILE.write_text(json.dumps(self._file_meta, indent=2))

    def is_current(self, file_id: str, last_modified: str) -> bool:
        """Return True if the file is already indexed at this version."""
        entry = self._file_meta.get(file_id)
        return entry is not None and entry.get("last_modified") == last_modified

    # ── Indexing ────────────────────────────────────────────────────────
    def index_file(
        self,
        file_id: str,
        filename: str,
        text: str,
        last_modified: str,
        site_name: str = "",
        web_url: str = "",
    ) -> int:
        """Chunk and index a file. Returns number of chunks created.

        Skips the file if it is already indexed at the same *last_modified*.
        """
        if self.is_current(file_id, last_modified):
            return 0

        # Remove stale chunks for this file
        self._remove_file_chunks(file_id)

        chunks = split_into_chunks(text)
        if not chunks:
            return 0

        ids = [f"{file_id}::chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file_id": file_id,
                "filename": filename,
                "site_name": site_name,
                "web_url": web_url,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "last_modified": last_modified,
            }
            for i in range(len(chunks))
        ]

        # ChromaDB add (uses default all-MiniLM-L6-v2 embeddings)
        self._collection.add(ids=ids, documents=chunks, metadatas=metadatas)

        self._file_meta[file_id] = {
            "last_modified": last_modified,
            "filename": filename,
            "site_name": site_name,
            "web_url": web_url,
            "chunks": len(chunks),
        }
        self._save_meta()

        logger.info("Indexed %s → %d chunks", filename, len(chunks))
        return len(chunks)

    def _remove_file_chunks(self, file_id: str) -> None:
        """Delete all chunks belonging to *file_id*."""
        try:
            results = self._collection.get(where={"file_id": file_id})
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
        except Exception:
            pass

    # ── Query ───────────────────────────────────────────────────────────
    def query(self, question: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return the *top_k* most relevant chunks for *question*."""
        count = self._collection.count()
        if count == 0:
            return []

        n = min(top_k, count)
        results = self._collection.query(query_texts=[question], n_results=n)

        chunks: list[dict[str, Any]] = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i] if results.get("distances") else None
            chunks.append(
                {
                    "text": doc,
                    "filename": meta.get("filename", ""),
                    "site_name": meta.get("site_name", ""),
                    "web_url": meta.get("web_url", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "total_chunks": meta.get("total_chunks", 1),
                    "distance": distance,
                }
            )
        return chunks

    # ── Utilities ───────────────────────────────────────────────────────
    def stats(self) -> dict[str, Any]:
        """Return index statistics."""
        return {
            "total_chunks": self._collection.count(),
            "indexed_files": len(self._file_meta),
            "files": {
                fid: {"filename": m["filename"], "chunks": m.get("chunks", "?")}
                for fid, m in self._file_meta.items()
            },
        }

    def clear(self) -> None:
        """Wipe the entire index."""
        self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._file_meta = {}
        self._save_meta()
        logger.info("Vector store cleared.")
