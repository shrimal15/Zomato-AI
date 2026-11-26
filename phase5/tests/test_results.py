from app.models import Budget, Recommendation, RecommendationResult, Restaurant
from phase4 import RankResult
from phase5 import present, render_results, results_payload
from phase5.present import FALLBACK_NOTICE, NO_EXPLANATION


def _restaurant(**overrides: object) -> Restaurant:
    payload: dict[str, object] = {
        "id": "jalsa",
        "name": "Jalsa",
        "location": "Banashankari",
        "cuisines": ["North Indian", "Chinese"],
        "cost_for_two": 800,
        "budget": Budget.medium,
        "rating": 4.1,
        "votes": 10,
    }
    payload.update(overrides)
    return Restaurant(**payload)


def _card(**overrides: object) -> Recommendation:
    payload: dict[str, object] = {
        "id": "jalsa",
        "name": "Jalsa",
        "cuisines": ["North Indian", "Chinese"],
        "rating": 4.1,
        "cost_for_two": 800,
        "explanation": "Quick service fits this Chinese spot.",
    }
    payload.update(overrides)
    return Recommendation(**payload)


def _ranked(
    cards: list[Recommendation],
    *,
    summary: str | None = None,
    explanations_available: bool = True,
    empty_message: str | None = None,
    model_called: bool = True,
) -> RankResult:
    return RankResult(
        result=RecommendationResult(
            recommendations=cards,
            summary=summary,
            explanations_available=explanations_available,
            empty_message=empty_message,
        ),
        model_called=model_called,
    )


def test_each_card_shows_catalog_facts_cuisine_list_and_explanation():
    ranked = _ranked(
        [_card()],
        summary="One strong match.",
    )
    page = render_results(ranked)
    assert "Jalsa" in page
    assert "North Indian, Chinese" in page
    assert "Rating 4.1" in page
    assert "4.1/5" not in page
    assert "Estimated ₹800 for two" in page
    assert "Quick service fits this Chinese spot." in page
    assert page.count("One strong match.") == 1
    assert page.index("One strong match.") < page.index("<ol>")
    assert page.count("<li>") == 1
    assert "1 recommendation" in page
    assert "1 recommendations" not in page


def test_five_cards_stay_in_model_order_and_repeat_with_the_same_facts():
    cards = [
        _card(id=f"place-{index}", name=f"Place {index}", rating=4.0 + index / 10, cost_for_two=400 + index)
        for index in range(5, 0, -1)
    ]
    ranked = _ranked(cards, summary="Five nearby options.")
    first = present(ranked)
    second = present(ranked)
    assert [card.name for card in first.cards] == [f"Place {index}" for index in range(5, 0, -1)]
    assert [(card.id, card.rating, card.cost_for_two) for card in first.cards] == [
        (card.id, card.rating, card.cost_for_two) for card in second.cards
    ]
    page = render_results(ranked)
    assert page.count("<li>") == 5
    assert "5 recommendations" in page
    assert page.index("Place 5") < page.index("Place 1")


def test_summary_that_names_a_dropped_restaurant_is_omitted():
    kept = _card()
    dropped = _restaurant(id="spice", name="Spice Elephant", rating=4.4, cost_for_two=700)
    ranked = _ranked([kept], summary="Skip Spice Elephant and choose Jalsa.")
    view = present(ranked, known=[_restaurant(), dropped])
    page = render_results(ranked, known=[_restaurant(), dropped])
    payload = results_payload(ranked, known=[_restaurant(), dropped])
    assert view.summary is None
    assert "Spice Elephant" not in page
    assert "summary" not in payload
    assert payload["recommendations"][0]["name"] == "Jalsa"
    assert payload["recommendations"][0]["cost_for_two"] == 800


def test_summary_of_shown_restaurants_stays_above_the_list():
    ranked = _ranked([_card()], summary="Jalsa is the strongest match.")
    page = render_results(ranked, known=[_restaurant()])
    assert page.count("Jalsa is the strongest match.") == 1
    assert page.index("Jalsa is the strongest match.") < page.index("<ol>")


def test_empty_filter_names_the_filters_and_lists_no_restaurants():
    message = (
        "No restaurants match location Banashankari, cuisine Chinese, "
        "minimum rating 4.9, and budget high."
    )
    ranked = _ranked([], explanations_available=False, empty_message=message, model_called=False)
    page = render_results(ranked, known=[_restaurant(name="Should Not Appear")])
    payload = results_payload(ranked)
    assert message in page
    assert "Should Not Appear" not in page
    assert "<ol>" not in page
    assert payload["recommendations"] == []
    assert payload["empty_message"] == message
    assert payload["model_called"] is False
    assert "summary" not in payload


def test_fallback_shows_catalog_facts_and_says_there_is_no_explanation():
    ranked = _ranked(
        [_card(explanation=None, cost_for_two=450, rating=4.0)],
        explanations_available=False,
    )
    page = render_results(ranked)
    payload = results_payload(ranked)
    assert "Jalsa" in page
    assert "North Indian, Chinese" in page
    assert "Rating 4" in page
    assert "Estimated ₹450 for two" in page
    assert FALLBACK_NOTICE in page
    assert NO_EXPLANATION in page
    assert payload["explanations_available"] is False
    assert payload["recommendations"][0]["explanation"] is None
    assert payload["recommendations"][0]["cost_for_two"] == 450
    assert "summary" not in payload


def test_displayed_rating_and_cost_ignore_numbers_in_the_explanation():
    ranked = _ranked(
        [
            _card(
                explanation="People call it rated 4.9 and priced ₹1,200, but the fit is the cuisine.",
            )
        ]
    )
    page = render_results(ranked)
    assert "Rating 4.1" in page
    assert "Estimated ₹800 for two" in page
    assert "Rating 4.9" not in page
    assert "Estimated ₹1200" not in page
    assert "Estimated ₹1,200" not in page


def test_names_and_explanations_are_escaped():
    ranked = _ranked(
        [_card(name="<Jalsa>", explanation='<script>alert("x")</script>')],
        summary="<summary>",
    )
    page = render_results(ranked)
    assert "<Jalsa>" not in page
    assert "&lt;Jalsa&gt;" in page
    assert "<script>" not in page
    assert "&lt;summary&gt;" in page
