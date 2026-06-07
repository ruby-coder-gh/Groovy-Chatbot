"""
Configuration loader for ISO 27001 chatbot.
Loads .env, configures Gemini SDK, and loads control_map.json.
Automatically adapts paths for Vercel serverless (uses /tmp for DB/PDFs).
"""

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env (local dev) or Vercel env vars
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables (.env or Vercel env)")

# Configure Gemini SDK
genai.configure(api_key=GEMINI_API_KEY)

# Load control map (read-only, bundled with code)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTROL_MAP_PATH = os.path.join(BASE_DIR, "data", "control_map.json")
with open(CONTROL_MAP_PATH) as f:
    CONTROL_MAP = json.load(f)

# ──────────────────────────────────────────────
# Path configuration — adapts for Vercel (/tmp/)
# ──────────────────────────────────────────────
ON_VERCEL = os.environ.get("VERCEL", "").lower() == "true"

if ON_VERCEL:
    # Vercel's /tmp/ is the only writable directory
    DB_PATH = os.path.join("/tmp", "iso27001.db")
    PDF_DIR = os.path.join("/tmp", "reports")
else:
    # Local development — use project-relative paths
    DB_PATH = os.path.join(BASE_DIR, "iso27001.db")
    PDF_DIR = os.path.join(BASE_DIR, "static", "reports")

os.makedirs(PDF_DIR, exist_ok=True)
