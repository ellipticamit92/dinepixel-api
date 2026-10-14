"""
Phase 1 MVP: Extract structured menu data from an image or PDF.

Usage:
    python extract.py path/to/menu.jpg
    python extract.py path/to/menu.pdf
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Union

from google.genai import types
from PIL import Image

from gemini_client import client, MODEL_NAME
from schemas import Menu, MenuItem
from prompts import EXTRACTION_PROMPT_V1

logger = logging.getLogger("extract")


_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # seconds, doubles each attempt


def _call_gemini(content: list) -> dict:
    last_error: Exception = RuntimeError("no attempts made")
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=content,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            finish_reason = response.candidates[0].finish_reason if response.candidates else "unknown"
            logger.info("gemini response status=ok finish_reason=%s", finish_reason)
            return json.loads(response.text)
        except Exception as e:
            last_error = e
            if any(code in str(e) for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                wait = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("gemini attempt=%d/%d retryable error=%s retrying in %ds", attempt + 1, _MAX_RETRIES, e, wait)
                time.sleep(wait)
                continue
            logger.error("gemini error=%s detail=%s", type(e).__name__, e)
            raise
    logger.error("gemini failed after %d attempts last_error=%s", _MAX_RETRIES, last_error)
    raise last_error


def extract_pdf(file_path: Path) -> dict:
    """Upload PDF via File API then pass the file reference to Gemini."""
    logger.info("uploading pdf via File API size_bytes=%d", file_path.stat().st_size)
    uploaded = client.files.upload(
        file=str(file_path),
        config=types.UploadFileConfig(mime_type="application/pdf"),
    )
    while uploaded.state.name == "PROCESSING":
        logger.info("pdf file_api state=PROCESSING, waiting...")
        time.sleep(3)
        uploaded = client.files.get(name=uploaded.name)
    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"File API upload failed: state={uploaded.state.name}")
    logger.info("pdf file_api state=ACTIVE uri=%s", uploaded.uri)
    try:
        return _call_gemini([EXTRACTION_PROMPT_V1, uploaded])
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass


def extract_image(file_path: Path) -> dict:
    """Resize if needed, then upload via File API and pass the reference to Gemini."""
    image = Image.open(file_path)
    max_width = 1600
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)), Image.LANCZOS)
        logger.info("resized image to %dx%d", image.width, image.height)
        image.save(file_path)

    suffix = file_path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    logger.info("uploading image via File API size_bytes=%d", file_path.stat().st_size)
    uploaded = client.files.upload(
        file=str(file_path),
        config=types.UploadFileConfig(mime_type=mime_type),
    )
    while uploaded.state.name == "PROCESSING":
        logger.info("image file_api state=PROCESSING, waiting...")
        time.sleep(3)
        uploaded = client.files.get(name=uploaded.name)
    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"File API upload failed: state={uploaded.state.name}")
    logger.info("image file_api state=ACTIVE uri=%s", uploaded.uri)
    try:
        return _call_gemini([EXTRACTION_PROMPT_V1, uploaded])
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass


def build_menu(raw: dict) -> Menu:
    """Build a validated Menu from a raw Gemini response dict."""
    all_items: list[MenuItem] = []
    restaurant_name = raw.get("restaurant_name") if isinstance(raw, dict) else None
    items_raw = raw.get("items", []) if isinstance(raw, dict) else raw

    for item_raw in items_raw:
        try:
            all_items.append(MenuItem.model_validate(item_raw))
        except Exception as e:
            logger.warning("skipping invalid item error=%s", e)

    logger.info("validated items=%d", len(all_items))
    return Menu(restaurant_name=restaurant_name, items=all_items)


def extract_menu(file_path: Union[str, Path]) -> Menu:
    """CLI entry point. Routes to extract_pdf or extract_image based on suffix."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    suffix = file_path.suffix.lower()
    logger.info("loading file=%s suffix=%s", file_path.name, suffix)

    try:
        raw = extract_pdf(file_path) if suffix == ".pdf" else extract_image(file_path)
    except Exception as e:
        logger.error("extraction failed error=%s", e)
        raise

    return build_menu(raw)

def print_summary(menu: Menu) -> None:
    print("\n" + "=" * 60)
    print(f"Restaurant: {menu.restaurant_name or 'Unknown'}")
    print(f"Total items: {menu.item_count}")
    print("=" * 60)
    for category, items in menu.by_category().items():
        print(f"\n[{category.upper()}] — {len(items)} items")
        for item in items[:3]:  # show first 3 per category
            price = f"₹{item.price}" if item.price else "N/A"
            print(f"  • {item.name} — {price}")
        if len(items) > 3:
            print(f"  ... and {len(items) - 3} more")


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract.py <path_to_menu.pdf_or_image>")
        sys.exit(1)

    file_path = sys.argv[1]
    menu = extract_menu(file_path)

    # Print human-readable summary
    print_summary(menu)

    # Save full JSON output
    output_path = Path(file_path).with_suffix(".extracted.json")
    output_path.write_text(menu.model_dump_json(indent=2))
    print(f"\n✓ Full output saved to {output_path}")


if __name__ == "__main__":
    main()
