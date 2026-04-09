"""Text chunker for RAG pipeline.

Splits documents into 300–800 token chunks with overlap,
breaking at paragraph → sentence → word boundaries.
"""

from __future__ import annotations

import re

# ~4 characters per token on average for English text
_CHARS_PER_TOKEN = 4

# Default: ~500 tokens per chunk, ~50 tokens overlap
DEFAULT_MAX_TOKENS = 500
DEFAULT_OVERLAP_TOKENS = 50
MIN_CHUNK_TOKENS = 30  # discard tiny fragments


def estimate_tokens(text: str) -> int:
    """Rough token count from character length."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


def split_into_chunks(
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[str]:
    """Split *text* into chunks of approximately *max_tokens* with overlap.

    Returns a list of non-empty chunk strings.
    """
    text = text.strip()
    if not text:
        return []

    max_chars = max_tokens * _CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * _CHARS_PER_TOKEN
    min_chars = MIN_CHUNK_TOKENS * _CHARS_PER_TOKEN

    # Short document → single chunk
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    pos = 0

    while pos < len(text):
        end = min(pos + max_chars, len(text))

        # If not at the very end, find a clean break point
        if end < len(text):
            earliest = pos + max_chars // 2  # don't break in first half
            bp = _find_break(text, earliest, end)
            if bp > pos:
                end = bp

        chunk = text[pos:end].strip()
        if len(chunk) >= min_chars:
            chunks.append(chunk)

        # Advance with overlap (but never backwards)
        next_pos = end - overlap_chars if end < len(text) else len(text)
        if next_pos <= pos:
            next_pos = end  # force forward progress
        pos = next_pos

    return chunks


def _find_break(text: str, earliest: int, latest: int) -> int:
    """Find the best break point between *earliest* and *latest*.

    Preference: paragraph break > sentence end > word boundary.
    """
    # Paragraph break (double newline)
    idx = text.rfind("\n\n", earliest, latest)
    if idx != -1:
        return idx + 2

    # Sentence end (period/!/? followed by space)
    for pattern in (". ", "? ", "! "):
        idx = text.rfind(pattern, earliest, latest)
        if idx != -1:
            return idx + 2

    # Word boundary
    idx = text.rfind(" ", earliest, latest)
    if idx != -1:
        return idx + 1

    return latest
