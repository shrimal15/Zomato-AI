"""Download the Zomato CSV once. Later reads use the local file."""

import csv
import sys
from collections.abc import Iterator
from pathlib import Path

from app.config import DATASET_ID, RAW_DATASET_PATH, SOURCE_COLUMNS
from app.errors import CatalogUnavailable

_SOURCE_FILENAME = "zomato.csv"


def ensure_raw_dataset(path: Path = RAW_DATASET_PATH) -> Path:
    """Return the local CSV, downloading it only when the copy is missing."""
    if path.is_file() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import hf_hub_download

    downloaded = Path(
        hf_hub_download(
            repo_id=DATASET_ID,
            filename=_SOURCE_FILENAME,
            repo_type="dataset",
            local_dir=str(path.parent),
        )
    )
    if downloaded != path:
        downloaded.replace(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise CatalogUnavailable(f"Dataset download did not create {path}.")
    return path


def iter_source_rows(path: Path) -> Iterator[dict[str, object]]:
    """Yield only the columns Phase 1 keeps. Review and menu text is discarded."""
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    kept = set(SOURCE_COLUMNS.values())
    try:
        handle = path.open(encoding="utf-8-sig", newline="")
    except OSError as error:
        raise CatalogUnavailable(f"Dataset cannot be read at {path}.") from error
    with handle:
        reader = csv.DictReader(handle)
        missing = kept.difference(reader.fieldnames or [])
        if missing:
            names = ", ".join(sorted(missing))
            raise CatalogUnavailable(f"Dataset is missing columns: {names}.")
        for row in reader:
            yield {column: row.get(column) for column in kept}
