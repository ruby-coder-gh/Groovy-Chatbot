"""
Configuration loader for ISO 27001 chatbot.
Loads .env, configures Gemini SDK, and loads control_map.json.
"""

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Configure Gemini SDK
genai.configure(api_key=GEMINI_API_KEY)

# Load control map
CONTROL_MAP_PATH = os.path.join(os.path.dirname(__file__), "data", "control_map.json")
with open(CONTROL_MAP_PATH) as f:
    CONTROL_MAP = json.load(f)

# Database path
DB_DIR = os.path.join(os.path.dirname(__file__), "db")
DB_PATH = os.path.join(os.path.dirname(__file__), "iso27001.db")

# PDF output directory
PDF_DIR = os.path.join(os.path.dirname(__file__), "static", "reports")
os.makedirs(PDF_DIR, exist_ok=True)
