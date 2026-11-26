"""Pure matching and ordering rules. These do not load the dataset."""

from app.config import CANDIDATE_CAP, RESULT_CAP
from app.errors import InvalidPreference
from app.models import Budget, BudgetThresholds, Preferences, Restaurant


def resolve_catalog_value(raw: str, known_values: set[str], field_name: str) -> str:
    """Map user text to the catalog spelling. Matching is case-insensitive equality."""
    if raw is None or not str(raw).strip():
        raise InvalidPreference(f"{field_name} is required")
    needle = str(raw).strip().casefold()
    for value in known_values:
        if value.strip().casefold() == needle:
            return value.strip()
    raise InvalidPreference(f"{field_name} {raw.strip()!r} is not in the catalog")


def cuisine_matches(cuisines: list[str], requested: str) -> bool:
    """True when requested equals one cuisine item. Substrings do not match."""
    needle = requested.strip().casefold()
    if not needle:
        return False
    return any(item.strip().casefold() == needle for item in cuisines)


def location_matches(location: str, requested: str) -> bool:
    return location.strip().casefold() == requested.strip().casefold()


def rating_meets_minimum(rating: float, minimum: float) -> bool:
    return rating >= minimum


def cost_in_budget(cost: int, budget: Budget, thresholds: BudgetThresholds) -> bool:
    return thresholds.band_for(cost) == budget


def rating_in_catalog_range(
    min_rating: float, catalog_min: float, catalog_max: float
) -> None:
    """Reject a minimum rating outside the ratings that remain after cleaning."""
    if min_rating < catalog_min or min_rating > catalog_max:
        raise InvalidPreference(
            f"min_rating {min_rating} is outside the catalog range "
            f"{catalog_min} to {catalog_max}"
        )


def candidate_sort_key(restaurant: Restaurant) -> tuple[float, int, str]:
    """Rating, then votes, then id. Lower keys sort first."""
    return (-restaurant.rating, -restaurant.votes, restaurant.id)


def cap_candidates(
    restaurants: list[Restaurant], limit: int = CANDIDATE_CAP
) -> list[Restaurant]:
    """Return the top rows for the model. Short lists are not padded."""
    if limit < 1:
        raise ValueError("candidate cap must be at least 1")
    ordered = sorted(restaurants, key=candidate_sort_key)
    return ordered[:limit]


def cap_results(restaurants: list[Restaurant], limit: int = RESULT_CAP) -> list[Restaurant]:
    if limit < 1:
        raise ValueError("result cap must be at least 1")
    return restaurants[:limit]


def prefer_duplicate(current: Restaurant, incoming: Restaurant) -> Restaurant:
    """Keep the duplicate with more votes, then the higher rating."""
    if incoming.votes > current.votes:
        return incoming
    if incoming.votes < current.votes:
        return current
    if incoming.rating > current.rating:
        return incoming
    return current


def empty_filter_message(preferences: Preferences) -> str:
    budget = preferences.budget.value
    return (
        "No restaurants match "
        f"location {preferences.location}, "
        f"cuisine {preferences.cuisine}, "
        f"minimum rating {preferences.min_rating}, "
        f"and budget {budget}."
    )
