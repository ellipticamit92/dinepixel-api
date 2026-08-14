"""
Shared Gemini client configuration.
"""

import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not set. Create a .env file with GEMINI_API_KEY=your_key"
    )

genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-flash-latest"  # change to gemini-2.5-pro for higher accuracy
