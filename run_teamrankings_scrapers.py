#!/usr/bin/env python3
"""Run TeamRankings scrapers without starting the Django server.

This bootstraps Django settings (so defaults like CURRENT_YEAR and DATA_PATH
match the web app), then runs TeamRankings Stats and Ratings scrapers.

By default it uses the app's CURRENT_YEAR for both start and end.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence


DEFAULT_ONEDRIVE_DATA_PATH = "/mnt/c/Users/mitch/OneDrive/March Madness/Data"


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run TeamRankings stats + ratings scrapers using the same defaults as the Django app"
        )
    )
    parser.add_argument(
        "--data-path",
        default=None,
        help=(
            "Where CSVs are written. If omitted, uses $MARCH_MADNESS_DATA_PATH when set; "
            f"otherwise defaults to {DEFAULT_ONEDRIVE_DATA_PATH} when it exists, or the app's ./data"
        ),
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Start year (defaults to CURRENT_YEAR)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="End year (defaults to CURRENT_YEAR)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would run; do not scrape",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    # Configure CSV output location before Django initializes settings.
    # This mirrors start_server.sh (WSL -> Windows OneDrive path), but falls back safely.
    if args.data_path:
        os.environ["MARCH_MADNESS_DATA_PATH"] = args.data_path
    elif "MARCH_MADNESS_DATA_PATH" not in os.environ:
        default_path = Path(DEFAULT_ONEDRIVE_DATA_PATH)
        if default_path.exists():
            os.environ["MARCH_MADNESS_DATA_PATH"] = str(default_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "march_madness.settings")

    # Important: set up Django before importing scraper modules,
    # since scraper.utils reads from django.conf.settings at import time.
    import django  # pylint: disable=import-outside-toplevel

    django.setup()

    from django.conf import settings  # pylint: disable=import-outside-toplevel

    current_year = int(settings.CURRENT_YEAR)
    start_year = current_year if args.start_year is None else int(args.start_year)
    end_year = current_year if args.end_year is None else int(args.end_year)

    if start_year > end_year:
        raise SystemExit("start_year cannot be after end_year")
    if end_year > current_year:
        raise SystemExit(
            f"end_year ({end_year}) cannot be after CURRENT_YEAR ({current_year})"
        )

    if args.dry_run:
        print(
            "Dry run: would run TeamRankings scrapers for years "
            f"{start_year}..{end_year} (DATA_PATH={settings.DATA_PATH})"
        )
        print("- scrape_stats")
        print("- scrape_ratings")
        return 0

    from scraper.tr_scraper import scrape_ratings, scrape_stats  # pylint: disable=import-outside-toplevel

    print(
        f"Running TeamRankings scrapers for years {start_year}..{end_year} "
        f"(DATA_PATH={settings.DATA_PATH})"
    )

    scrape_stats(start_year=start_year, end_year=end_year)
    scrape_ratings(start_year=start_year, end_year=end_year)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
