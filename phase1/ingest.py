"""Build the local catalog from the raw dataset."""

from pathlib import Path

from app.config import CATALOG_PATH, RAW_DATASET_PATH, THRESHOLDS_PATH
from phase1.clean import build_catalog
from phase1.download import ensure_raw_dataset, iter_source_rows
from phase1.store import Catalog, load_catalog, save_catalog

current: Catalog | None = None


def _with_progress(rows):
    for index, row in enumerate(rows, start=1):
        if index % 10000 == 0:
            print(f"Read {index} source rows...", flush=True)
        yield row


def ingest(
    source: Path | None = None,
    catalog_path: Path = CATALOG_PATH,
    thresholds_path: Path = THRESHOLDS_PATH,
    *,
    download: bool = True,
    progress: bool = False,
) -> Catalog:
    """Clean the dataset and write the parquet catalog plus budget thresholds."""
    raw_path = source
    if raw_path is None:
        raw_path = ensure_raw_dataset() if download else RAW_DATASET_PATH
    rows = iter_source_rows(raw_path)
    if progress:
        rows = _with_progress(rows)
    restaurants, thresholds = build_catalog(rows)
    catalog = Catalog(restaurants, thresholds)
    save_catalog(catalog, catalog_path, thresholds_path)
    return catalog


def activate(
    catalog_path: Path = CATALOG_PATH,
    thresholds_path: Path = THRESHOLDS_PATH,
) -> Catalog | None:
    """Load the catalog once at startup. A missing file leaves the form usable."""
    global current
    if not catalog_path.is_file():
        current = None
        return None
    current = load_catalog(catalog_path, thresholds_path)
    return current
