"""CampusAI configuration: categories, routing and staff accounts.

Change the PINs below before using this in a real campus.
"""

import os

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", 8000))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "campusai.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

CATEGORIES = ["Discipline", "Cleanliness", "Infrastructure"]
STATUSES = ["pending", "in-progress", "resolved"]

# Which staff member receives which category
ROUTING = {
    "Discipline": "discipline_head",
    "Cleanliness": "peon_incharge",
    "Infrastructure": "director",
}

# Staff accounts (role -> display name, PIN)
STAFF = {
    "discipline_head": {"name": "Discipline Head", "pin": "1111", "category": "Discipline"},
    "peon_incharge": {"name": "Peon In-charge", "pin": "2222", "category": "Cleanliness"},
    "director": {"name": "Director", "pin": "3333", "category": "Infrastructure"},
}

# Optional: set ANTHROPIC_API_KEY in your environment to use Claude for analysis.
# Without it, the built-in rule based AI analyzer is used (works offline).
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-5-5"

MAX_PHOTO_BYTES = 5 * 1024 * 1024
