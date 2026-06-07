"""
Vercel serverless entry point for the ISO 27001 chatbot Flask app.

This file bridges the Flask application to Vercel's Python runtime.
Vercel looks for a WSGI callable named `app` in this module.
"""

import sys
import os

# Add project root to the Python path so imports work
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Signal to the app that it's running on Vercel
os.environ.setdefault("VERCEL", "true")
# Ensure Flask debug is off in production
os.environ.setdefault("FLASK_DEBUG", "0")

# Import the Flask app — this triggers config.py and init_db()
from app import app

# Vercel's Python runtime expects a WSGI callable named `app`
# Flask's app object is already WSGI-compatible, so we just re-export it.
