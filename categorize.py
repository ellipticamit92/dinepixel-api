"""
Streaming menu item categorization using Groq (llama-3.3-70b).

Items are categorized in a single call, with the model instructed to emit
one JSON object per line (JSONL) so results can be parsed and yielded
incrementally as the response streams in.
"""

import json
from typing import Iterator

from groq_client import groq_client, GROQ_MODEL
from prompts import CATEGORIZATION_PROMPT_V1
from schemas import CategorizedItem, CategorizeItemIn


def categorize_items_stream(items: list[CategorizeItemIn]) -> Iterator[CategorizedItem]:
    """Stream categorized items from Groq as they're produced, one per JSONL line."""
    items_json = json.dumps([item.model_dump() for item in items], ensure_ascii=False)
    prompt = CATEGORIZATION_PROMPT_V1.format(items_json=items_json)

    buffer = ""
    stream = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        stream=True,
    )
    for chunk in stream:
        text = chunk.choices[0].delta.content or ""
        if not text:
            continue
        buffer += text
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
