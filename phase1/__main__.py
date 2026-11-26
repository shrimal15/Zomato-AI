"""Build the catalog: python -m phase1"""

from phase1.ingest import ingest


def main() -> int:
    print("Building the restaurant catalog from the local Zomato dataset...")
    catalog = ingest(progress=True)
    print(
        f"Saved {len(catalog.restaurants)} restaurants. "
        f"Budget bands: low <= {catalog.thresholds.low_max}, "
        f"medium <= {catalog.thresholds.medium_max}, "
        f"high above {catalog.thresholds.medium_max}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
