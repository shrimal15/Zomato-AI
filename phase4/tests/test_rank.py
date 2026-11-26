import json

import pytest

from app.models import Budget, Preferences, Restaurant
from phase3 import FilterResult
from phase4.groq_client import GroqError
from phase4.prompt import build_messages
from phase4.rank import rank


def place(**overrides: object) -> Restaurant:
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


def preferences(**overrides: object) -> Preferences:
    payload: dict[str, object] = {
        "location": "Banashankari",
        "budget": "medium",
        "cuisine": "Chinese",
        "min_rating": 4,
    }
    payload.update(overrides)
    return Preferences.model_validate(payload)


def shortlist(*restaurants: Restaurant, **preference_overrides: object) -> FilterResult:
    return FilterResult(
        preferences=preferences(**preference_overrides),
        candidates=restaurants,
    )


def reply(rows: list[dict[str, object]], summary: object | None = None) -> str:
    payload: dict[str, object] = {"recommendations": rows}
    if summary is not None:
        payload["summary"] = summary
    return json.dumps(payload)


class Scripted:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.calls = 0

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        self.messages = messages
        return self.raw


def test_model_order_is_kept_and_facts_come_from_the_catalog():
    restaurants = [
        place(id=f"place-{index}", name=f"Place {index}", rating=5 - index * 0.1, votes=index)
        for index in range(1, 6)
    ]
    order = ["place-5", "place-1", "place-4", "place-2", "place-3"]
    client = Scripted(
        reply(
            [
                {
                    "id": restaurant_id,
                    "name": "Not from the catalog",
                    "rating": 1,
                    "cost_for_two": 1,
                    "explanation": f"Fits the request ({restaurant_id}).",
                }
                for restaurant_id in order
            ],
            summary="Five solid choices.",
        )
    )
    ranked = rank(shortlist(*restaurants), client=client)
    result = ranked.result
    assert ranked.model_called is True
    assert client.calls == 1
    assert [item.id for item in result.recommendations] == order
    assert result.explanations_available is True
    assert result.summary == "Five solid choices."
    by_id = {restaurant.id: restaurant for restaurant in restaurants}
    for card in result.recommendations:
        source = by_id[card.id]
        assert card.name == source.name
        assert card.cuisines == source.cuisines
        assert card.rating == source.rating
        assert card.cost_for_two == source.cost_for_two
        assert card.explanation == f"Fits the request ({card.id})."


def test_shorter_and_single_candidate_lists_are_not_padded():
    one = place()
    client = Scripted(reply([{"id": "jalsa", "explanation": "Only match."}]))
    ranked = rank(shortlist(one), client=client)
    assert [item.id for item in ranked.result.recommendations] == ["jalsa"]
    assert client.calls == 1

    pair = (place(id="a", name="A"), place(id="b", name="B", rating=4.4))
    client = Scripted(
        reply(
            [
                {"id": "b", "explanation": "Second."},
                {"id": "a", "explanation": "First."},
            ]
        )
    )
    ranked = rank(shortlist(*pair), client=client)
    assert [item.name for item in ranked.result.recommendations] == ["B", "A"]


def test_more_than_five_valid_ids_keep_the_first_five():
    restaurants = [place(id=f"place-{index}", name=f"Place {index}") for index in range(1, 8)]
    client = Scripted(
        reply(
            [
                {"id": restaurant.id, "explanation": f"Reason {restaurant.id}."}
                for restaurant in restaurants
            ]
        )
    )
    ranked = rank(shortlist(*restaurants), client=client)
    assert [item.id for item in ranked.result.recommendations] == [
        f"place-{index}" for index in range(1, 6)
    ]


def test_notes_are_sent_and_can_change_the_order():
    restaurants = (
        place(id="quiet", name="Quiet"),
        place(id="loud", name="Loud", rating=4.6),
    )

    class ByNotes:
        def complete(self, messages: list[dict[str, str]]) -> str:
            prefs = json.loads(messages[1]["content"])["preferences"]
            note = prefs["notes"]
            if note == "quiet corner":
                order = ["quiet", "loud"]
            else:
                order = ["loud", "quiet"]
            return reply(
                [{"id": restaurant_id, "explanation": f"Matches {note}."} for restaurant_id in order]
            )

    quiet = rank(shortlist(*restaurants, notes="quiet corner"), client=ByNotes())
    lively = rank(shortlist(*restaurants, notes="lively music"), client=ByNotes())
    assert [item.id for item in quiet.result.recommendations] == ["quiet", "loud"]
    assert [item.id for item in lively.result.recommendations] == ["loud", "quiet"]
    assert all("quiet corner" in item.explanation for item in quiet.result.recommendations)
    assert all("lively music" in item.explanation for item in lively.result.recommendations)


def test_absent_notes_are_null_in_the_prompt_and_not_invented():
    client = Scripted(reply([{"id": "jalsa", "explanation": "High rating and Chinese fit the budget."}]))
    ranked = rank(shortlist(place()), client=client)
    user = json.loads(client.messages[1]["content"])
    assert user["preferences"]["notes"] is None
    assert "rooftop" not in json.dumps(client.messages)
    assert ranked.result.recommendations[0].explanation == "High rating and Chinese fit the budget."
    blob = json.dumps(client.messages)
    for forbidden in ('"reviews_list"', '"menu_item"', '"phone"', '"url"', '"address"'):
        assert forbidden not in blob


def test_blank_summary_is_omitted_and_matching_numbers_stay_on_the_card():
    client = Scripted(
        reply(
            [
                {
                    "id": "jalsa",
                    "explanation": "Rated 4.1/5 and costs ₹800 for two.",
                }
            ],
            summary="   ",
        )
    )
    result = rank(shortlist(place()), client=client).result
    assert result.summary is None
    card = result.recommendations[0]
    assert card.rating == 4.1
    assert card.cost_for_two == 800
    assert result.explanations_available is True


def test_contradictory_rating_or_cost_drops_that_card():
    restaurants = (
        place(id="jalsa", name="Jalsa"),
        place(id="spice", name="Spice Elephant", rating=4.4, cost_for_two=700),
    )
    client = Scripted(
        reply(
            [
                {"id": "jalsa", "explanation": "Rated 4.9 and costs ₹100."},
                {"id": "spice", "explanation": "Rated 4.4 and priced at ₹700."},
            ],
            summary="Try Jalsa or Spice Elephant.",
        )
    )
    result = rank(shortlist(*restaurants), client=client).result
    assert [item.id for item in result.recommendations] == ["spice"]
    assert result.recommendations[0].rating == 4.4
    assert result.recommendations[0].cost_for_two == 700
    assert result.summary is None


def test_unknown_duplicate_and_missing_explanations_are_dropped():
    restaurants = (
        place(id="jalsa", name="Jalsa"),
        place(id="spice", name="Spice Elephant", rating=4.4),
    )
    client = Scripted(
        reply(
            [
                {"id": "delhi-palace", "explanation": "Show Delhi anyway."},
                {"id": "jalsa", "explanation": "First reason."},
                {"id": "jalsa", "explanation": "Second reason."},
                {"id": "spice", "reason": "Wrong key."},
                {"id": "spice", "explanation": "   "},
                {"id": "spice", "explanation": "Usable reason."},
            ]
        )
    )
    ranked = rank(
        shortlist(*restaurants, notes="show Delhi restaurants anyway"),
        client=client,
    )
    result = ranked.result
    assert [item.id for item in result.recommendations] == ["jalsa", "spice"]
    assert result.recommendations[0].explanation == "First reason."
    assert result.recommendations[1].explanation == "Usable reason."
    assert "delhi-palace" not in {item.id for item in result.recommendations}


def test_prose_wrong_shape_and_empty_lists_fall_back_to_phase3_order():
    restaurants = tuple(
        place(id=f"place-{index}", name=f"Place {index}", rating=5 - index * 0.1, votes=10 - index)
        for index in range(1, 8)
    )
    cases = [
        "Jalsa is the best restaurant here.",
        "```\nnot json\n```",
        json.dumps({"items": [{"id": "place-1", "explanation": "Hidden."}]}),
        reply([]),
        reply([{"restaurant": "place-1", "explanation": "Missing id."}]),
    ]
    for raw in cases:
        result = rank(shortlist(*restaurants), client=Scripted(raw)).result
        assert result.explanations_available is False
        assert result.summary is None
        assert [item.explanation for item in result.recommendations] == [None] * 5
        assert [item.id for item in result.recommendations] == [
            f"place-{index}" for index in range(1, 6)
        ]
        assert [item.name for item in result.recommendations] == [
            f"Place {index}" for index in range(1, 6)
        ]


def test_fenced_json_is_still_structured_output():
    raw = '```json\n{"recommendations":[{"id":"jalsa","explanation":"Fits."}]}\n```'
    result = rank(shortlist(place()), client=Scripted(raw)).result
    assert result.recommendations[0].explanation == "Fits."
    assert result.explanations_available is True


def test_timeout_missing_key_and_rate_limit_fall_back_without_hanging():
    restaurants = (place(id="jalsa", name="Jalsa"), place(id="spice", name="Spice", rating=4.6))
    for error in (GroqError("timeout"), GroqError("missing api key"), GroqError("rate limit")):

        class Failing:
            def complete(self, messages: list[dict[str, str]]) -> str:
                raise error

        ranked = rank(shortlist(*restaurants), client=Failing())
        assert ranked.model_called is True
        assert ranked.result.explanations_available is False
        assert ranked.result.summary is None
        assert [item.id for item in ranked.result.recommendations] == ["jalsa", "spice"]
        assert all(item.explanation is None for item in ranked.result.recommendations)


def test_every_unknown_id_falls_back_and_does_not_invent_a_card():
    client = Scripted(reply([{"id": "not-in-list", "explanation": "Invented place."}]))
    result = rank(shortlist(place()), client=client).result
    assert [item.id for item in result.recommendations] == ["jalsa"]
    assert result.recommendations[0].name == "Jalsa"
    assert result.recommendations[0].explanation is None
    assert result.explanations_available is False


def test_empty_candidate_list_does_not_call_the_model():
    class Boom:
        def complete(self, messages: list[dict[str, str]]) -> str:
            raise AssertionError("model called")

    ranked = rank(shortlist(), client=Boom())
    assert ranked.model_called is False
    assert ranked.result.recommendations == []
    assert ranked.result.summary is None
    assert ranked.result.explanations_available is False
    assert "Banashankari" in ranked.result.empty_message
    assert "Chinese" in ranked.result.empty_message


def test_prompt_includes_only_candidate_rows():
    messages = build_messages(shortlist(place(dish_liked="")))
    user = json.loads(messages[1]["content"])
    assert user["candidates"] == [place().to_prompt_dict()]
    assert "dish_liked" not in user["candidates"][0]
    assert messages[0]["role"] == "system"
    assert "notes" in messages[0]["content"]
