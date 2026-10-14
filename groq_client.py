"""
Groq client for fast, free LLM inference (text-only tasks).
Used for categorization to reduce Gemini dependency.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set. Add GROQ_API_KEY=<your_key> to .env")

groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"
