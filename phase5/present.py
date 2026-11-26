"""Turn a Phase 4 ranking into the short list Phase 5 shows."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.config import RESULT_CAP
from app.models import Restaurant
from phase4 import RankResult

FALLBACK_NOTICE = "These matches use catalog facts. An AI explanation was not produced."
NO_EXPLANATION = "No AI explanation was produced."


@dataclass(frozen=True)
class ResultCard:
    """One scannable restaurant. Facts are the catalog values already on the ranking."""

    id: str
    name: str
    cuisines: tuple[str, ...]
    rating: float
    cost_for_two: int
    explanation: str | None


@dataclass(frozen=True)
class ResultsView:
    """What the user sees. Cards are the ranked list only, never the full shortlist."""

    cards: tuple[ResultCard, ...]
    summary: str | None
    empty_message: str | None
    explanations_available: bool
    model_called: bool

    @property
    def showing_fallback(self) -> bool:
        return bool(self.cards) and not self.explanations_available


def present(
    ranked: RankResult,
    known: Sequence[Restaurant] | None = None,
) -> ResultsView:
    """Keep at most five cards and drop a summary that names a restaurant not on that list."""
    result = ranked.result
    cards = tuple(
        ResultCard(
            id=item.id,
            name=item.name,
            cuisines=tuple(item.cuisines),
            rating=item.rating,
            cost_for_two=item.cost_for_two,
            explanation=item.explanation,
        )
        for item in result.recommendations[:RESULT_CAP]
    )
    summary = result.summary if result.explanations_available else None
    return ResultsView(
        cards=cards,
        summary=_visible_summary(summary, cards, known),
        empty_message=result.empty_message if not cards else None,
        explanations_available=result.explanations_available and bool(cards),
        model_called=ranked.model_called,
    )


def _visible_summary(
    summary: str | None,
    cards: Sequence[ResultCard],
    known: Sequence[Restaurant] | None,
) -> str | None:
    if summary is None:
        return None
    text = summary.strip()
    if not text or not cards:
        return None
    shown = {card.id for card in cards}
    for restaurant in known or ():
        if restaurant.id in shown:
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
