"""Turn model JSON into catalog-backed cards. Invalid output becomes a fallback."""

import json
import re
from collections.abc import Sequence

from app.config import RESULT_CAP
from app.models import Recommendation, RecommendationResult, Restaurant

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_RATING_CLAIM = re.compile(
    r"(?:rated|rating|stars?)\s*(?:of|is|at|:)?\s*(\d+(?:\.\d+)?)"
    r"|(\d+(?:\.\d+)?)\s*/\s*5"
    r"|(\d+(?:\.\d+)?)\s*stars?",
    re.IGNORECASE,
)
_COST_CLAIM = re.compile(
    r"(?:₹|(?<!\w)rs\.?|(?<!\w)inr)\s*(\d[\d,]*)"
    r"|(?:cost(?:\s+for\s+two)?|price|priced)\s*(?:of|is|at|:)?\s*"
    r"(?:₹|(?<!\w)rs\.?|(?<!\w)inr)?\s*(\d[\d,]*)",
    re.IGNORECASE,
)


def parse_ranking(raw: str, candidates: Sequence[Restaurant]) -> RecommendationResult | None:
    """Ground a model reply in the candidate list.

    Returns None when the reply cannot produce a single explained card.
    The caller then shows the Phase 3 order with catalog facts and no explanation.
    """
    payload = _load_object(raw)
    if payload is None:
        return None
    rows = payload.get("recommendations")
    if not isinstance(rows, list):
        return None

    by_id = {restaurant.id: restaurant for restaurant in candidates}
    chosen: list[Recommendation] = []
    seen: set[str] = set()
    for row in rows:
        if len(chosen) >= RESULT_CAP:
            break
        restaurant = _usable_row(row, by_id, seen)
        if restaurant is None:
            continue
        explanation = str(row["explanation"]).strip()
        if _explanation_contradicts(explanation, restaurant):
            continue
        seen.add(restaurant.id)
        chosen.append(Recommendation.from_restaurant(restaurant, explanation))

    if not chosen:
        return None

    summary = _summary(payload.get("summary"), chosen, candidates)
    return RecommendationResult(
        summary=summary,
        recommendations=chosen,
        explanations_available=True,
    )


def _usable_row(
    row: object,
    by_id: dict[str, Restaurant],
    seen: set[str],
) -> Restaurant | None:
    if not isinstance(row, dict):
        return None
    restaurant_id = row.get("id")
    explanation = row.get("explanation")
    if not isinstance(restaurant_id, str) or restaurant_id not in by_id:
        return None
    if restaurant_id in seen:
        return None
    if not isinstance(explanation, str) or not explanation.strip():
        return None
    return by_id[restaurant_id]


def _summary(
    value: object,
    chosen: Sequence[Recommendation],
    candidates: Sequence[Restaurant],
) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    kept_ids = {item.id for item in chosen}
    for restaurant in candidates:
        if restaurant.id in kept_ids:
            continue
        if _mentions(text, restaurant.id) or _mentions(text, restaurant.name):
            return None
    return text


def _mentions(text: str, needle: str) -> bool:
    cleaned = needle.strip()
    if not cleaned:
        return False
    pattern = rf"(?<!\w){re.escape(cleaned)}(?!\w)"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _explanation_contradicts(explanation: str, restaurant: Restaurant) -> bool:
    """True when the sentence states a rating or cost that is not the catalog value."""
    for claimed in _claimed_ratings(explanation):
        if round(claimed, 1) != round(restaurant.rating, 1):
            return True
    for claimed in _claimed_costs(explanation):
        if claimed != restaurant.cost_for_two:
            return True
    return False


def _claimed_ratings(text: str) -> list[float]:
    found: list[float] = []
    for match in _RATING_CLAIM.finditer(text):
        raw = next(group for group in match.groups() if group is not None)
        found.append(float(raw))
    return found


def _claimed_costs(text: str) -> list[int]:
    found: list[int] = []
    for match in _COST_CLAIM.finditer(text):
        raw = next(group for group in match.groups() if group)
        found.append(int(raw.replace(",", "")))
    return found


def _load_object(raw: str) -> dict[str, object] | None:
    text = _FENCE.sub("", raw.strip())
    value = _decode(text)
    if value is None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None
        value = _decode(text[start : end + 1])
    if not isinstance(value, dict):
        return None
    return value


def _decode(text: str) -> object | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
