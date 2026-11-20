"""Async Ollama HTTP client for Seabot."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Default generation options
_DEFAULT_OPTIONS: dict[str, Any] = {
    "temperature": 0.1,
    "top_p": 0.9,
    "repeat_penalty": 1.15,
    "num_predict": 1024,
    "num_ctx": 8192,
}


def _base_url() -> str:
    return get_settings().OLLAMA_BASE_URL.rstrip("/")


# ---------------------------------------------------------------------------
# Streaming generation
# ---------------------------------------------------------------------------

async def generate_stream(
    model: str,
    prompt: str,
    images: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream tokens from Ollama /api/generate.

    Args:
        model: Ollama model name.
        prompt: Full prompt string.
        images: Optional list of base64-encoded PNG strings for multimodal input.

    Yields:
        Individual content token strings as they arrive.
    """
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": _DEFAULT_OPTIONS,
    }
    if images:
        payload["images"] = images

    url = f"{_base_url()}/api/generate"
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        data = json.loads(raw_line)
                    except json.JSONDecodeError:
                        logger.warning("Could not parse Ollama NDJSON line: %r", raw_line)
                        continue
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
    except httpx.RequestError as exc:
        logger.error("Ollama stream request error: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Non-streaming generation (collects full response)
# ---------------------------------------------------------------------------

async def generate(
    model: str,
    prompt: str,
    images: list[str] | None = None,
) -> str:
    """Call Ollama and return the complete generated text.

    Args:
        model: Ollama model name.
        prompt: Full prompt string.
        images: Optional list of base64-encoded PNG strings.

    Returns:
        Full generated string.
    """
    full_text: list[str] = []
    async for token in generate_stream(model, prompt, images=images):
        full_text.append(token)
    return "".join(full_text)


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

async def embed(model: str, texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts via Ollama /api/embeddings.

    Args:
        model: Embedding model name (e.g. nomic-embed-text).
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors, one per input text.
    """
    url = f"{_base_url()}/api/embeddings"
    embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for text in texts:
            payload = {"model": model, "prompt": text}
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding", [])
                embeddings.append(embedding)
            except httpx.RequestError as exc:
                logger.error("Ollama embed request error for text slice: %s", exc)
                raise
    return embeddings


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def health_check() -> bool:
    """Return True if Ollama is reachable (GET /api/tags succeeds)."""
    url = f"{_base_url()}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.status_code == 200
    except httpx.RequestError:
        return False
