"""Read and write the cleaned catalog. Requests never call Hugging Face."""

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from app.config import CATALOG_PATH, EXCLUDED_SOURCE_COLUMNS, THRESHOLDS_PATH
from app.errors import CatalogUnavailable, EmptyCatalog
from app.models import Budget, BudgetThresholds, Restaurant
from app.rules import (
    candidate_sort_key,
    cost_in_budget,
    cuisine_matches,
    location_matches,
    rating_meets_minimum,
)

CATALOG_SCHEMA = pa.schema(
    [
        ("id", pa.string()),
        ("name", pa.string()),
        ("location", pa.string()),
        ("cuisines", pa.list_(pa.string())),
        ("cost_for_two", pa.int64()),
        ("budget", pa.string()),
        ("rating", pa.float64()),
        ("votes", pa.int64()),
        ("rest_type", pa.string()),
        ("dish_liked", pa.string()),
        ("online_order", pa.string()),
        ("book_table", pa.string()),
    ]
)


class Catalog:
    """Queryable restaurants plus the budget thresholds saved with them."""

    def __init__(self, restaurants: list[Restaurant], thresholds: BudgetThresholds) -> None:
        if not restaurants:
            raise EmptyCatalog("Cleaning produced no restaurants.")
        self.restaurants = restaurants
        self.thresholds = thresholds

    def lookup(
        self,
        location: str,
        cuisine: str,
        min_rating: float,
        budget: Budget | str,
    ) -> list[Restaurant]:
        """Return every restaurant that matches all four filters."""
        selected = Budget.parse(budget)
        matches = [
            restaurant
            for restaurant in self.restaurants
            if location_matches(restaurant.location, location)
            and cuisine_matches(restaurant.cuisines, cuisine)
            and rating_meets_minimum(restaurant.rating, min_rating)
            and cost_in_budget(restaurant.cost_for_two, selected, self.thresholds)
        ]
        return sorted(matches, key=candidate_sort_key)

    def locations(self) -> set[str]:
        return {restaurant.location for restaurant in self.restaurants}

    def cuisines(self) -> set[str]:
        return {cuisine for restaurant in self.restaurants for cuisine in restaurant.cuisines}


def save_catalog(
    catalog: Catalog,
    catalog_path: Path = CATALOG_PATH,
    thresholds_path: Path = THRESHOLDS_PATH,
) -> None:
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(
        [restaurant.model_dump(mode="json") for restaurant in catalog.restaurants],
        schema=CATALOG_SCHEMA,
    )
    for column in EXCLUDED_SOURCE_COLUMNS:
        if column in table.column_names:
            raise CatalogUnavailable(f"Catalog must not store {column}.")
    pq.write_table(table, catalog_path)
    thresholds_path.write_text(catalog.thresholds.model_dump_json(), encoding="utf-8")


def load_catalog(
    catalog_path: Path = CATALOG_PATH,
    thresholds_path: Path = THRESHOLDS_PATH,
) -> Catalog:
    if not catalog_path.is_file() or not thresholds_path.is_file():
        raise CatalogUnavailable(
            f"Catalog is unavailable at {catalog_path}. Build it with python -m phase1."
        )
    try:
        table = pq.read_table(catalog_path)
        thresholds = BudgetThresholds.model_validate(
            json.loads(thresholds_path.read_text(encoding="utf-8"))
        )
        restaurants = [Restaurant.model_validate(row) for row in table.to_pylist()]
    except EmptyCatalog:
        raise
    except (OSError, pa.ArrowException, json.JSONDecodeError, ValidationError) as error:
        raise CatalogUnavailable(
            f"Catalog is unavailable at {catalog_path}. The file cannot be read."
        ) from error
    if not restaurants:
        raise EmptyCatalog("Cleaning produced no restaurants.")
    return Catalog(restaurants, thresholds)
