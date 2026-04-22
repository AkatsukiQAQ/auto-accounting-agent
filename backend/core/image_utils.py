from __future__ import annotations

import base64
import mimetypes


def image_to_data_url(path: str) -> str:
    """Read an image from disk and return a ``data:`` URL suitable for multimodal LLM prompts."""
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"
