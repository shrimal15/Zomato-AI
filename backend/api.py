"""JSON API over Phases 2–5. Responses are objects, never pages."""

from dataclasses import dataclass

from app.config import FRONTEND_ORIGIN
from app.models import BudgetThresholds, Preferences
from phase1.store import Catalog
from phase2.collect import accept_json
from phase2.options import options_for
from phase3 import filter_candidates
from phase4 import rank
from phase4.rank import ChatClient
from phase5 import results_payload

_ROUTES = {
    "/api/health": frozenset({"GET"}),
    "/api/options": frozenset({"GET"}),
    "/api/recommendations": frozenset({"POST"}),
}
_CATALOG_UNAVAILABLE = "The catalog is not available."


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: dict[str, object]
    headers: dict[str, str]


class RecommendationApi:
    """Handle one API call. The catalog is loaded by the process, not per request."""

    def __init__(
        self,
        catalog: Catalog | None,
        client: ChatClient | None = None,
        frontend_origin: str = FRONTEND_ORIGIN,
    ) -> None:
        self.catalog = catalog
        self.client = client
        self.frontend_origins = tuple(
            origin.strip().rstrip("/")
            for origin in frontend_origin.split(",")
            if origin.strip()
        )

    def handle(
        self,
        method: str,
        path: str,
        body: str = "",
        origin: str | None = None,
    ) -> ApiResponse:
        method = method.upper()
        path = path.split("?", 1)[0]
        headers = self._headers(origin)
        if path not in _ROUTES:
            return ApiResponse(404, {"errors": ["Not found."]}, headers)
        if method == "OPTIONS":
            return ApiResponse(204, {}, headers)
        allowed = _ROUTES[path]
        if method not in allowed:
            headers = {**headers, "Allow": ", ".join(sorted(allowed))}
            return ApiResponse(405, {"errors": ["Method not allowed."]}, headers)
        if path == "/api/health":
            return ApiResponse(200, {"catalog_loaded": self.catalog is not None}, headers)
        if self.catalog is None:
            return ApiResponse(503, {"errors": [_CATALOG_UNAVAILABLE]}, headers)
        if path == "/api/options":
            return ApiResponse(200, options_payload(self.catalog), headers)
        status, payload = self._recommendations(body)
        return ApiResponse(status, payload, headers)

    def _recommendations(self, body: str) -> tuple[int, dict[str, object]]:
        assert self.catalog is not None
        status, payload = accept_json(body, self.catalog)
        if status != 200:
            return status, payload
        preferences = Preferences.model_validate(payload)
        filtered = filter_candidates(preferences, self.catalog)
        ranked = rank(filtered, client=self.client)
        return 200, {**payload, **results_payload(ranked, known=filtered.candidates)}

    def _headers(self, origin: str | None) -> dict[str, str]:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        allowed = origin.rstrip("/") if origin else ""
        if allowed and allowed in self.frontend_origins:
            headers["Access-Control-Allow-Origin"] = allowed
            headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Content-Type"
            headers["Vary"] = "Origin"
        return headers


def options_payload(catalog: Catalog) -> dict[str, object]:
    """Choices for the form. Restaurant rows are not included."""
    options = options_for(catalog)
    return {
        "locations": list(options.locations),
        "cuisines": list(options.cuisines),
        "rating_min": options.rating_min,
        "rating_max": options.rating_max,
        "budgets": budget_bands(catalog.thresholds),
    }


def budget_bands(thresholds: BudgetThresholds) -> list[dict[str, int | str]]:
    """Rupee limits for each band. A boundary belongs to the lower band."""
    return [
        {"id": "low", "max": thresholds.low_max},
        {
            "id": "medium",
            "min_exclusive": thresholds.low_max,
            "max": thresholds.medium_max,
        },
        {"id": "high", "min_exclusive": thresholds.medium_max},
    ]
