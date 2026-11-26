import json

from app.models import Budget, BudgetThresholds, Restaurant
from phase1.store import Catalog
from phase2.tests.test_phase2 import sample_catalog
from backend.api import RecommendationApi

_FORBIDDEN = ("phone", "url", "address", "reviews_list", "menu_item", "GROQ_API_KEY")


class _ExplainsJalsa:
    def complete(self, messages: list[dict[str, str]]) -> str:
        return json.dumps(
            {
                "recommendations": [
                    {"id": "jalsa", "explanation": "Quick service fits this Chinese spot."}
                ],
                "summary": "One strong match.",
            }
        )


class _Boom:
    def complete(self, messages: list[dict[str, str]]) -> str:
        raise AssertionError("model called")


class _Timeout:
    def complete(self, messages: list[dict[str, str]]) -> str:
        raise TimeoutError("timed out")


def _place(**overrides: object) -> Restaurant:
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


def test_health_reports_whether_the_catalog_loaded():
    loaded = RecommendationApi(sample_catalog()).handle("GET", "/api/health")
    missing = RecommendationApi(None).handle("GET", "/api/health")
    assert loaded.status == 200
    assert loaded.body == {"catalog_loaded": True}
    assert missing.status == 200
    assert missing.body == {"catalog_loaded": False}


def test_options_list_choices_and_rupee_bands_without_restaurant_rows():
    response = RecommendationApi(sample_catalog()).handle("GET", "/api/options")
    assert response.status == 200
    assert response.body["locations"] == ["Banashankari", "Basavanagudi"]
    assert "Chinese" in response.body["cuisines"]
    assert response.body["rating_min"] == 2.5
    assert response.body["rating_max"] == 4.6
    assert response.body["budgets"] == [
        {"id": "low", "max": 300},
        {"id": "medium", "min_exclusive": 300, "max": 800},
        {"id": "high", "min_exclusive": 800},
    ]
    assert "Jalsa" not in json.dumps(response.body)
    assert "<html" not in json.dumps(response.body).lower()


def test_recommendations_return_phase5_json():
    api = RecommendationApi(sample_catalog(), client=_ExplainsJalsa())
    response = api.handle(
        "POST",
        "/api/recommendations",
        json.dumps(
            {
                "location": " banashankari ",
                "budget": "medium",
                "cuisine": "Chinese",
                "min_rating": "4",
                "notes": "quick service",
            }
        ),
    )
    assert response.status == 200
    assert response.body["location"] == "Banashankari"
    assert response.body["budget"] == "medium"
    assert response.body["model_called"] is True
    assert response.body["explanations_available"] is True
    assert response.body["summary"] == "One strong match."
    cards = response.body["recommendations"]
    assert len(cards) == 1
    assert cards[0]["name"] == "Jalsa"
    assert cards[0]["cuisines"] == ["North Indian", "Chinese"]
    assert cards[0]["rating"] == 4.1
    assert cards[0]["cost_for_two"] == 800
    assert cards[0]["explanation"] == "Quick service fits this Chinese spot."
    encoded = json.dumps(response.body)
    for forbidden in _FORBIDDEN:
        assert forbidden not in encoded
    assert "<html" not in encoded.lower()


def test_invalid_preferences_are_400_and_do_not_call_the_model():
    response = RecommendationApi(sample_catalog(), client=_Boom()).handle(
        "POST",
        "/api/recommendations",
        json.dumps({"location": "Delhi", "budget": "low", "cuisine": "Chinese", "min_rating": 4}),
    )
    assert response.status == 400
    assert "errors" in response.body
    assert "recommendations" not in response.body


def test_empty_filter_is_200_and_does_not_call_the_model():
    response = RecommendationApi(sample_catalog(), client=_Boom()).handle(
        "POST",
        "/api/recommendations",
        json.dumps(
            {
                "location": "Banashankari",
                "budget": "low",
                "cuisine": "Chinese",
                "min_rating": 4,
            }
        ),
    )
    assert response.status == 200
    assert response.body["recommendations"] == []
    assert response.body["model_called"] is False
    assert "Banashankari" in response.body["empty_message"]
    assert "Chinese" in response.body["empty_message"]
    assert "low" in response.body["empty_message"]


def test_model_failure_returns_catalog_cards_without_an_explanation():
    response = RecommendationApi(sample_catalog(), client=_Timeout()).handle(
        "POST",
        "/api/recommendations",
        json.dumps(
            {
                "location": "Banashankari",
                "budget": "medium",
                "cuisine": "Chinese",
                "min_rating": 4,
            }
        ),
    )
    assert response.status == 200
    assert response.body["explanations_available"] is False
    assert response.body["model_called"] is True
    card = response.body["recommendations"][0]
    assert card["name"] == "Jalsa"
    assert card["rating"] == 4.1
    assert card["cost_for_two"] == 800
    assert card["explanation"] is None
    assert "summary" not in response.body


def test_missing_catalog_refuses_a_search():
    response = RecommendationApi(None, client=_Boom()).handle(
        "POST",
        "/api/recommendations",
        json.dumps(
            {
                "location": "Banashankari",
                "budget": "medium",
                "cuisine": "Chinese",
                "min_rating": 4,
            }
        ),
    )
    options = RecommendationApi(None).handle("GET", "/api/options")
    assert response.status == 503
    assert options.status == 503
    assert response.body["errors"] == ["The catalog is not available."]


def test_unknown_routes_are_json_and_only_the_frontend_origin_is_allowed():
    api = RecommendationApi(sample_catalog(), frontend_origin="http://127.0.0.1:5173")
    missing = api.handle("GET", "/")
    preflight = api.handle("OPTIONS", "/api/recommendations", origin="http://127.0.0.1:5173")
    other = api.handle("GET", "/api/health", origin="http://evil.example")
    assert missing.status == 404
    assert missing.body == {"errors": ["Not found."]}
    assert "text/html" not in missing.headers["Content-Type"]
    assert preflight.status == 204
    assert preflight.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
    assert "Access-Control-Allow-Origin" not in other.headers
    deployed = RecommendationApi(
        sample_catalog(),
        frontend_origin="https://zomato-ai.vercel.app, http://127.0.0.1:3000",
    )
    live = deployed.handle("GET", "/api/health", origin="https://zomato-ai.vercel.app")
    local = deployed.handle("GET", "/api/health", origin="http://127.0.0.1:3000/")
    blocked = deployed.handle("GET", "/api/health", origin="https://evil.example")
    assert live.headers["Access-Control-Allow-Origin"] == "https://zomato-ai.vercel.app"
    assert local.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:3000"
    assert "Access-Control-Allow-Origin" not in blocked.headers


def test_options_use_the_catalog_thresholds():
    catalog = Catalog(
        [_place(cost_for_two=450, budget=Budget.medium)],
        BudgetThresholds(low_max=300, medium_max=500),
    )
    response = RecommendationApi(catalog).handle("GET", "/api/options")
    assert response.body["budgets"][1] == {
        "id": "medium",
        "min_exclusive": 300,
        "max": 500,
    }
