"""Filter the catalog down to a capped shortlist. This phase does not call a model."""

from dataclasses import dataclass

from app.rules import cap_candidates, empty_filter_message
from app.models import Preferences, Restaurant
from phase1.store import Catalog


@dataclass(frozen=True)
class FilterResult:
    """Candidates for a later ranking step. model_called stays false."""

    preferences: Preferences
    candidates: tuple[Restaurant, ...]

    @property
    def model_called(self) -> bool:
        return False

    def prompt_rows(self) -> list[dict[str, object]]:
        """Restaurant contract fields only. Phone, URL, address, reviews, and menu stay out."""
        return [restaurant.to_prompt_dict() for restaurant in self.candidates]

    def empty_message(self) -> str | None:
        if self.candidates:
            return None
        return empty_filter_message(self.preferences)


def filter_candidates(preferences: Preferences, catalog: Catalog) -> FilterResult:
    """Apply location, cuisine, rating, and budget, then cap the list.

    Notes never change those four filters. An empty list is returned as-is.
    """
    matches = catalog.lookup(
        preferences.location,
        preferences.cuisine,
        preferences.min_rating,
        preferences.budget,
    )
    return FilterResult(
        preferences=preferences,
        candidates=tuple(cap_candidates(matches)),
    )
