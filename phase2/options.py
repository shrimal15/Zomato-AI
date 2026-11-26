"""Location, cuisine, and rating choices taken from the catalog."""

from dataclasses import dataclass

from app.models import Budget
from phase1.store import Catalog


@dataclass(frozen=True)
class PreferenceOptions:
    locations: tuple[str, ...]
    cuisines: tuple[str, ...]
    rating_min: float
    rating_max: float
    budgets: tuple[str, ...] = tuple(band.value for band in Budget)


def options_for(catalog: Catalog) -> PreferenceOptions:
    ratings = [restaurant.rating for restaurant in catalog.restaurants]
    return PreferenceOptions(
        locations=tuple(sorted(catalog.locations(), key=str.casefold)),
        cuisines=tuple(sorted(catalog.cuisines(), key=str.casefold)),
        rating_min=min(ratings),
        rating_max=max(ratings),
    )
