"""LLM client using NVIDIA API (OpenAI-compatible)."""

from __future__ import annotations

import logging

from openai import OpenAI

import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about documents stored in SharePoint. "
    "Use ONLY the provided document context to answer. "
    "If the context does not contain the answer, say so clearly. "
    "Cite the source file name when possible."
)

MAX_CONTEXT_CHARS = 12_000

# Singleton client — reuse connection pool across requests
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )
    return _client


def ask(question: str, context_chunks: list[dict[str, str]]) -> str:
    """Send question + SharePoint context to NVIDIA LLM and return the answer.

    context_chunks: list of {"filename": ..., "text": ...}
    """
    # Build context block, truncating to stay within limits
    context_parts: list[str] = []
    total = 0
    for chunk in context_chunks:
        entry = f"--- {chunk['filename']} ---\n{chunk['text']}\n"
        if total + len(entry) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total
            if remaining > 200:
                context_parts.append(entry[:remaining] + "\n[...truncated]")
            break
        context_parts.append(entry)
        total += len(entry)

    context_block = "\n".join(context_parts) if context_parts else "(no documents found)"

    user_message = (
        f"## Documents from SharePoint\n\n{context_block}\n\n"
        f"## Question\n{question}"
    )

    client = _get_client()

    try:
        response = client.chat.completions.create(
            model=config.NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return response.choices[0].message.content or "(empty response)"
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        raise RuntimeError(f"LLM request failed: {exc}") from exc
