"""Extract: download the Complete Journey source files and land them as Parquet.

The source is the CC0 ``completejourney`` package (84.51° / dunnhumby data).
Raw files are kept byte-for-byte with a SHA-256 manifest, so any later change
upstream is detected instead of silently altering the numbers.

    python -m retail.ingest            # download missing files, land Parquet
    python -m retail.ingest --force    # re-download everything
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import urllib.request
from datetime import UTC, datetime

import pyreadr

from retail.config import LANDING_DIR, RAW_DIR, SOURCE_BASE_URL, SOURCE_FILES, skipped_tables

logger = logging.getLogger("retail")
MANIFEST_PATH = RAW_DIR / "manifest.json"


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(force: bool = False) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {}
    for name, filename in SOURCE_FILES.items():
        target = RAW_DIR / filename
        if (target.exists() and not force) or name in skipped_tables():
            continue
        url = f"{SOURCE_BASE_URL}/{filename}"
        logger.info("downloading %s", url)
        tmp = target.with_suffix(target.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)  # noqa: S310 - fixed https source
        tmp.replace(target)
        manifest[name] = {
            "file": filename,
            "url": url,
            "bytes": target.stat().st_size,
            "sha256": _sha256(target),
            "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    for name, entry in manifest.items():
        if not (RAW_DIR / entry["file"]).exists() and name in skipped_tables():
            continue
        current = _sha256(RAW_DIR / entry["file"])
        if current != entry["sha256"]:
            raise RuntimeError(f"{entry['file']} changed on disk (checksum mismatch).")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    return manifest


def land(names: tuple[str, ...] | None = None) -> dict[str, int]:
    """Convert each R file to Parquet without changing values or types."""
    LANDING_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name in names or tuple(SOURCE_FILES):
        if name in skipped_tables():
            logger.info("skipped %s (RETAIL_SKIP_TABLES)", name)
            continue
        source = RAW_DIR / SOURCE_FILES[name]
        result = pyreadr.read_r(str(source))
        frame = next(iter(result.values()))
        frame.to_parquet(LANDING_DIR / f"{name}.parquet", index=False)
        counts[name] = len(frame)
        logger.info("landed %-22s %10s rows", name, f"{len(frame):,}")
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="Re-download every file.")
    args = parser.parse_args()
    download(force=args.force)
    land()


if __name__ == "__main__":
    main()
