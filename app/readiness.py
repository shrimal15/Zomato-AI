"""Startup check. Recommendations stay closed until a catalog file exists."""

from pathlib import Path

from app.config import CATALOG_PATH
from app.errors import CatalogUnavailable


def assert_catalog_ready(path: Path = CATALOG_PATH) -> None:
    """Raise when the catalog file is missing, empty, or unreadable.

    This does not parse the file. Phase 1 owns download, cleaning, and load.
    """
    if not path.is_file():
        raise CatalogUnavailable(
            f"Catalog is unavailable at {path}. "
            "Build it in Phase 1 before requesting recommendations."
        )
    try:
        with path.open("rb") as handle:
            if handle.read(1) == b"":
                raise CatalogUnavailable(
                    f"Catalog is unavailable at {path}. The file is empty."
                )
    except CatalogUnavailable:
        raise
    except OSError as error:
        raise CatalogUnavailable(
            f"Catalog is unavailable at {path}. The file cannot be read."
        ) from error
