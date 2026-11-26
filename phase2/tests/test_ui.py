import json

import pytest
from pydantic import ValidationError

from app.models import Budget
from phase2 import options_for
from phase2.tests.test_phase2 import sample_catalog
from phase2.ui import handle_form, parse_preferences, preference_errors, render_page


class _ExplainsJalsa:
    def complete(self, messages: list[dict[str, str]]) -> str:
        return json.dumps(
            {
                "recommendations": [
                    {
                        "id": "jalsa",
                        "explanation": "Quick service fits this Chinese spot.",
                    }
                ],
                "summary": "One strong match.",
            }
        )


def test_form_becomes_one_preference_object():
    preferences = parse_preferences(
        {
            "location": " Banashankari ",
            "budget": " HIGH ",
            "cuisine": " Italian ",
            "min_rating": "4",
            "notes": "  family-friendly  ",
        }
    )
    assert preferences.location == "Banashankari"
    assert preferences.budget is Budget.high
    assert preferences.cuisine == "Italian"
    assert preferences.min_rating == 4.0
    assert preferences.notes == "family-friendly"


def test_blank_notes_are_absent():
    preferences = parse_preferences(
        {
            "location": "Banashankari",
            "budget": "low",
            "cuisine": "Chinese",
            "min_rating": "3.5",
            "notes": "   ",
        }
    )
    assert preferences.notes is None


def test_invalid_budget_is_rejected_before_any_catalog():
    with pytest.raises(ValidationError) as error:
        parse_preferences(
            {
                "location": "Delhi",
                "budget": "cheap",
                "cuisine": "Chinese",
                "min_rating": "4",
                "notes": "",
            }
        )
    assert preference_errors(error.value) == ["Choose a budget: low, medium, or high."]


def test_accepted_page_shows_normalized_preferences_and_escapes_text():
    catalog = sample_catalog()
    page = handle_form(
        {
            "location": "Banashankari",
            "budget": "medium",
            "cuisine": "Chinese",
            "min_rating": "4",
            "notes": "quick service",
        },
        catalog,
        client=_ExplainsJalsa(),
    )
    assert "Preferences accepted" in page
    assert "quick service" in page
    assert "Jalsa" in page
    assert "North Indian, Chinese" in page
    assert "Rating 4.1" in page
    assert "Estimated ₹800 for two" in page
    assert "Quick service fits this Chinese spot." in page
    assert "One strong match." in page
    assert "1 recommendation" in page
    rejected = handle_form(
        {
            "location": "<script>",
            "budget": "medium",
            "cuisine": "Chinese",
            "min_rating": "4",
            "notes": "",
        },
        catalog,
    )
    assert "Preferences accepted" not in rejected
    assert "&lt;script&gt;" in rejected
    assert "<script>" not in rejected


def test_invalid_page_keeps_the_entered_location():
    page = handle_form(
        {
            "location": "Banashankari",
            "budget": "",
            "cuisine": "",
            "min_rating": "9",
            "notes": "",
        },
        sample_catalog(),
    )
    assert "Preferences accepted" not in page
    assert "Enter a cuisine." in page
    assert "Choose a budget: low, medium, or high." in page
    assert "Enter a minimum rating from 0 to 5." in page
    assert 'value="Banashankari" selected' in page


def test_empty_filter_does_not_call_the_model():
    class Boom:
        def complete(self, messages: list[dict[str, str]]) -> str:
            raise AssertionError("model called")

    page = handle_form(
        {
            "location": "Banashankari",
            "budget": "low",
            "cuisine": "Chinese",
            "min_rating": "4",
            "notes": "",
        },
        sample_catalog(),
        client=Boom(),
    )
    assert "No restaurants match" in page
    assert "Jalsa" not in page
    assert "recommendation" not in page


def test_empty_page_has_the_input_fields():
    page = render_page(options=options_for(sample_catalog()))
    for name in ("location", "budget", "cuisine", "min_rating", "notes"):
        assert f'name="{name}"' in page
