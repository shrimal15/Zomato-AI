"""Backend JSON API. It runs Phases 2–5 and does not render a page."""

from backend.api import RecommendationApi
from backend.server import serve

__all__ = ["RecommendationApi", "serve"]
