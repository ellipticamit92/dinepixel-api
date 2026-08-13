"""
Phase 1 MVP: Extract structured menu data from an image or PDF.
 
Usage:
    python extract.py path/to/menu.jpg
    python extract.py path/to/menu.pdf
"""

import os
import sys 
import json
from pathlib import Path
from typing import Optional, Union

import google.generativeai as genai
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PIL import Image

from schemas import Menu, MenuItem
from prompts import EXTRACTION_PROMPT_V1


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not set. Create a .env file with GEMINI_API_KEY=your_key"
    )
 
genai.configure(api_key=GEMINI_API_KEY)
 
MODEL_NAME = "gemini-flash-latest"  # change to gemini-2.5-pro for higher accuracy

def load_images(file_path: Path) -> list[Image.Image]:
    """Load one or more images from an image file or PDF."""
    suffix = file_path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return [Image.open(file_path)]
    if suffix == ".pdf":
        # Higher DPI = better OCR but slower and more tokens
        return convert_from_path(file_path, dpi=200)
    raise ValueError(f"Unsupported file type: {suffix}")


def extract_from_image(image: Image.Image) -> dict:
    """Send one image to Gemini and get back parsed JSON."""
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "temperature": 0.1,  # low temp = more consistent extraction
            "response_mime_type": "application/json",  # forces JSON output
        },
    )
    response = model.generate_content([EXTRACTION_PROMPT_V1, image])
    return json.loads(response.text)

def extract_menu(file_path: Union[str, Path]) -> Menu:
    """Main entry point. Extract a structured Menu from a file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)
 
    print(f"[1/3] Loading {file_path.name}...")
    images = load_images(file_path)
    print(f"      Loaded {len(images)} page(s)")
 
    all_items: list[MenuItem] = []
    restaurant_name = None
 
    for i, img in enumerate(images, start=1):
        print(f"[2/3] Extracting page {i}/{len(images)}...")
        try:
            raw = extract_from_image(img)
        except Exception as e:
            print(f"      Page {i} failed: {e}")
            continue
 
        # The model might return {"items": [...]} or a raw list
        if isinstance(raw, dict):
            restaurant_name = restaurant_name or raw.get("restaurant_name")
            items_raw = raw.get("items", [])
        else:
            items_raw = raw
 
        for item_raw in items_raw:
            try:
                item = MenuItem.model_validate(item_raw)
                all_items.append(item)
            except Exception as e:
                print(f"      Skipping invalid item: {e}")
 
    print(f"[3/3] Validating {len(all_items)} items...")
    menu = Menu(restaurant_name=restaurant_name, items=all_items)
    return menu

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
    