#!/usr/bin/env python3
"""media_sorter_refactored.py – Robust media organiser (SQLite edition)

Changes in this version
-----------------------
* **SQLite manifest** (`media_sort_log.sqlite3`) replaces the CSV file; handles 100 k+ rows easily.
* Single shared connection, auto‑initialised and committed per action.
* Otherwise identical copy/duplicate behaviour.
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import re
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, UnidentifiedImageError
from moviepy.editor import VideoFileClip
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants & regexes
# ---------------------------------------------------------------------------

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS

DATE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(\d{4})(\d{2})(\d{2})"), "%Y%m%d"),           # YYYYMMDD
    (re.compile(r"(\d{2})(\d{2})(\d{4})"), "%m%d%Y"),         # MMDDYYYY
    (re.compile(r"(\d{4})[-/.](\d{2})[-/.](\d{2})"), "%Y-%m-%d"),  # YYYY-MM-DD
    (re.compile(r"(\d{2})[-/.](\d{2})[-/.](\d{4})"), "%d-%m-%Y"),  # DD-MM-YYYY
    (re.compile(r"(\d{2})[-/.](\d{2})[-/.](\d{2})"), "%y-%m-%d"),  # YY-MM-DD
    (re.compile(r"(\d{2})[-/.](\d{2})[-/.](\d{2})"), "%d-%m-%y"),  # DD-MM-YY
]

_EXIF_DATETIME_ID = 0x9003  # DateTimeOriginal
DB_FILENAME = "media_sort_log.sqlite3"

_DB_CONN: Optional[sqlite3.Connection] = None  # lazily initialised

# ---------------------------------------------------------------------------
# Dataclass configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Config:
    source: Path
    destination: Path
    qualifier: Optional[str] = None
    dry_run: bool = False
    filter_pxl: bool = False
    verbose: bool = False

    @property
    def qualifier_prefix(self) -> str:
        return f"{self.qualifier[0].upper()}_" if self.qualifier else ""

    @property
    def qualifier_dir(self) -> str:
        return self.qualifier or ""

    @property
    def db_path(self) -> Path:
        return self.destination / DB_FILENAME

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_conn(db_path: Path) -> sqlite3.Connection:
    """Return a module‑level cached connection, creating file/table if needed."""
    global _DB_CONN
    if _DB_CONN is None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _DB_CONN = sqlite3.connect(db_path)
        _DB_CONN.execute(
            """CREATE TABLE IF NOT EXISTS actions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT,
                   action TEXT,
                   src TEXT,
                   dst TEXT,
                   checksum TEXT
               )"""
        )
        _DB_CONN.execute("CREATE INDEX IF NOT EXISTS idx_checksum ON actions(checksum)")
        _DB_CONN.commit()
    return _DB_CONN


def _log_action(cfg: Config, action: str, src: Path, dst: Path, checksum: str | None = None) -> None:
    conn = _get_conn(cfg.db_path)
    conn.execute(
        "INSERT INTO actions (timestamp, action, src, dst, checksum) VALUES (?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), action, str(src), str(dst), checksum or ""),
    )
    conn.commit()

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def gather_media(folder: Path, *, filter_pxl: bool = False) -> Iterable[Path]:
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in MEDIA_EXTS:
            if filter_pxl and not path.name.upper().startswith("PXL"):
                continue
            yield path


def _sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logging.warning("Could not hash file %s: %s", path, e)
        return "ERROR_HASH"  # Use a special string or skip this file



def _get_image_date(path: Path) -> Optional[datetime]:
    try:
        with Image.open(path) as img:
            if (exif := img.getexif()):
                if (date_str := exif.get(_EXIF_DATETIME_ID)):
                    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except (UnidentifiedImageError, OSError):
        logging.debug("Unidentified image: %s", path)
    except Exception as exc:  # noqa: BLE001
        logging.debug("Error reading EXIF from %s: %s", path, exc)
    return None


def _get_video_date(path: Path) -> Optional[datetime]:
    try:
        with VideoFileClip(str(path)) as clip:
            if (creation := getattr(clip, "creation_date", None)):
                if isinstance(creation, datetime):
                    return creation
                try:
                    return datetime.strptime(creation, "%Y-%m-%d %H:%M:%S")
                except (TypeError, ValueError):
                    pass
    except Exception as exc:  # noqa: BLE001
        logging.debug("moviepy error on %s: %s", path, exc)
    return None


def _get_filename_date(path: Path) -> Optional[datetime]:
    for pattern, fmt in DATE_PATTERNS:
        if (match := pattern.search(path.stem)):
            try:
                return datetime.strptime("".join(match.groups()), fmt)
            except ValueError as exc:
                logging.debug("Filename date parse error %s: %s", path.name, exc)
                continue
    return None


def get_media_date(path: Path) -> datetime:
    if path.suffix.lower() in IMAGE_EXTS:
        date = _get_image_date(path)
    else:
        date = _get_video_date(path)
    if not date:
        date = _get_filename_date(path)
    if not date:
        date = datetime.fromtimestamp(path.stat().st_mtime)
    return date

# ---------------------------------------------------------------------------
# Copy routine with duplicate detection
# ---------------------------------------------------------------------------

def _checksum_exists(cfg: Config, checksum: str) -> bool:
    """Check if this checksum has already been logged in the DB."""
    conn = _get_conn(cfg.db_path)
    result = conn.execute(
        "SELECT 1 FROM actions WHERE checksum = ? LIMIT 1", (checksum,)
    ).fetchone()
    return result is not None

def _safe_copy(src: Path, dst_dir: Path, new_name: str, *, cfg: Config) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / new_name
    checksum_src = _sha256(src)

    # 1. GLOBAL DUPLICATE CHECK
    if _checksum_exists(cfg, checksum_src):
        logging.warning("Duplicate file already imported (by checksum): %s", src.name)
        _log_action(cfg, "duplicate_seen", src, target, checksum_src)
        return

    # 2. LOCAL NAME CLASH HANDLING (RARE IF CHECKSUM UNIQUE, BUT STILL USEFUL)
    final_target = target
    if final_target.exists():
        checksum_dst = _sha256(final_target)
        if checksum_src == checksum_dst:
            # Should never happen if DB is correct, but just in case
            logging.warning("Duplicate at destination: %s", final_target.name)
            _log_action(cfg, "duplicate_ref", src, final_target, checksum_src)
            return
        stem_with_hash = f"{final_target.stem}_{checksum_src[:8]}"
        final_target = final_target.with_stem(stem_with_hash)
        while final_target.exists():
            final_target = final_target.with_stem(f"{final_target.stem}_1")
        logging.warning("Name clash – copying as %s", final_target.name)

    if cfg.dry_run:
        logging.info("[DRY‑RUN] copy %s -> %s", src, final_target)
        _log_action(cfg, "dry_run", src, final_target, checksum_src)
        return

    shutil.copy2(src, final_target)
    _log_action(cfg, "copy", src, final_target, checksum_src)


# ---------------------------------------------------------------------------
# Core organiser
# ---------------------------------------------------------------------------

def sort_media(cfg: Config) -> None:
    _get_conn(cfg.db_path)  # ensure DB/table ready
    media_files = list(gather_media(cfg.source, filter_pxl=cfg.filter_pxl))
    if not media_files:
        logging.warning("No media files found in %s", cfg.source)
        return

    # Compute the date for each file, then sort descending (most recent first)
    media_files_with_dates = [
        (path, get_media_date(path)) for path in media_files
    ]
    media_files_with_dates.sort(key=lambda x: x[1], reverse=True)  # Most recent first

    for path, date in tqdm(media_files_with_dates, desc="Copying media", unit="file"):
        dest_dir = cfg.destination / f"{date.year}" / f"{date.month:02d}"
        if cfg.qualifier_dir:
            dest_dir /= cfg.qualifier_dir
        new_filename = f"{cfg.qualifier_prefix}{path.name}"
        _safe_copy(path, dest_dir, new_filename, cfg=cfg)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Copy (not move) media files into YYYY/MM/[qualifier] folders and log to SQLite.")
    p.add_argument("source_dir", type=Path, help="Directory containing media to sort")
    p.add_argument("dest_dir", type=Path, help="Destination directory")
    p.add_argument("--qualifier", help="Optional qualifier for sub‑categorisation (e.g. trip name)")
    p.add_argument("--dry-run", action="store_true", help="Simulate without copying files")
    p.add_argument("--filter-pxl", action="store_true", help="Only process files beginning with 'PXL'")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable debug output")
    return p


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = _build_arg_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname).1s %(message)s",
        stream=sys.stdout,
    )

    cfg = Config(
        source=args.source_dir.expanduser().resolve(),
        destination=args.dest_dir.expanduser().resolve(),
        qualifier=args.qualifier,
        dry_run=args.dry_run,
        filter_pxl=args.filter_pxl,
        verbose=args.verbose,
    )

    logging.debug("Running with config: %s", cfg)
    sort_media(cfg)


if __name__ == "__main__":
    main()