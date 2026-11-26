"""HTML and JSON for the Phase 5 results list."""

from collections.abc import Sequence
from html import escape

from app.models import Restaurant
from phase4 import RankResult
from phase5.present import FALLBACK_NOTICE, NO_EXPLANATION, ResultCard, ResultsView, present


def render_results(
    ranked: RankResult,
    known: Sequence[Restaurant] | None = None,
) -> str:
    """Render the list the user scans. An empty filter names the filters that matched nothing."""
    return render_view(present(ranked, known))


def render_view(view: ResultsView) -> str:
    if not view.cards:
        return f'<section class="results"><p>{escape(view.empty_message or "")}</p></section>'

    summary = ""
    if view.summary:
        summary = f'<p class="summary">{escape(view.summary)}</p>'
    notice = ""
    if view.showing_fallback:
        notice = f'<p class="no-explanation">{escape(FALLBACK_NOTICE)}</p>'
    items = [_card_html(card, explained=view.explanations_available) for card in view.cards]
    count = len(view.cards)
    label = "recommendation" if count == 1 else "recommendations"
    return (
        '<section class="results">'
        f"<h2>{count} {label}</h2>"
        f"{summary}{notice}"
        f"<ol>{''.join(items)}</ol>"
        "</section>"
    )


def results_payload(
    ranked: RankResult,
    known: Sequence[Restaurant] | None = None,
) -> dict[str, object]:
    """JSON for the same list. Preference fields stay with the caller."""
    view = present(ranked, known)
    body: dict[str, object] = {
        "recommendations": [
            {
                "id": card.id,
                "name": card.name,
                "cuisines": list(card.cuisines),
                "rating": card.rating,
                "cost_for_two": card.cost_for_two,
                "explanation": card.explanation,
            }
            for card in view.cards
        ],
        "explanations_available": view.explanations_available,
        "model_called": view.model_called,
    }
    if view.summary:
        body["summary"] = view.summary
    if view.empty_message:
        body["empty_message"] = view.empty_message
    return body


def _card_html(card: ResultCard, explained: bool) -> str:
    cuisines = ", ".join(escape(name) for name in card.cuisines)
    if explained and card.explanation:
        reason = f'<p class="why">{escape(card.explanation)}</p>'
    else:
        reason = f'<p class="why no-explanation">{escape(NO_EXPLANATION)}</p>'
    return (
        "<li>"
        f"<strong>{escape(card.name)}</strong>"
        f'<p class="meta">{cuisines}</p>'
        f'<p class="meta">Rating {card.rating:g}</p>'
        f'<p class="meta">Estimated ₹{card.cost_for_two} for two</p>'
        f"{reason}"
        "</li>"
    )
