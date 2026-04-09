"""Vision client — describe images and video frames via NVIDIA vision API."""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

from openai import OpenAI

import config

logger = logging.getLogger(__name__)


def _get_vision_model() -> str:
    return config.NVIDIA_VISION_MODEL
_MAX_FRAMES = 4  # max video frames to describe

# Singleton client — reuse connection pool across vision requests
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )
    return _client


def _b64_data_url(raw: bytes, mime: str) -> str:
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _describe_single_image(client: OpenAI, data_url: str, prompt: str) -> str:
    """Send one image to the vision model and return its description."""
    resp = client.chat.completions.create(
        model=_get_vision_model(),
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        max_tokens=300,
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


# ── Public API ──────────────────────────────────────────────────────────

def describe_image(name: str, raw: bytes) -> str:
    """Return a text description of an image file."""
    lower = name.lower()
    if lower.endswith(".png"):
        mime = "image/png"
    elif lower.endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    elif lower.endswith(".gif"):
        mime = "image/gif"
    elif lower.endswith(".webp"):
        mime = "image/webp"
    elif lower.endswith(".bmp"):
        mime = "image/bmp"
    else:
        mime = "image/png"

    try:
        data_url = _b64_data_url(raw, mime)
        client = _get_client()
        description = _describe_single_image(
            client,
            data_url,
            "Describe this image in detail. Include all visible text, diagrams, "
            "charts, labels, and any meaningful content. Be thorough.",
        )
        return f"[Image: {name}]\n{description}"
    except Exception as exc:
        logger.warning("Vision API failed for image %s: %s", name, exc)
        return f"[Image file: {name} — could not describe]"


def describe_video(name: str, raw: bytes) -> str:
    """Extract key frames from a video and describe them."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("opencv-python not installed — cannot process video %s", name)
        return f"[Video file: {name} — install opencv-python for frame extraction]"

    try:
        # Write to temp buffer and open with cv2
        import tempfile
        import os

        suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        try:
            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                return f"[Video file: {name} — could not open video]"

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            duration_sec = total_frames / fps if fps > 0 else 0

            # Pick evenly spaced frames
            num_frames = min(_MAX_FRAMES, max(1, total_frames // 30))
            if total_frames <= 0:
                cap.release()
                return f"[Video file: {name} — empty video, duration: 0s]"

            indices = [int(i * total_frames / (num_frames + 1)) for i in range(1, num_frames + 1)]

            client = _get_client()
            descriptions: list[str] = []

            for idx, frame_num in enumerate(indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if not ret:
                    continue

                # Resize if too large (keep under 1MB encoded)
                h, w = frame.shape[:2]
                max_dim = 768
                if max(h, w) > max_dim:
                    scale = max_dim / max(h, w)
                    frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                data_url = _b64_data_url(buf.tobytes(), "image/jpeg")

                timestamp = round(frame_num / fps, 1) if fps > 0 else 0
                desc = _describe_single_image(
                    client,
                    data_url,
                    f"This is frame at {timestamp}s from a video called '{name}'. "
                    "Describe what you see — people, text, diagrams, actions, scenes.",
                )
                descriptions.append(f"[{timestamp}s] {desc}")

            cap.release()
        finally:
            os.unlink(tmp_path)

        header = f"[Video: {name} | duration: {round(duration_sec, 1)}s | {num_frames} frames analyzed]"
        body = "\n\n".join(descriptions) if descriptions else "No frames could be extracted."
        return f"{header}\n{body}"

    except Exception as exc:
        logger.warning("Video processing failed for %s: %s", name, exc)
        return f"[Video file: {name} — processing error]"
