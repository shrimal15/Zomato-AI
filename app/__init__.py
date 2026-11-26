"""Restaurant recommendation foundations.

Phase 1 catalog cleaning is not implemented here. Import the contracts,
identity rules, and matching rules from this package when that work starts.
"""

from app.config import CANDIDATE_CAP, CATALOG_PATH, DATASET_ID, RESULT_CAP
from app.errors import CatalogUnavailable, EmptyCatalog, IdentityCollision, InvalidPreference
from app.models import (
    Budget,
    BudgetThresholds,
    Preferences,
    Recommendation,
    RecommendationResult,
    Restaurant,
)

__all__ = [
    "Budget",
    "BudgetThresholds",
    "CANDIDATE_CAP",
    "CATALOG_PATH",
    "CatalogUnavailable",
    "DATASET_ID",
    "EmptyCatalog",
    "IdentityCollision",
    "InvalidPreference",
    "Preferences",
    "RESULT_CAP",
    "Recommendation",
    "RecommendationResult",
    "Restaurant",
]
