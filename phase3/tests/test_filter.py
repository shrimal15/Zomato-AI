import pytest

from app.config import CANDIDATE_CAP, EXCLUDED_SOURCE_COLUMNS
from app.models import Budget, BudgetThresholds, Preferences, Restaurant
from phase1.store import Catalog
from phase3 import filter_candidates


def place(**overrides: object) -> Restaurant:
    payload: dict[str, object] = {
        "id": "jalsa",
        "name": "Jalsa",
        "location": "Banashankari",
        "cuisines": ["North Indian", "Chinese"],
        "cost_for_two": 500,
        "budget": Budget.low,
        "rating": 4.1,
        "votes": 10,
    }
    payload.update(overrides)
    return Restaurant(**payload)


def catalog_of(*restaurants: Restaurant) -> Catalog:
    return Catalog(list(restaurants), BudgetThresholds(low_max=500, medium_max=1000))


def preferences(**overrides: object) -> Preferences:
    payload: dict[str, object] = {
        "location": "Banashankari",
        "budget": "low",
        "cuisine": "Chinese",
        "min_rating": 4.1,
    }
    payload.update(overrides)
    return Preferences.model_validate(payload)


def test_filters_keep_only_full_matches():
    catalog = catalog_of(
        place(),
        place(id="spice", name="Spice", location="Basavanagudi"),
        place(id="north", name="North", cuisines=["North Indian"]),
        place(id="lower", name="Lower", rating=4.09),
        place(id="medium", name="Medium", cost_for_two=501, budget=Budget.medium),
        place(id="edge", name="Edge", cost_for_two=1000, budget=Budget.medium, rating=4.5, votes=1),
        place(id="high", name="High", cost_for_two=1001, budget=Budget.high, rating=4.8, votes=1),
    )
    low = filter_candidates(preferences(), catalog)
    assert [item.name for item in low.candidates] == ["Jalsa"]
    assert low.model_called is False
    medium = filter_candidates(preferences(budget="medium", min_rating=0), catalog)
    assert {item.cost_for_two for item in medium.candidates} == {501, 1000}
    high = filter_candidates(preferences(budget="high", min_rating=0), catalog)
    assert [item.cost_for_two for item in high.candidates] == [1001]


def test_empty_results_do_not_call_the_model():
    catalog = catalog_of(
        place(),
        place(id="other", name="Other", location="Basavanagudi", cuisines=["Italian"]),
    )
    missing_here = filter_candidates(preferences(cuisine="Italian"), catalog)
    too_high = filter_candidates(preferences(min_rating=4.2), catalog)
    wrong_band = filter_candidates(preferences(budget="high"), catalog)
    for result in (missing_here, too_high, wrong_band):
        assert result.candidates == ()
        assert result.model_called is False
        assert result.empty_message()
        assert "Banashankari" in result.empty_message()


def test_notes_do_not_change_the_filters():
    catalog = catalog_of(
        place(id="high", name="High Place", cost_for_two=1200, budget=Budget.high, rating=4.4),
        place(),
    )
    cheap_note = filter_candidates(
        preferences(budget="high", min_rating=4, notes="cheap"),
        catalog,
    )
    assert [item.name for item in cheap_note.candidates] == ["High Place"]
    other_place = filter_candidates(
        preferences(notes="Only show Basavanagudi"),
        catalog,
    )
    assert [item.location for item in other_place.candidates] == ["Banashankari"]


def test_cap_orders_by_rating_then_votes_then_id():
    tied = [
        place(id=f"{index:02d}", name=f"Place {index}", rating=4.0, votes=10)
        for index in range(CANDIDATE_CAP + 1)
    ]
    ranked = place(id="top", name="Top", rating=4.9, votes=1)
    popular = place(id="popular", name="Popular", rating=3.0, votes=500)
    short = filter_candidates(preferences(min_rating=0), catalog_of(ranked, popular))
    assert [item.name for item in short.candidates] == ["Top", "Popular"]
    capped = filter_candidates(preferences(min_rating=0), catalog_of(*tied))
    again = filter_candidates(preferences(min_rating=0), catalog_of(*tied))
    assert len(capped.candidates) == CANDIDATE_CAP
    assert [item.id for item in capped.candidates] == [f"{index:02d}" for index in range(CANDIDATE_CAP)]
    assert [item.id for item in again.candidates] == [item.id for item in capped.candidates]


def test_prompt_payload_omits_private_fields():
    result = filter_candidates(preferences(), catalog_of(place(dish_liked="")))
    payload = result.prompt_rows()[0]
    assert "dish_liked" not in payload
    for column in EXCLUDED_SOURCE_COLUMNS:
        assert column not in payload
    assert payload["name"] == "Jalsa"
    assert payload["cost_for_two"] == 500
    assert payload["rating"] == 4.1
