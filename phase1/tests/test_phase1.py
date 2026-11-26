import csv
import json

import pyarrow.parquet as pq
import pytest

from app.config import EXCLUDED_SOURCE_COLUMNS, SOURCE_COLUMNS
from app.errors import CatalogUnavailable, EmptyCatalog
from app.models import Budget
from phase1.clean import budget_thresholds, build_catalog, parse_cost, parse_cuisines, parse_rating
from phase1.download import ensure_raw_dataset, iter_source_rows
from phase1.ingest import ingest
from phase1.store import load_catalog


def row(**overrides) -> dict[str, object]:
    payload = {
        "name": "Jalsa",
        "address": "942, 21st Main Road, Banashankari",
        "location": "Banashankari",
        "cuisines": "North Indian, Mughlai, Chinese",
        "approx_cost(for two people)": "800",
        "rate": "4.1/5",
        "votes": "775",
        "rest_type": "Casual Dining",
        "dish_liked": "Pasta",
        "online_order": "Yes",
        "book_table": "Yes",
        "reviews_list": "x" * 1000,
        "menu_item": "[]",
        "url": "https://example.test",
        "phone": "080",
    }
    payload.update(overrides)
    return payload


def test_rating_and_cost_parse_the_dataset_shapes():
    assert parse_rating("4.1/5") == 4.1
    assert parse_rating("4.1 / 5") == 4.1
    assert parse_rating("4.1/5 ") == 4.1
    assert parse_rating("NEW") is None
    assert parse_rating("-") is None
    assert parse_rating(" ") is None
    assert parse_rating(None) is None
    assert parse_rating("5.4/5") is None
    assert parse_rating("-1/5") is None
    assert parse_cost("800") == 800
    assert parse_cost("1,200") == 1200
    assert parse_cost("1,000") == 1000
    assert parse_cost("0") == 0
    assert parse_cost("") is None
    assert parse_cost(None) is None
    assert parse_cost("about 800") is None
    assert parse_cuisines("Cafe,  Italian") == ["Cafe", "Italian"]
    assert parse_cuisines(None) is None
    assert parse_cuisines(" , ") is None


def test_duplicate_listings_collapse_and_chains_stay_separate():
    restaurants, _thresholds = build_catalog(
        [
            row(votes="10", rate="4.0/5", **{"approx_cost(for two people)": "600"}),
            row(
                votes="50",
                rate="3.8/5",
                name=" jalsa ",
                **{"approx_cost(for two people)": "900"},
            ),
            row(name="Jalsa", address="Church Street", votes="5"),
            row(rate="NEW"),
            row(**{"approx_cost(for two people)": ""}),
            row(cuisines=None),
            row(name="   ", address="   "),
            row(name="CafÃ© Down The Alley", address="12 Hosakerehalli", dish_liked=None),
        ]
    )
    by_address = {restaurant.cost_for_two: restaurant for restaurant in restaurants}
    assert len(restaurants) == 3
    kept = next(item for item in restaurants if item.votes == 50)
    assert kept.name == "jalsa"
    assert kept.rating == 3.8
    assert kept.cost_for_two == 900
    assert kept.dish_liked == "Pasta"
    chain = next(item for item in restaurants if item.votes == 5)
    assert chain.id != kept.id
    encoded = next(item for item in restaurants if item.name == "CafÃ© Down The Alley")
    assert encoded.dish_liked == ""
    assert "reviews_list" not in by_address[900].model_dump()


def test_budget_thresholds_are_stable_and_boundaries_belong_to_the_lower_band():
    costs = [100, 200, 300, 400, 500, 600]
    first = budget_thresholds(costs)
    second = budget_thresholds(list(reversed(costs)))
    assert first == second
    assert first.low_max == 200
    assert first.medium_max == 400
    assert first.band_for(200) is Budget.low
    assert first.band_for(201) is Budget.medium
    assert first.band_for(400) is Budget.medium
    assert first.band_for(401) is Budget.high
    single = budget_thresholds([0, 0])
    assert single.band_for(0) is Budget.low


def test_lookup_applies_location_cuisine_rating_and_budget():
    restaurants, thresholds = build_catalog(
        [
            row(**{"approx_cost(for two people)": "300"}),
            row(
                name="Spice Elephant",
                address="80 Feet Road",
                rate="3.2/5",
                cuisines="Chinese",
                **{"approx_cost(for two people)": "800"},
            ),
            row(
                name="Onesta",
                address="24th Cross",
                rate="4.6/5",
                cuisines="Pizza, Cafe, Italian",
                **{"approx_cost(for two people)": "2,000"},
            ),
            row(
                name="Other Place",
                address="Delhi Road",
                location="Basavanagudi",
                cuisines="Chinese",
                **{"approx_cost(for two people)": "300"},
            ),
        ]
    )
    catalog_rows = restaurants
    from phase1.store import Catalog

    catalog = Catalog(catalog_rows, thresholds)
    chinese = catalog.lookup(" banashankari ", "chinese", 4.1, "low")
    assert [item.name for item in chinese] == ["Jalsa"]
    assert chinese[0].cost_for_two == 300
    assert chinese[0].budget is Budget.low
    assert catalog.lookup("Banashankari", "Italian", 4.6, "high")[0].budget is Budget.high
    assert catalog.lookup("Banashankari", "Indian", 0, "high") == []
    assert catalog.lookup("Banashankari", "Italian", 4.6, "high")[0].name == "Onesta"
    assert "Banashankari" in catalog.locations()
    assert "Chinese" in catalog.cuisines()


def test_ingest_writes_a_catalog_without_private_columns(tmp_path):
    source = tmp_path / "zomato.csv"
    fieldnames = list(SOURCE_COLUMNS.values()) + list(EXCLUDED_SOURCE_COLUMNS)
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row())
        writer.writerow(row(name="Jalsa", votes="1"))
    catalog_path = tmp_path / "restaurants.parquet"
    thresholds_path = tmp_path / "budget_thresholds.json"
    catalog = ingest(
        source,
        catalog_path,
        thresholds_path,
        download=False,
    )
    loaded = load_catalog(catalog_path, thresholds_path)
    assert len(loaded.restaurants) == 1
    assert loaded.thresholds == catalog.thresholds
    schema = pq.read_schema(catalog_path)
    for column in EXCLUDED_SOURCE_COLUMNS:
        assert column not in schema.names
    assert "cost_for_two" in schema.names
    assert "budget" in schema.names
    assert loaded.restaurants[0].cost_for_two == 800
    assert loaded.restaurants[0].budget in {Budget.low, Budget.medium, Budget.high}
    saved = json.loads(thresholds_path.read_text(encoding="utf-8"))
    assert saved == {"low_max": catalog.thresholds.low_max, "medium_max": catalog.thresholds.medium_max}
    assert list(iter_source_rows(source))[0].keys() == set(SOURCE_COLUMNS.values())


def test_empty_clean_does_not_write_a_catalog(tmp_path):
    source = tmp_path / "zomato.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SOURCE_COLUMNS.values()))
        writer.writeheader()
        writer.writerow({column: row(rate="NEW").get(column) for column in SOURCE_COLUMNS.values()})
    with pytest.raises(EmptyCatalog):
        ingest(source, tmp_path / "restaurants.parquet", tmp_path / "budget_thresholds.json", download=False)
    assert not (tmp_path / "restaurants.parquet").exists()


def test_missing_or_unreadable_catalog_is_rejected(tmp_path):
    with pytest.raises(CatalogUnavailable):
        load_catalog(tmp_path / "missing.parquet", tmp_path / "missing.json")
    broken = tmp_path / "restaurants.parquet"
    broken.write_text("not parquet", encoding="utf-8")
    (tmp_path / "budget_thresholds.json").write_text('{"low_max": 1, "medium_max": 2}', encoding="utf-8")
    with pytest.raises(CatalogUnavailable):
        load_catalog(broken, tmp_path / "budget_thresholds.json")


def test_existing_raw_file_is_reused(tmp_path):
    raw = tmp_path / "zomato.csv"
    raw.write_text("already here", encoding="utf-8")
    assert ensure_raw_dataset(raw) == raw
