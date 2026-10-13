"""
Streaming menu item categorization using Gemini.

Items are categorized in a single Gemini call, but the model is instructed to
emit one JSON object per line (JSONL) so results can be parsed and yielded
incrementally as the response streams in, rather than waiting for the full
batch to complete.
"""

import json
from typing import Iterator

from google.genai import types

from gemini_client import client, MODEL_NAME
from prompts import CATEGORIZATION_PROMPT_V1
from schemas import CategorizedItem, CategorizeItemIn


def categorize_items_stream(items: list[CategorizeItemIn]) -> Iterator[CategorizedItem]:
    """Stream categorized items from Gemini as they're produced, one per JSONL line."""
    items_json = json.dumps([item.model_dump() for item in items], ensure_ascii=False)
    prompt = CATEGORIZATION_PROMPT_V1.format(items_json=items_json)

    buffer = ""
    for chunk in client.models.generate_content_stream(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    ):
        if not chunk.text:
            continue
        buffer += chunk.text
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                yield CategorizedItem.model_validate(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue

    line = buffer.strip()
    if line:
        try:
            yield CategorizedItem.model_validate(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            pass
