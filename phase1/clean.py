"""Turn raw Zomato rows into one catalog row per restaurant."""

import math
import re
from collections.abc import Iterable

from app.config import SOURCE_COLUMNS
from app.errors import EmptyCatalog
from app.identity import display_text, identity_key, register_identity
from app.models import Budget, BudgetThresholds, Restaurant
from app.rules import prefer_duplicate

_RATING = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:/\s*5)?\s*$")
_MISSING = {"", "nan", "none", "null"}


def _text(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    if text.lower() in _MISSING:
        return None
    return text


def parse_rating(value: object) -> float | None:
    """Parse values such as ``4.1/5``. Unclear or out-of-range ratings are dropped."""
    text = _text(value)
    if text is None or text.lower() == "new" or text == "-":
        return None
    match = _RATING.fullmatch(text)
    if match is None:
        return None
    rating = float(match.group(1))
    if rating < 0 or rating > 5:
        return None
    return rating


def parse_cost(value: object) -> int | None:
    """Parse a rupee amount. Commas are allowed. Anything else is dropped."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or not value.is_integer():
            return None
        number = int(value)
        return number if number >= 0 else None
    if isinstance(value, int):
        return value if value >= 0 else None
    text = _text(value)
    if text is None:
        return None
    digits = text.replace(",", "")
    if not digits.isdigit():
        return None
    return int(digits)


def parse_votes(value: object) -> int:
    parsed = parse_cost(value)
    return parsed if parsed is not None else 0


def parse_cuisines(value: object) -> list[str] | None:
    text = _text(value)
    if text is None:
        return None
    items = [part.strip() for part in text.split(",") if part.strip()]
    return items or None


def _optional_text(value: object) -> str:
    text = _text(value)
    return "" if text is None else text


def clean_row(raw: dict[str, object], seen_ids: dict[str, str]) -> Restaurant | None:
    """Return one restaurant, or None when the row cannot be used."""
    name = raw.get(SOURCE_COLUMNS["name"])
    address = raw.get(SOURCE_COLUMNS["address"])
    if not isinstance(name, str) or not isinstance(address, str):
        return None
    if identity_key(name, address) is None:
        return None

    rating = parse_rating(raw.get(SOURCE_COLUMNS["rate"]))
    cost = parse_cost(raw.get(SOURCE_COLUMNS["cost"]))
    cuisines = parse_cuisines(raw.get(SOURCE_COLUMNS["cuisines"]))
    location = _optional_text(raw.get(SOURCE_COLUMNS["location"]))
    if rating is None or cost is None or not cuisines or not location:
        return None

    restaurant_id = register_identity(seen_ids, name, address)
    return Restaurant(
        id=restaurant_id,
        name=display_text(name),
        location=location,
        cuisines=cuisines,
        cost_for_two=cost,
        budget=Budget.low,
        rating=rating,
        votes=parse_votes(raw.get(SOURCE_COLUMNS["votes"])),
        rest_type=_optional_text(raw.get(SOURCE_COLUMNS["rest_type"])),
        dish_liked=_optional_text(raw.get(SOURCE_COLUMNS["dish_liked"])),
        online_order=_optional_text(raw.get(SOURCE_COLUMNS["online_order"])),
        book_table=_optional_text(raw.get(SOURCE_COLUMNS["book_table"])),
    )


def budget_thresholds(costs: list[int]) -> BudgetThresholds:
    """Split the cleaned cost distribution into low, medium, and high.

    The boundary belongs to the lower band. The same costs always produce the
    same thresholds.
    """
    if not costs:
        raise EmptyCatalog("Cleaning produced no restaurants.")
    ordered = sorted(costs)
    count = len(ordered)
    if count < 3:
        low_index = 0
        medium_index = 0
    else:
        low_index = count // 3 - 1
        medium_index = (2 * count) // 3 - 1
    low_max = ordered[low_index]
    medium_max = ordered[max(low_index, medium_index)]
    if low_max >= medium_max:
        higher = next((cost for cost in ordered if cost > low_max), None)
        medium_max = higher if higher is not None else low_max + 1
    return BudgetThresholds(low_max=low_max, medium_max=medium_max)


def build_catalog(rows: Iterable[dict[str, object]]) -> tuple[list[Restaurant], BudgetThresholds]:
    """Clean and deduplicate rows. One name and address becomes one restaurant."""
    kept: dict[str, Restaurant] = {}
    seen_ids: dict[str, str] = {}
    for raw in rows:
        restaurant = clean_row(raw, seen_ids)
        if restaurant is None:
            continue
        current = kept.get(restaurant.id)
        kept[restaurant.id] = restaurant if current is None else prefer_duplicate(current, restaurant)
    if not kept:
        raise EmptyCatalog("Cleaning produced no restaurants.")
    ordered = sorted(kept.values(), key=lambda restaurant: restaurant.id)
    thresholds = budget_thresholds([restaurant.cost_for_two for restaurant in ordered])
    restaurants = [
        restaurant.model_copy(update={"budget": thresholds.band_for(restaurant.cost_for_two)})
        for restaurant in ordered
    ]
    return restaurants, thresholds
