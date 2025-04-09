"""Score Scraper Module."""

import logging
import time
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from scraper.task_manager import TaskCancelledError, get_task
from scraper.utils import (
    CURRENT_YEAR,
    REQUEST_TIMEOUT,
    DataScrapingError,
    create_session,
    write_df_to_csv,
)

logger = logging.getLogger(__name__)

SPORTS_REF_URL_BASE = "https://www.sports-reference.com/cbb/postseason/men"


def scrape_scores(
    start_year: int, end_year: int = CURRENT_YEAR, task_id: Optional[str] = None
) -> None:
    # pylint: disable=too-many-locals
    """Scrape tournament game scores from given year to current year.

    Args:
        start_year: The earliest year to scrape scores for
        task_id: Optional task ID for progress tracking (used when called directly)

    Raises:
        TaskCancelledError: If the task is cancelled during execution.
        DataScrapingError: If a non-recoverable error occurs during scraping.
    """
    task = get_task(task_id) if task_id else None
    years_to_process = [y for y in range(start_year, end_year + 1) if y != 2020]
    total_years = len(years_to_process)

    all_games = []
    logger.info(
        "Task %s: Starting Scores scraping for %d years (%d to %d).",
        task_id,
        total_years,
        start_year,
        end_year,
    )

    processed_years_count = 0
    try:
        with create_session() as session:
            for i, year in enumerate(years_to_process):
                if task and task.cancelled:
                    logger.info(
                        "Task %s: Scores scraping cancelled before processing year %d.",
                        task_id,
                        year,
                    )
                    raise TaskCancelledError(
                        f"Task {task_id} cancelled during Scores scraping loop."
                    )

                logger.info(
                    "Task %s: Processing Scores for year %d (%d/%d)",
                    task_id,
                    year,
                    i + 1,
                    total_years,
                )

                yearly_games = _process_single_year_scores(session, year, task, task_id)

                if yearly_games:
                    all_games.extend(yearly_games)
                    # Save yearly data
                    games_df = pd.json_normalize(yearly_games)
                    write_df_to_csv(games_df, f"Scores{year}.csv")
                    processed_years_count += 1  # Increment only if successful

                # Update progress regardless of year success/failure, based on year iteration
                if task:
                    progress = int(((i + 1) / total_years) * 100)
                    task.update_progress(progress)
                    logger.debug(
                        "Task %s: Scores progress after year %d: %d%%", task_id, year, progress
                    )

                # Sleep to avoid overwhelming the server (Sports Ref limits requests to 20/min)
                time.sleep(3)

        if not all_games:
            logger.warning(
                "Task %s: No score data collected for the specified year range (%d to %d).",
                task_id,
                start_year,
                end_year,
            )
            return

        # Concatenate list of dicts outside the loop
        all_games_df = pd.json_normalize(all_games)
        logger.info(
            "Task %s: Finished scraping scores. Total games collected: %d",
            task_id,
            len(all_games_df),
        )
        write_df_to_csv(all_games_df, "AllScores.csv")
        logger.info(
            "Task %s: Finished Scores scraping. Successfully processed %d out of %d years.",
            task_id,
            processed_years_count,
            total_years,
        )

    except TaskCancelledError:
        # Catch cancellation signal from helper or main loop check
        logger.info("Task %s: Scores scraping process cancelled.", task_id)
        raise  # Re-raise if needed by caller
    except requests.RequestException as e:
        # Catch session-level or initial connection errors
        error_msg = f"Network error during score scraping: {str(e)}"
        logger.exception("Task %s: %s", task_id, error_msg)
        raise DataScrapingError(error_msg) from e
    except Exception as e:
        # Catch other unexpected errors in the main setup/finalization
        error_msg = f"Unexpected error during score scraping process: {str(e)}"
        logger.exception("Task %s: %s", task_id, error_msg)
        raise DataScrapingError(error_msg) from e


def _process_single_year_scores(session, year, task, task_id) -> Optional[list]:
    """Helper to scrape and process scores for a single year, handling errors."""
    try:
        if task and task.cancelled:
            logger.info("Task %s: Cancelled before processing scores for year %d.", task_id, year)
            raise TaskCancelledError(
                f"Task {task_id} cancelled before processing scores for year {year}."
            )

        yearly_games = _scrape_year_scores(session, year, task_id)
        if not yearly_games:
            logger.warning("Task %s: No score data found for year %d.", task_id, year)
            return None

        logger.info("Task %s: Successfully processed scores for year %d.", task_id, year)
        return yearly_games

    except TaskCancelledError:
        logger.info("Task %s: Cancelled during Scores processing for year %d.", task_id, year)
        raise  # Re-raise TaskCancelledError
    except DataScrapingError as e:  # Catch specific error from _scrape_year_scores
        logger.error(
            "Task %s: Failed to process scores for year %d: %s. Skipping year.", task_id, year, e
        )
        return None  # Indicate failure for this year
    except Exception as e:  # Catch unexpected errors
        logger.exception(
            "Task %s: Unexpected error scraping scores for year %d. Skipping year. Error: %s",
            task_id,
            year,
            e,
        )
        return None  # Indicate failure for this year


def _scrape_year_scores(session, year, task_id) -> list:
    """Scrape tournament scores data for a specific year.

    Args:
        session: Requests session to use
        year: Year to scrape data for
        task_id: Optional task ID for logging

    Returns:
        List of game dictionaries for the given year.

    Raises:
        DataScrapingError: If the request fails or parsing encounters an error.
    """
    games = []
    url = f"{SPORTS_REF_URL_BASE}/{year}-ncaa.html"
    try:
        logger.debug("Task %s: Requesting scores for %d from URL: %s", task_id, year, url)
        session_request = session.get(url, params={}, timeout=REQUEST_TIMEOUT)
        session_request.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        parsed_response = BeautifulSoup(session_request.text, "html.parser")
        brackets_node = parsed_response.find(id="brackets")
        if not brackets_node:
            raise DataScrapingError(f"Could not find brackets node for year {year} at URL {url}")

        # Use find_all directly on brackets_node for direct children with 'id' attribute
        bracket_children = brackets_node.find_all(lambda tag: tag.has_attr("id"), recursive=False)
        if not bracket_children:
            raise DataScrapingError(
                f"Could not find bracket children nodes for year {year} at URL {url}"
            )

        for bracket_child in bracket_children:
            bracket_games = _parse_bracket_games(year, bracket_child, task_id)
            games.extend(bracket_games)

    except requests.RequestException as e:
        error_msg = f"HTTP request failed for scores year {year}: {e}"
        logger.error("Task %s: %s", task_id, error_msg)
        raise DataScrapingError(error_msg) from e
    except Exception as e:
        error_msg = f"Error parsing scores HTML for year {year}: {e}"
        logger.exception("Task %s: %s", task_id, error_msg)
        raise DataScrapingError(error_msg) from e

    logger.debug("Task %s: Found %d games for year %d.", task_id, len(games), year)
    return games


def _parse_bracket_games(year, bracket_child, task_id):
    """Parse all games within a tournament bracket.

    Args:
        year: Tournament year
        bracket_child: BeautifulSoup element for the bracket
        task_id: Optional task ID for logging

    Returns:
        List of game dictionaries for the given bracket
    """
    bracket_games = []
    bracket_id = bracket_child.get("id", "unknown_bracket")  # Default if id is missing
    # Find rounds robustly
    bracket_rounds = bracket_child.find_all("div", class_=lambda x: x and x.startswith("round"))
    if not bracket_rounds:
        logger.warning(
            "Task %s: No rounds found in bracket '%s' for year %d", task_id, bracket_id, year
        )
        return []

    round_num = 1
    for bracket_round in bracket_rounds:
        # Find game containers
        game_nodes = bracket_round.find_all("div", recursive=False)
        for game_node in game_nodes:
            # Check if it looks like a game node (e.g., has children)
            if game_node.find(True, recursive=False):
                game = _parse_game(year, bracket_id, round_num, game_node, task_id)
                if game:
                    bracket_games.append(game)
            else:
                logger.debug(
                    "Task %s: Skipping empty node in round %d, bracket %s, year %d",
                    task_id,
                    round_num,
                    bracket_id,
                    year,
                )
        round_num += 1

    return bracket_games


def _parse_game(
    year: int, bracket_id: str, round_number: int, game_node, task_id
) -> Optional[dict]:
    """Parse a tournament game from HTML node.

    Extracts information about a tournament game, including participating teams,
    location, scores, and metadata. Returns None if essential parts are missing.

    Args:
        year: The year of the tournament
        bracket_id: Identifier for the tournament bracket
        round_number: Round number within the tournament
        game_node: BeautifulSoup element containing the game information
        task_id: Optional task ID for logging

    Returns:
        Dictionary containing structured game data, or None if parsing fails.
    """
    try:
        game = {
            "year": year,
            "bracket": bracket_id,
            "round": round_number,
            "team_a": None,
            "team_b": None,
            "location": None,
        }
        # Find direct children robustly
        game_children = game_node.find_all(True, recursive=False)

        # Expect at least 2 children for teams, optionally 3 for location
        if len(game_children) >= 2:
            game["team_a"] = _parse_team(game_children[0], task_id)
            game["team_b"] = _parse_team(game_children[1], task_id)
        else:
            logger.debug(
                "Task %s: Game node missing team children in round %d, bracket %s, year %d",
                task_id,
                round_number,
                bracket_id,
                year,
            )
            return None  # Cannot proceed without teams

        if len(game_children) >= 3:
            # Check if the third child contains a link for location
            location_link = game_children[2].find("a")
            if location_link and location_link.get_text().startswith("at "):
                game["location"] = location_link.get_text()[len("at ") :].strip()
            else:
                # Log if the structure is unexpected but don't fail the game parse
                logger.debug(
                    "Task %s: Unexpected location node structure in round %d, bracket %s, year %d",
                    task_id,
                    round_number,
                    bracket_id,
                    year,
                )

        # Check if teams were parsed successfully
        if not game["team_a"] or not game["team_b"]:
            logger.debug(
                "Task %s: Failed to parse one or both teams in round %d, bracket %s, year %d",
                task_id,
                round_number,
                bracket_id,
                year,
            )
            return None

        return game
    except Exception as e:
        logger.error(
            "Task %s: Error parsing game node in round %d, bracket %s, year %d: %s",
            task_id,
            round_number,
            bracket_id,
            year,
            e,
        )
        return None  # Return None on any parsing error within a game


def _parse_team(team_node, task_id) -> Optional[dict]:
    """Parse team information from a tournament game HTML node.

    Extracts team details including seed, name, score, and win status.
    Returns None if essential parts (like name) are missing.

    Args:
        team_node: BeautifulSoup element containing the team information
        task_id: Optional task ID for logging

    Returns:
        Dictionary containing structured team data, or None if parsing fails.
    """
    try:
        team = {
            "seed": None,
            "name": None,
            "score": None,
            "won": False,
        }
        classes = team_node.get("class", [])
        team["won"] = "winner" in classes

        # Find direct children
        team_children = team_node.find_all(True, recursive=False)

        # Check structure: Expect 3 items for seed, name, score
        if len(team_children) >= 3:
            team["seed"] = team_children[0].get_text().strip()
            team["name"] = team_children[1].get_text().strip()
            team["score"] = team_children[2].get_text().strip()
        elif len(team_children) == 2:
            team["seed"] = team_children[0].get_text().strip()
            team["name"] = team_children[1].get_text().strip()
            logger.debug("Task %s: Team node missing score for '%s'", task_id, team["name"])
        else:
            logger.warning(
                "Task %s: Unexpected team node structure: %s", task_id, team_node.prettify()
            )
            return None  # Cannot proceed without at least seed and name

        # Validate essential fields
        if not team["name"]:
            logger.warning(
                "Task %s: Failed to parse team name from node: %s", task_id, team_node.prettify()
            )
            return None

        # Convert seed/score to int if possible, otherwise keep as string
        try:
            team["seed"] = int(team["seed"]) if team["seed"] else None
        except (ValueError, TypeError):
            pass  # Keep as string if conversion fails or seed is None
        try:
            team["score"] = int(team["score"]) if team["score"] else None
        except (ValueError, TypeError):
            pass  # Keep as string if conversion fails or score is None

        return team
    except Exception as e:
        logger.error("Task %s: Error parsing team node: %s", task_id, e)
        return None  # Return None on any parsing error within a team
