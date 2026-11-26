"""Rank a Phase 3 shortlist. An empty shortlist never calls the model."""

from dataclasses import dataclass
from typing import Protocol

from app.models import Recommendation, RecommendationResult
from app.rules import cap_results, empty_filter_message
from phase3 import FilterResult
from phase4.groq_client import GroqClient
from phase4.parse import parse_ranking
from phase4.prompt import build_messages


class ChatClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Return the model text. Raise on timeout, auth, or transport failure."""


@dataclass(frozen=True)
class RankResult:
    result: RecommendationResult
    model_called: bool


def rank(filter_result: FilterResult, client: ChatClient | None = None) -> RankResult:
    """Ask Groq to order the shortlist. Failure returns up to five catalog cards."""
    if not filter_result.candidates:
        return RankResult(result=_empty_result(filter_result), model_called=False)

    ranker = client if client is not None else GroqClient()
    try:
        raw = ranker.complete(build_messages(filter_result))
    except Exception:
        return RankResult(result=_fallback_result(filter_result), model_called=True)

    parsed = parse_ranking(raw, filter_result.candidates)
    if parsed is None:
        return RankResult(result=_fallback_result(filter_result), model_called=True)
    return RankResult(result=parsed, model_called=True)


def _fallback_result(filter_result: FilterResult) -> RecommendationResult:
    chosen = cap_results(list(filter_result.candidates))
    return RecommendationResult(
        recommendations=[
            Recommendation.from_restaurant(restaurant, None) for restaurant in chosen
        ],
        explanations_available=False,
    )


def _empty_result(filter_result: FilterResult) -> RecommendationResult:
    message = filter_result.empty_message() or empty_filter_message(filter_result.preferences)
    return RecommendationResult(
        recommendations=[],
        explanations_available=False,
        empty_message=message,
    )
