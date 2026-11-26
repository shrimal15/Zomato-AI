"""Shared contracts. Later phases pass these objects and do not invent fields."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import NOTES_MAX_LENGTH, RATING_MAX, RATING_MIN, RESULT_CAP


class Budget(str, Enum):
    """Budget band. Membership is decided by BudgetThresholds."""

    low = "low"
    medium = "medium"
    high = "high"

    @classmethod
    def parse(cls, value: object) -> "Budget":
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise ValueError("budget must be low, medium, or high")
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as error:
            raise ValueError("budget must be low, medium, or high") from error


class BudgetThresholds(BaseModel):
    """Rupee boundaries stored with the catalog. A boundary belongs to the lower band."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    low_max: int = Field(ge=0)
    medium_max: int = Field(ge=0)

    @model_validator(mode="after")
    def bands_are_ordered(self) -> "BudgetThresholds":
        if self.low_max >= self.medium_max:
            raise ValueError("low_max must be less than medium_max")
        return self

    def band_for(self, cost: int) -> Budget:
        if cost <= self.low_max:
            return Budget.low
        if cost <= self.medium_max:
            return Budget.medium
        return Budget.high


class Restaurant(BaseModel):
    """One cleaned catalog row. Address is not stored; it is only used to build id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    cuisines: list[str] = Field(min_length=1)
    cost_for_two: int = Field(ge=0)
    budget: Budget
    rating: float = Field(ge=RATING_MIN, le=RATING_MAX)
    votes: int = Field(ge=0)
    rest_type: str = ""
    dish_liked: str = ""
    online_order: str = ""
    book_table: str = ""

    @field_validator("cuisines")
    @classmethod
    def cuisines_are_nonempty(cls, cuisines: list[str]) -> list[str]:
        cleaned = [item.strip() for item in cuisines if item.strip()]
        if not cleaned:
            raise ValueError("at least one cuisine is required")
        return cleaned

    def to_prompt_dict(self) -> dict[str, object]:
        """Fields the model may see. Empty dish_liked is omitted."""
        payload: dict[str, object] = {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "cuisines": list(self.cuisines),
            "cost_for_two": self.cost_for_two,
            "budget": self.budget.value,
            "rating": self.rating,
            "votes": self.votes,
            "rest_type": self.rest_type,
            "online_order": self.online_order,
            "book_table": self.book_table,
        }
        if self.dish_liked.strip():
            payload["dish_liked"] = self.dish_liked
        return payload


class Preferences(BaseModel):
    """User request. Catalog membership is checked in Phase 2, not here."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    location: str = Field(min_length=1)
    budget: Budget
    cuisine: str = Field(min_length=1)
    min_rating: float = Field(ge=RATING_MIN, le=RATING_MAX)
    notes: str | None = None

    @field_validator("budget", mode="before")
    @classmethod
    def normalize_budget(cls, value: object) -> Budget:
        return Budget.parse(value)

    @field_validator("location", "cuisine", mode="before")
    @classmethod
    def strip_required_text(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("must be text")
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("min_rating", mode="before")
    @classmethod
    def coerce_rating(cls, value: object) -> float:
        if isinstance(value, bool) or value is None:
            raise ValueError("min_rating must be a number")
        if isinstance(value, str):
            stripped = value.strip()
            try:
                return float(stripped)
            except ValueError as error:
                raise ValueError("min_rating must be a number") from error
        if isinstance(value, (int, float)):
            return float(value)
        raise ValueError("min_rating must be a number")

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("notes must be text")
        stripped = value.strip()
        if not stripped:
            return None
        if len(stripped) > NOTES_MAX_LENGTH:
            raise ValueError(f"notes must be at most {NOTES_MAX_LENGTH} characters")
        return stripped


class Recommendation(BaseModel):
    """One result card. Facts are copied from the catalog row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str
    cuisines: list[str]
    rating: float
    cost_for_two: int
    explanation: str | None = None

    @classmethod
    def from_restaurant(
        cls, restaurant: Restaurant, explanation: str | None
    ) -> "Recommendation":
        return cls(
            id=restaurant.id,
            name=restaurant.name,
            cuisines=list(restaurant.cuisines),
            rating=restaurant.rating,
            cost_for_two=restaurant.cost_for_two,
            explanation=explanation,
        )


class RecommendationResult(BaseModel):
    """What Phase 5 renders. At most five cards, and fallback cards have no explanation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str | None = None
    recommendations: list[Recommendation]
    explanations_available: bool
    empty_message: str | None = None

    @model_validator(mode="after")
    def result_is_consistent(self) -> "RecommendationResult":
        if len(self.recommendations) > RESULT_CAP:
            raise ValueError(f"at most {RESULT_CAP} recommendations are allowed")
        if not self.recommendations:
            if self.explanations_available or self.summary:
                raise ValueError("an empty result cannot include model text")
            if not self.empty_message or not self.empty_message.strip():
                raise ValueError("an empty result must explain which filters matched nothing")
            return self
        if self.explanations_available:
            missing = [item.id for item in self.recommendations if not item.explanation]
            if missing:
                raise ValueError("each recommendation needs an explanation")
        else:
            if self.summary:
                raise ValueError("fallback results cannot include a model summary")
            explained = [item.id for item in self.recommendations if item.explanation]
            if explained:
                raise ValueError("fallback cards cannot include a generated explanation")
        return self
