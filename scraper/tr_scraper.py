"""TeamRankings Scraper Module."""

import logging
import time
from dataclasses import dataclass
from io import StringIO
from typing import Callable, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.task_manager import Task, TaskCancelledError, get_task
from scraper.utils import CURRENT_YEAR, DataScrapingError, get_end_day, write_df_to_csv

logger = logging.getLogger(__name__)

# TeamRankings.com URLs and statistics
TEAM_RANKINGS_URL_BASE = "https://www.teamrankings.com/ncaa-basketball"
TEAM_RANKINGS_STAT_NAMES = [
    "points-per-game",
    "average-scoring-margin",
    "offensive-efficiency",
    "floor-percentage",
    "1st-half-points-per-game",
    "2nd-half-points-per-game",
    "shooting-pct",
    "free-throw-pct",
    "true-shooting-percentage",
    "field-goals-made-per-game",
    "field-goals-attempted-per-game",
    "offensive-rebounds-per-game",
    "defensive-rebounds-per-game",
    "total-rebounding-percentage",
    "blocks-per-game",
    "steals-per-game",
    "assists-per-game",
    "assists-per-possession",
    "turnovers-per-game",
    "personal-fouls-per-game",
    "opponent-points-per-game",
    "opponent-average-scoring-margin",
    "defensive-efficiency",
    "opponent-floor-percentage",
    "opponent-1st-half-points-per-game",
    "opponent-2nd-half-points-per-game",
    "opponent-shooting-pct",
    "opponent-free-throw-pct",
    "opponent-true-shooting-percentage",
    "opponent-field-goals-made-per-game",
    "opponent-field-goals-attempted-per-game",
    "opponent-offensive-rebounds-per-game",
    "opponent-defensive-rebounds-per-game",
    "opponent-blocks-per-game",
    "opponent-steals-per-game",
    "opponent-assists-per-game",
    "opponent-assists-per-possession",
    "opponent-turnovers-per-game",
    "opponent-personal-fouls-per-game",
    "possessions-per-game",
    "extra-chances-per-game",
]
TEAM_RANKINGS_RATING_NAMES = [
    "predictive",
    "neutral",
    "schedule-strength",
    "season-sos",
    "sos-basic",
    "last-5-games",
    "last-10-games",
    "luck",
    "consistency",
    "vs-1-25",
    "vs-26-50",
    "vs-51-100",
    "vs-101-200",
    "vs-201-and-up",
    "first-half",
    "second-half",
]

# Constants for requests
REQUEST_TIMEOUT = 15  # seconds
RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],  # Common transient errors
)
HTTP_ADAPTER = HTTPAdapter(max_retries=RETRY_STRATEGY)


@dataclass
class ScrapingItemConfig:
    """Configuration for scraping a specific type of item (stat or rating)."""

    scrape_type: str
    item_names: list[str]
    url_template_func: Callable[[str, int, int], str]
    process_item_func: Callable
    output_filename_template: str
    process_single_year_func: Callable


@dataclass
class YearContext:
    """Context for scraping data for a specific year."""

    year: int
    end_day: int


@dataclass
class ItemContext:
    """Context for scraping a single item."""

    item_name: str
    year: int
    url: str
    item_type: str  # 'Stat' or 'Rating'
    expected_col_name: str


def scrape_ratings(
    start_year: int, end_year: int = CURRENT_YEAR, task_id: Optional[str] = None
) -> None:
    """Scrape team ratings from given year to current year."""
    ratings_config = ScrapingItemConfig(
        scrape_type="Ratings",
        item_names=TEAM_RANKINGS_RATING_NAMES,
        process_single_year_func=_process_single_year_ratings,
        url_template_func=_get_rating_url,
        process_item_func=_scrape_and_process_rating_item,
        output_filename_template="TeamRankingsRatings{year}.csv",
    )
    _scrape_generic(
        start_year=start_year,
        end_year=end_year,
        task_id=task_id,
        item_config=ratings_config,
    )


def scrape_stats(
    start_year: int, end_year: int = CURRENT_YEAR, task_id: Optional[str] = None
) -> None:
    """Scrape team statistics from given year to current year."""
    stats_config = ScrapingItemConfig(
        scrape_type="Stats",
        item_names=TEAM_RANKINGS_STAT_NAMES,
        process_single_year_func=_process_single_year_stats,
        url_template_func=_get_stat_url,
        process_item_func=_scrape_and_process_stat_item,
        output_filename_template="TeamRankingsStats{year}.csv",
    )
    _scrape_generic(
        start_year=start_year,
        end_year=end_year,
        task_id=task_id,
        item_config=stats_config,
    )


def _scrape_generic(
    start_year: int,
    end_year: int,
    task_id: Optional[str],
    item_config: ScrapingItemConfig,
) -> None:
    # pylint: disable=too-many-locals, too-many-statements
    """Generic scraping function for TeamRankings stats or ratings."""
    task = get_task(task_id) if task_id else None
    years_to_process = [y for y in range(start_year, end_year + 1) if y != 2020]
    total_years = len(years_to_process)

    logger.info(
        "Task %s: Starting TeamRankings %s scraping for %d years (%d to %d).",
        task_id,
        item_config.scrape_type,
        total_years,
        start_year,
        end_year,
    )

    processed_years_count = 0
    try:
        with _create_session() as session:
            for i, year in enumerate(years_to_process):
                # Check for cancellation before processing each year
                if task and task.cancelled:
                    logger.info(
                        "Task %s: %s scraping cancelled before processing year %d.",
                        task_id,
                        item_config.scrape_type,
                        year,
                    )
                    raise TaskCancelledError(
                        f"Task {task_id} cancelled during {item_config.scrape_type} scraping loop."
                    )

                end_day = get_end_day(year)

                logger.info(
                    "Task %s: Processing %s for year %d (%d/%d)",
                    task_id,
                    item_config.scrape_type,
                    year,
                    i + 1,
                    total_years,
                )

                try:
                    year_ctx = YearContext(year=year, end_day=end_day)
                    # Call specific helper to process the year
                    year_processed_successfully = item_config.process_single_year_func(
                        session, year_ctx, item_config, task, task_id
                    )
                    if year_processed_successfully:
                        processed_years_count += 1
                        logger.info(
                            "Task %s: Successfully processed %s for year %d.",
                            task_id,
                            item_config.scrape_type,
                            year,
                        )

                except TaskCancelledError:
                    # Re-raise immediately if caught from helper
                    raise
                except DataScrapingError as e:
                    # Log year-specific scraping errors but continue
                    logger.error(
                        "Task %s: Failed to process %s for year %d: %s. Skipping year.",
                        task_id,
                        item_config.scrape_type,
                        year,
                        e,
                    )
                except Exception as e:
                    # Catch unexpected errors during single year processing
                    logger.exception(
                        "Task %s: Unexpected error processing %s for year %d. Skipping year. "
                        "Error: %s",
                        task_id,
                        item_config.scrape_type,
                        year,
                        e,
                    )

                # Update progress after attempting each year
                if task:
                    progress = int(((i + 1) / total_years) * 100)
                    task.update_progress(progress)
                    logger.debug(
                        "Task %s: %s progress after year %d: %d%%",
                        task_id,
                        item_config.scrape_type,
                        year,
                        progress,
                    )

                time.sleep(0.5)

    except TaskCancelledError:
        logger.info("Task %s: %s scraping process cancelled.", task_id, item_config.scrape_type)
        raise  # Re-raise for the task manager
    except requests.RequestException as e:
        # Catch session-level or initial connection errors
        error_msg = f"Network error during {item_config.scrape_type} scraping: {str(e)}"
        logger.exception("Task %s: %s", task_id, error_msg)
        raise DataScrapingError(error_msg) from e
    except Exception as e:
        # Catch other unexpected errors in the main setup/finalization
        error_msg = f"Unexpected error during {item_config.scrape_type} scraping process: {str(e)}"
        logger.exception("Task %s: %s", task_id, error_msg)
        raise DataScrapingError(error_msg) from e

    logger.info(
        "Task %s: Finished TeamRankings %s scraping. Successfully processed %d out of %d years.",
        task_id,
        item_config.scrape_type,
        processed_years_count,
        total_years,
    )


def _create_session() -> requests.Session:
    """Creates a requests session with retry logic."""
    session = requests.Session()
    session.mount("https://", HTTP_ADAPTER)
    session.mount("http://", HTTP_ADAPTER)
    return session


def _process_single_year_ratings(
    session: requests.Session,
    year_ctx: YearContext,
    item_config: ScrapingItemConfig,
    task: Optional[Task],
    task_id: Optional[str],
) -> bool:
    """Scrapes, processes, and saves all ratings for a single year."""
    return _process_single_year_generic(
        session=session,
        year_ctx=year_ctx,
        item_config=item_config,
        task=task,
        task_id=task_id,
    )


def _process_single_year_stats(
    session: requests.Session,
    year_ctx: YearContext,
    item_config: ScrapingItemConfig,
    task: Optional[Task],
    task_id: Optional[str],
) -> bool:
    """Scrapes, processes, and saves all stats for a single year."""
    return _process_single_year_generic(
        session=session,
        year_ctx=year_ctx,
        item_config=item_config,
        task=task,
        task_id=task_id,
    )


def _get_rating_url(rating_name: str, year: int, end_day: int) -> str:
    """Constructs the URL for a specific rating."""
    return f"{TEAM_RANKINGS_URL_BASE}/ranking/{rating_name}-by-other?date={year}-03-{end_day}"


def _get_stat_url(stat_name: str, year: int, end_day: int) -> str:
    """Constructs the URL for a specific stat."""
    return f"{TEAM_RANKINGS_URL_BASE}/stat/{stat_name}?date={year}-03-{end_day}"


def _process_all_items_for_year(
    session: requests.Session,
    year_ctx: YearContext,
    item_config: ScrapingItemConfig,
    task: Optional[Task],
    task_id: Optional[str],
) -> pd.DataFrame:
    """Processes all items (stats/ratings) for a single year, returning a merged DataFrame."""
    all_items_for_year = pd.DataFrame()
    total_items = len(item_config.item_names)
    year = year_ctx.year
    end_day = year_ctx.end_day

    for item_index, item_name in enumerate(item_config.item_names):
        # Check for cancellation before each item request
        if task and task.cancelled:
            logger.info(
                "Task %s: Cancelled during %s scraping (inner loop for year %d, item %s).",
                task_id,
                item_config.scrape_type,
                year,
                item_name,
            )
            raise TaskCancelledError(
                f"Task {task_id} cancelled during {item_config.scrape_type} scraping for year "
                f"{year}."
            )

        logger.debug(
            "Task %s: Processing %s %d/%d: '%s' for year %d",
            task_id,
            item_config.scrape_type.lower(),
            item_index + 1,
            total_items,
            item_name,
            year,
        )

        url = item_config.url_template_func(item_name, year, end_day)
        # process_item_func is now part of item_config
        current_item_df = item_config.process_item_func(session, item_name, year, url, task_id)

        if current_item_df is not None:
            if all_items_for_year.empty:
                all_items_for_year = current_item_df
            else:
                # Use outer merge to handle potential team mismatches across items
                all_items_for_year = pd.merge(
                    all_items_for_year, current_item_df, on="Team", how="outer"
                )
            logger.debug(
                "Task %s: Merged %s '%s' into year %d DataFrame",
                task_id,
                item_config.scrape_type.lower(),
                item_name,
                year,
            )

        time.sleep(0.2)

    return all_items_for_year


def _process_single_year_generic(
    session: requests.Session,
    year_ctx: YearContext,
    item_config: ScrapingItemConfig,
    task: Optional[Task],
    task_id: Optional[str],
) -> bool:
    """Generic function to scrape, process, and save all items (stats/ratings) for a single year."""
    year = year_ctx.year
    scrape_type_lower = item_config.scrape_type.lower()

    try:
        all_items_for_year = _process_all_items_for_year(
            session,
            year_ctx,
            item_config,
            task,
            task_id,
        )

        # After processing all items for the year
        if not all_items_for_year.empty:
            logger.info(
                "Task %s: Finished scraping all %s for %d. Found %d teams.",
                task_id,
                scrape_type_lower,
                year,
                len(all_items_for_year),
            )
            output_filename = item_config.output_filename_template.format(year=year)
            write_df_to_csv(all_items_for_year, output_filename)
            return True
        # else: DataFrame is empty, meaning no items were successfully processed or found
        logger.warning(
            "Task %s: No %s collected or processed successfully for year %d. Skipping file write.",
            task_id,
            scrape_type_lower,
            year,
        )
        return False

    except TaskCancelledError:
        # Logged within _process_all_items_for_year, just re-raise
        raise
    except (
        requests.RequestException
    ) as e:  # Catch request errors from process_item_func if they bubble up
        logger.error(
            "Task %s: Network error during %s processing for year %d: %s",
            task_id,
            scrape_type_lower,
            year,
            e,
        )
        # Raise as DataScrapingError to signal failure for this year
        raise DataScrapingError(
            f"Network error scraping {scrape_type_lower} for year {year}"
        ) from e
    except Exception as e:  # Catch unexpected errors during this year's processing
        error_msg = f"Unexpected error scraping {scrape_type_lower} for year {year}: {str(e)}"
        logger.exception("Task %s: %s", task_id, error_msg)
        # Raise as DataScrapingError to signal failure for this year
        raise DataScrapingError(error_msg) from e


def _scrape_and_process_rating_item(
    session: requests.Session,
    item_name: str,
    year: int,
    url: str,
    task_id: Optional[str],
) -> Optional[pd.DataFrame]:
    """Wrapper for _scrape_and_process_item specific to ratings."""
    item_ctx = ItemContext(
        item_name=item_name, year=year, url=url, item_type="Rating", expected_col_name="Rating"
    )
    return _scrape_and_process_item(
        session=session,
        item_ctx=item_ctx,
        task_id=task_id,
    )


def _scrape_and_process_stat_item(
    session: requests.Session,
    item_name: str,
    year: int,
    url: str,
    task_id: Optional[str],
) -> Optional[pd.DataFrame]:
    """Wrapper for _scrape_and_process_item specific to stats."""
    item_ctx = ItemContext(
        item_name=item_name, year=year, url=url, item_type="Stat", expected_col_name=str(year - 1)
    )
    return _scrape_and_process_item(
        session=session,
        item_ctx=item_ctx,
        task_id=task_id,
    )


def _scrape_and_process_item(
    session: requests.Session,
    item_ctx: ItemContext,
    task_id: Optional[str],
) -> Optional[pd.DataFrame]:
    """Scrapes and processes a single statistic or rating page for a given year."""
    item_name = item_ctx.item_name
    year = item_ctx.year
    url = item_ctx.url
    item_type = item_ctx.item_type
    item_type_lower = item_type.lower()

    logger.debug(
        "Task %s: Requesting %s '%s' for %d from URL: %s", task_id, item_type, item_name, year, url
    )
    attempt = 0
    sleep_minutes = 5  # Sleep time in minutes for retrying after a 403 error
    # Loop indefinitely until a successful response or a non-403 error occurs
    while True:
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            break  # Exit loop on successful response
        except requests.RequestException as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 403:
                attempt += 1
                logger.warning(
                    "Task %s: Received 403 Forbidden for %s '%s' for year %d (attempt %d). "
                    "Sleeping for %d minutes before retrying.",
                    task_id,
                    item_type,
                    item_name,
                    year,
                    attempt,
                    sleep_minutes,
                )
                time.sleep(sleep_minutes * 60)
                continue  # Retry the request
            logger.error(
                "Task %s: HTTP request failed for %s '%s', year %d: %s",
                task_id,
                item_type_lower,
                item_name,
                year,
                e,
            )
            return None
        except Exception as e:
            logger.exception(
                "Task %s: Unexpected error processing %s '%s' for year %d: %s",
                task_id,
                item_type_lower,
                item_name,
                year,
                e,
            )
            return None

    # Process the response if successful
    current_item_df = _parse_and_clean_item_table(response.text, item_ctx, task_id)
    if current_item_df is not None:
        logger.debug(
            "Task %s: Successfully processed %s '%s' for year %d",
            task_id,
            item_type_lower,
            item_name,
            year,
        )
    return current_item_df


def _parse_and_clean_item_table(
    html_content: str,
    item_ctx: ItemContext,
    task_id: Optional[str],
) -> Optional[pd.DataFrame]:
    """Parses HTML, extracts, validates, and cleans the relevant table."""
    item_name = item_ctx.item_name
    year = item_ctx.year
    item_type = item_ctx.item_type
    expected_col_name = item_ctx.expected_col_name
    item_type_lower = item_type.lower()

    try:
        page_tables = pd.read_html(StringIO(html_content))
        if not page_tables:
            logger.warning(
                "Task %s: No tables found for %s '%s', year %d",
                task_id,
                item_type_lower,
                item_name,
                year,
            )
            return None

        current_item_df = page_tables[0]

        if (
            "Team" not in current_item_df.columns
            or expected_col_name not in current_item_df.columns
        ):
            logger.error(
                "Task %s: Missing expected columns ('Team', '%s') in %s data for '%s', year %d",
                task_id,
                expected_col_name,
                item_type_lower,
                item_name,
                year,
            )
            return None

        current_item_df = current_item_df.loc[:, ["Team", expected_col_name]]
        current_item_df = current_item_df.rename(columns={expected_col_name: item_name})
        current_item_df[item_name] = current_item_df[item_name].replace("--", "0")

        # Specific processing for ratings to clean team names
        if item_type == "Rating":
            # Use .str accessor safely
            extracted_teams = current_item_df["Team"].str.extract(
                r"^(.*?)(?:\s+\(\d+-\d+\))?$", expand=False
            )
            current_item_df["Team"] = extracted_teams.str.strip()
            original_nan_count = current_item_df["Team"].isna().sum()
            current_item_df = current_item_df.dropna(subset=["Team"])
            dropped_nan_count = (
                original_nan_count - current_item_df["Team"].isna().sum()
            )  # Recalculate after dropna
            if dropped_nan_count > 0:
                logger.debug(
                    "Task %s: Dropped %d rows with NaN Team names for rating '%s', year %d",
                    task_id,
                    dropped_nan_count,
                    item_name,
                    year,
                )
        return current_item_df

    except (pd.errors.ParserError, ValueError, IndexError, KeyError) as e:
        logger.error(
            "Task %s: Error parsing %s '%s' for year %d: %s",
            task_id,
            item_type_lower,
            item_name,
            year,
            e,
        )
        return None
