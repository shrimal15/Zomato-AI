"""Turn a form or JSON body into one Preference object.

Invalid input raises InvalidPreference. This module does not filter restaurants.
"""

import json

from pydantic import ValidationError

from app.config import NOTES_MAX_LENGTH, RATING_MAX, RATING_MIN
from app.errors import InvalidPreference
from app.models import Preferences
from app.rules import rating_in_catalog_range, resolve_catalog_value
from phase1.store import Catalog
from phase2.options import options_for


def preference_errors(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for item in error.errors():
        field = str(item["loc"][0]) if item.get("loc") else "form"
        text = str(item.get("msg", "Invalid value"))
        if text.startswith("Value error, "):
            text = text.removeprefix("Value error, ")
        messages.append(_friendly_message(field, text))
    return messages


def _friendly_message(field: str, text: str) -> str:
    if field == "location":
        return "Enter a location."
    if field == "cuisine":
        return "Enter a cuisine."
    if field == "budget":
        return "Choose a budget: low, medium, or high."
    if field == "min_rating":
        return f"Enter a minimum rating from {RATING_MIN:g} to {RATING_MAX:g}."
    if field == "notes":
        return f"Other preferences must be {NOTES_MAX_LENGTH} characters or fewer."
    return text


def collect(payload: dict[str, object], catalog: Catalog) -> Preferences:
    """Validate one request against the catalog and return a single Preference."""
    if not isinstance(payload, dict):
        raise InvalidPreference("A preference request must be an object.")
    try:
        draft = Preferences.model_validate(payload)
    except ValidationError as error:
        messages = preference_errors(error)
        raise InvalidPreference(messages[0], messages) from error

    options = options_for(catalog)
    errors: list[str] = []
    location = draft.location
    cuisine = draft.cuisine
    try:
        location = resolve_catalog_value(draft.location, set(options.locations), "location")
    except InvalidPreference as error:
        errors.append(str(error))
    try:
        cuisine = resolve_catalog_value(draft.cuisine, set(options.cuisines), "cuisine")
    except InvalidPreference as error:
        errors.append(str(error))
    try:
        rating_in_catalog_range(draft.min_rating, options.rating_min, options.rating_max)
    except InvalidPreference as error:
        errors.append(str(error))
    if errors:
        raise InvalidPreference(errors[0], errors)

    return Preferences(
        location=location,
        budget=draft.budget,
        cuisine=cuisine,
        min_rating=draft.min_rating,
        notes=draft.notes,
    )


def accept_json(body: str, catalog: Catalog) -> tuple[int, dict[str, object]]:
    """Accept a JSON preference body. The result is one object or a list of errors."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"errors": ["The request body must be JSON."]}
    try:
        preferences = collect(payload, catalog)
    except InvalidPreference as error:
        return 400, {"errors": error.errors}
    return 200, preferences.model_dump(mode="json")
