"""T-Rank Scraper Module."""

import logging
import time
from io import StringIO
from typing import Optional

import pandas as pd
import requests

from scraper.task_manager import TaskCancelledError, get_task
from scraper.utils import (
    CURRENT_YEAR,
    REQUEST_TIMEOUT,
    DataScrapingError,
    create_session,
    get_end_day,
    write_df_to_csv,
)

logger = logging.getLogger(__name__)

# T-Rank URLs and statistics
T_RANK_URL_BASE = "https://barttorvik.com/trank.php"
T_RANK_RATING_NAMES = [
    "TEAM",
    "YEAR",
    "G",
    "REC",
    "W",
    "ADJOE",
    "ADJDE",
    "BARTHAG",
    "EFG%",
    "EFGD%",
    "TO%",
    "TO%D",
    "OR%",
    "DR%",
    "FTR",
    "FTRD",
    "3P%",
    "3P%D",
    "2P%",
    "2P%D",
    "FT%",
    "FT%D",
    "BLK%",
    "BLK%D",
    "3PR",
    "3PRD",
    "AST%",
    "AST%D",
    "TEMPO",
    "ADJTEMPO",
    "WAB",
]


def scrape_trank(
    start_year: int, end_year: int = CURRENT_YEAR, task_id: Optional[str] = None
) -> None:
    """Scrape team T-Rank ratings from given year to current year.

    Args:
        start_year: The earliest year to scrape ratings for
        task_id: Optional task ID for progress tracking

    Raises:
        TaskCancelledError: If the task is cancelled during execution.
        DataScrapingError: If a non-recoverable error occurs during scraping.
    """
    task = get_task(task_id) if task_id else None
    years_to_process = [y for y in range(start_year, end_year + 1) if y != 2020]
    total_years = len(years_to_process)

    logger.info(
        "Task %s: Starting T-Rank scraping for %d years (%d to %d).",
        task_id,
        total_years,
        start_year,
        end_year,
    )

    # Define headers for the T-Rank data
    raw_headers = [
        "TEAM",
        "ADJOE",
        "ADJDE",
        "BARTHAG",
        "REC",
        "W",
        "G",
        "EFG%",
        "EFGD%",
        "FTR",
        "FTRD",
        "TO%",
        "TO%D",
        "OR%",
        "DR%",
        "TEMPO",
        "2P%",
        "2P%D",
        "3P%",
        "3P%D",
        "BLK%",
        "BLK%D",
        "AST%",
        "AST%D",
        "3PR",
        "3PRD",
        "ADJTEMPO",
        "Unnamed: 27",
        "Unnamed: 28",
        "Unnamed: 29",
        "YEAR",
        "Unnamed: 31",
        "Unnamed: 32",
        "Unnamed: 33",
        "WAB",
        "FT%",
        "FT%D",
    ]

    processed_count = 0
    try:
        for i, year in enumerate(years_to_process):
            if task and task.cancelled:
                logger.info(
                    "Task %s: T-Rank scraping cancelled before processing year %d.", task_id, year
                )
                raise TaskCancelledError(f"Task {task_id} cancelled during T-Rank scraping.")

            logger.info(
                "Task %s: Processing T-Rank for year %d (%d/%d)", task_id, year, i + 1, total_years
            )

            end_day = get_end_day(year)

            try:
                _process_trank_year(year, end_day, raw_headers, T_RANK_RATING_NAMES, task_id)
                processed_count += 1
                logger.info("Task %s: Successfully scraped T-Rank data for %s", task_id, year)
            except DataScrapingError as e:
                # Log year-specific scraping errors but continue with other years
                logger.error(
                    "Task %s: Failed to process T-Rank for year %d: %s. Skipping year.",
                    task_id,
                    year,
                    e,
                )
            except Exception as e:  # pylint: disable=broad-except
                # Catch unexpected errors during single year processing
                logger.exception(
                    "Task %s: Unexpected error processing T-Rank for year %d. Skipping year. "
                    "Error: %s",
                    task_id,
                    year,
                    e,
                )

            # Update progress after attempting each year
            if task:
                progress = int(((i + 1) / total_years) * 100)
                task.update_progress(progress)
                logger.debug(
                    "Task %s: T-Rank progress after year %d: %d%%", task_id, year, progress
                )

            time.sleep(0.5)

    except TaskCancelledError:
        logger.info("Task %s: T-Rank scraping process cancelled.", task_id)
        raise  # Re-raise for the task manager
    except Exception as e:
        # Catch unexpected errors in the main loop setup/logic
        logger.exception("Task %s: Unexpected error during T-Rank scraping process.", task_id)
        raise DataScrapingError(f"Unexpected error during T-Rank scraping: {e}") from e

    logger.info(
        "Task %s: Finished T-Rank scraping. Processed %d out of %d years.",
        task_id,
        processed_count,
        total_years,
    )


def _process_trank_year(
    year: int, end_day: int, raw_headers: list, target_columns: list, task_id: Optional[str]
) -> None:
    """Fetches, processes, and saves T-Rank data for a single year."""
    try:
        # Construct URL (Keep existing logic)
        url = f"{T_RANK_URL_BASE}?&begin={year-1}1101&end={year}03{end_day-1}" f"&year={year}&csv=1"
        logger.debug("Task %s: Requesting T-Rank data for %s from URL: %s", task_id, year, url)

        # Fetch CSV with headers (BartTorvik may return HTML/blocked content without a UA)
        with create_session() as session:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()
            body = response.text.lstrip("\ufeff\n\r\t ")
            if body.startswith("<"):
                raise DataScrapingError(
                    f"T-Rank returned HTML instead of CSV for year {year}. "
                    "The site may be blocking automated requests."
                )

        # Read the CSV data
        df = pd.read_csv(StringIO(body), header=None, engine="python")
        logger.debug("Task %s: Read %d rows from T-Rank CSV for %d", task_id, len(df), year)

        # Assign raw headers and check column count
        if len(df.columns) != len(raw_headers):
            raise ValueError(
                f"Column count mismatch for year {year}. "
                f"Expected {len(raw_headers)}, got {len(df.columns)}."
            )
        df.columns = raw_headers

        # Remove the blank/unnamed columns
        cols_to_drop = [col for col in df.columns if "Unnamed" in str(col)]
        df = df.drop(columns=cols_to_drop)
        logger.debug(
            "Task %s: Dropped unnamed columns for year %d: %s", task_id, year, cols_to_drop
        )

        # Sort the dataset by TEAM
        df = df.sort_values(by="TEAM").reset_index(drop=True)

        # Reorder columns to match target_columns
        # Ensure all expected columns are present
        missing_cols = [col for col in target_columns if col not in df.columns]
        if missing_cols:
            logger.warning(
                "Task %s: Columns missing in T-Rank DataFrame for year %s: %s",
                task_id,
                year,
                missing_cols,
            )
            final_columns = [col for col in target_columns if col in df.columns]
        else:
            final_columns = target_columns
        df = df[final_columns]

        # Save the processed data
        output_filename = f"TRank{year}.csv"
        logger.debug(
            "Task %s: Saving processed T-Rank data for %s to %s", task_id, year, output_filename
        )
        write_df_to_csv(df, output_filename)

    except (requests.RequestException, pd.errors.ParserError, ValueError, IndexError) as e:
        # Catch specific, potentially recoverable errors for this year
        error_msg = f"Error scraping or processing T-Rank data for year {year}: {str(e)}"
        logger.error("Task %s: %s", task_id, error_msg)
        raise DataScrapingError(error_msg) from e
    except Exception as e:
        # Catch unexpected errors during this year's processing
        error_msg = f"Unexpected error scraping T-Rank data for year {year}: {str(e)}"
        logger.exception("Task %s: %s", task_id, error_msg)
        raise DataScrapingError(error_msg) from e
