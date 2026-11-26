"""Start the recommendation API and load the catalog when it has been built."""

from app.errors import CatalogUnavailable, EmptyCatalog
from backend import serve
from phase1.ingest import activate


def main() -> int:
    try:
        catalog = activate()
    except (CatalogUnavailable, EmptyCatalog) as error:
        print(error)
        return 1
    if catalog is None:
        print("Catalog is not built yet. Run python -m phase1. Searches stay refused until then.")
    else:
        print(f"Loaded {len(catalog.restaurants)} restaurants from the local catalog.")
    serve(catalog)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
