"""Paths, dataset columns, and limits fixed before Phase 1."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CATALOG_PATH = DATA_DIR / "restaurants.parquet"
THRESHOLDS_PATH = DATA_DIR / "budget_thresholds.json"
RAW_DATASET_PATH = DATA_DIR / "raw" / "zomato.csv"

DATASET_ID = "ManikaSaini/zomato-restaurant-recommendation"

# Phase 3 sends at most this many rows to the model.
CANDIDATE_CAP = 20
# Phase 4 and Phase 5 show at most this many restaurants.
RESULT_CAP = 5
NOTES_MAX_LENGTH = 500

RATING_MIN = 0.0
RATING_MAX = 5.0

UI_HOST = "127.0.0.1"
UI_PORT = 8000


def _api_bind() -> tuple[str, int]:
    """Local runs stay on localhost. Render sets PORT and must be reachable on all interfaces."""
    raw_port = os.environ.get("PORT", os.environ.get("API_PORT", str(UI_PORT)))
    try:
        port = int(raw_port)
    except ValueError:
        port = UI_PORT
    host = os.environ.get("API_HOST")
    if not host:
        host = "0.0.0.0" if "PORT" in os.environ else UI_HOST
    return host, port


API_HOST, API_PORT = _api_bind()
# Comma-separated browser origins allowed to call the API.
# Local default is the Next.js dev server. Production sets the Vercel URL.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://127.0.0.1:3000")

# Columns Phase 1 may read. reviews_list and menu_item are intentionally absent.
SOURCE_COLUMNS = {
    "name": "name",
    "address": "address",
    "location": "location",
    "cuisines": "cuisines",
    "cost": "approx_cost(for two people)",
    "rate": "rate",
    "votes": "votes",
    "rest_type": "rest_type",
    "dish_liked": "dish_liked",
    "online_order": "online_order",
    "book_table": "book_table",
}

# Never written to the catalog and never sent to the model.
EXCLUDED_SOURCE_COLUMNS = (
    "url",
    "phone",
    "reviews_list",
    "menu_item",
    "listed_in(type)",
    "listed_in(city)",
)
