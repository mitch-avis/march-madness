"""
Scraper utility module.

This module contains functions for scraping and parsing NCAA basketball data
including team statistics, ratings, and tournament game scores.

The module provides functionality to:
- Scrape team statistics from multiple seasons
- Scrape team ratings and rankings
- Scrape and parse tournament game results
- Process and save data to standardized formats
"""

import logging
import os
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from django.conf import settings

from .task_manager import get_task

logger = logging.getLogger(__name__)

# Constants
CURRENT_YEAR = settings.CURRENT_YEAR
DATA_PATH = settings.DATA_PATH

# Configure constants from original code
SITE_URL_PREFIX = "https://www.teamrankings.com/ncaa-basketball"
STAT_NAMES = [
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
RATING_NAMES = [
    "predictive",
    "neutral",
    "schedule-strength",
    "season-sos",
    "sos-basic",
    "last-5-games",
    "last-10-games",
    "luck",
    "consistency",
]
END_DATES = {
    2008: 20,
    2009: 19,
    2010: 18,
    2011: 17,
    2012: 15,
    2013: 21,
    2014: 20,
    2015: 19,
    2016: 17,
    2017: 16,
    2018: 15,
    2019: 21,
    2021: 19,
    2022: 17,
    2023: 16,
    2024: 21,
    2025: 20,
}


class DataScrapingError(Exception):
    """Exception raised when data scraping operations fail."""

    def __init__(self, message="Data scraping operation failed"):
        self.message = message
        super().__init__(self.message)


def scrape_stats(start_year: int, task_id: str = None) -> None:
    """Scrape team statistics from given year to current year.

    Args:
        start_year: The earliest year to scrape statistics for
        task_id: Optional task ID for progress tracking

    Raises:
        DataScrapingError: If there's an error during scraping
        ValueError: If the year is invalid
    """
    task = get_task(task_id) if task_id else None
    years_to_process = [y for y in range(start_year, CURRENT_YEAR + 1) if y != 2020]
    total_years = len(years_to_process)

    for i, year in enumerate(years_to_process):
        if task:
            # Update progress based on year completion
            progress = int((i / total_years) * 100)
            task.update_progress(progress)

        try:
            all_stats = pd.DataFrame()
            for _, stat_name in enumerate(STAT_NAMES):
                url = f"{SITE_URL_PREFIX}/stat/{stat_name}?date={year}-03-{END_DATES[year]}"
                logger.debug("Scraping from URL: %s", url)
                page = pd.read_html(url)
                current_stat = page[0]
                current_stat = current_stat.loc[:, ["Team", str(year - 1)]]
                current_stat = current_stat.rename(columns={str(year - 1): stat_name})

                if all_stats.empty:
                    all_stats = current_stat
                else:
                    all_stats = pd.merge(all_stats, current_stat, on="Team")

                logger.debug("Successfully scraped %s", stat_name)

            logger.debug("Done scraping stats for %s", year)
            write_df_to_csv(all_stats, f"TeamRankings{year}.csv")

        except (requests.RequestException, pd.errors.ParserError) as e:
            error_msg = f"Error scraping stats for year {year}: {str(e)}"
            logger.exception(error_msg)
            raise DataScrapingError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error scraping stats for year {year}: {str(e)}"
            logger.exception(error_msg)
            raise DataScrapingError(error_msg) from e


def scrape_ratings(start_year: int, task_id: str = None) -> None:
    """Scrape team ratings from given year to current year.

    Args:
        start_year: The earliest year to scrape ratings for
        task_id: Optional task ID for progress tracking
    """
    task = get_task(task_id) if task_id else None
    years_to_process = [y for y in range(start_year, CURRENT_YEAR + 1) if y != 2020]
    total_years = len(years_to_process)

    for i, year in enumerate(years_to_process):
        if task:
            # Update progress based on year completion
            progress = int((i / total_years) * 100)
            task.update_progress(progress)

        try:
            all_stats = pd.DataFrame()
            for stat_name in RATING_NAMES:
                url = (
                    f"{SITE_URL_PREFIX}/ranking/{stat_name}-by-other?"
                    f"date={year}-03-{END_DATES[year]}"
                )
                logger.debug("Scraping from URL: %s", url)
                page = pd.read_html(url)
                current_stat = page[0]
                current_stat = current_stat.loc[:, ["Team", "Rating"]]
                current_stat = current_stat.rename(columns={"Rating": stat_name})
                current_stat["Team"] = current_stat["Team"].str.extract(r"(.*?)\s+\(\d+-\d+\)")

                if all_stats.empty:
                    all_stats = current_stat
                else:
                    all_stats = pd.merge(all_stats, current_stat, on="Team")

                logger.debug("Successfully scraped %s", stat_name)

            logger.debug("Done scraping stats for %s", year)
            write_df_to_csv(all_stats, f"TeamRankingsRatings{year}.csv")

        except (requests.RequestException, pd.errors.ParserError) as e:
            error_msg = f"Error scraping ratings for year {year}: {str(e)}"
            logger.exception(error_msg)
            raise DataScrapingError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error scraping ratings for year {year}: {str(e)}"
            logger.exception(error_msg)
            raise DataScrapingError(error_msg) from e


def scrape_scores(start_year: int, task_id: str = None) -> None:
    """Scrape tournament game scores from given year to current year.

    Args:
        start_year: The earliest year to scrape scores for
        task_id: Optional task ID for progress tracking
    """
    task = get_task(task_id) if task_id else None
    years_to_process = [y for y in range(start_year, CURRENT_YEAR + 1) if y != 2020]
    total_years = len(years_to_process)
    all_games = []

    try:
        session = requests.Session()
        with session:
            for i, year in enumerate(years_to_process):
                if task:
                    # Update progress based on year completion
                    progress = int((i / total_years) * 100)
                    task.update_progress(progress)

                yearly_games = _scrape_year_scores(session, year)
                all_games.extend(yearly_games)

                # Save yearly data
                games_df = pd.json_normalize(yearly_games)
                write_df_to_csv(games_df, f"Scores{year}.csv")
                time.sleep(0.5)

        # Save all years' data
        all_games_df = pd.json_normalize(all_games)
        write_df_to_csv(all_games_df, "AllScores.csv")

    except (requests.RequestException, pd.errors.ParserError) as e:
        error_msg = f"Error scraping scores: {str(e)}"
        logger.exception(error_msg)
        raise DataScrapingError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error scraping scores: {str(e)}"
        logger.exception(error_msg)
        raise DataScrapingError(error_msg) from e


def _scrape_year_scores(session, year):
    """Scrape tournament scores data for a specific year.

    Args:
        session: Requests session to use
        year: Year to scrape data for

    Returns:
        List of game dictionaries for the given year
    """
    games = []
    url = f"https://www.sports-reference.com/cbb/postseason/{year}-ncaa.html"
    session_request = session.get(url, params={})
    logger.debug("URL: %s", session_request.url)

    # Parse each round from HTML response
    parsed_response = BeautifulSoup(session_request.text, "html.parser")
    brackets_node = parsed_response.find(id="brackets")
    brackets_children = brackets_node.find_all(True, recursive=False)

    for bracket_child in brackets_children:
        bracket_games = _parse_bracket_games(year, bracket_child)
        games.extend(bracket_games)

    return games


def _parse_bracket_games(year, bracket_child):
    """Parse all games within a tournament bracket.

    Args:
        year: Tournament year
        bracket_child: BeautifulSoup element for the bracket

    Returns:
        List of game dictionaries for the given bracket
    """
    bracket_games = []
    bracket_id = bracket_child.get("id")
    bracket_rounds = bracket_child.find_all("div", class_="round")

    round_num = 1
    for bracket_round in bracket_rounds:
        round_children = bracket_round.find_all(True, recursive=False)
        for game_node in round_children:
            game = _parse_game(year, bracket_id, round_num, game_node)
            bracket_games.append(game)
        round_num += 1

    return bracket_games


def _parse_game(year: int, bracket_id: str, round_number: int, game_node) -> dict:
    """Parse a tournament game from HTML node.

    Extracts information about a tournament game, including participating teams,
    location, scores, and metadata.

    Args:
        year: The year of the tournament
        bracket_id: Identifier for the tournament bracket
        round_number: Round number within the tournament
        game_node: BeautifulSoup element containing the game information

    Returns:
        Dictionary containing structured game data
    """
    game = {
        "year": year,
        "bracket": bracket_id,
        "round": round_number,
    }
    game_children = game_node.find_all(True, recursive=False)
    logger.debug("len(game_children) = %s", len(game_children))
    if len(game_children) >= 1:
        game["team_a"] = _parse_team(game_children[0])
    if len(game_children) >= 2:
        game["team_b"] = _parse_team(game_children[1])
    if len(game_children) >= 3:
        location_link = game_children[2].contents[0]
        game["location"] = location_link.get_text()[len("at ") :]
    else:
        game["location"] = None
    return game


def read_write_data(data_name: str, func, *args, **kwargs) -> pd.DataFrame:
    """Read data from CSV file or generate and save it if not found.

    Attempts to read data from a CSV file with the given name. If the file
    doesn't exist, calls the provided function to generate the data and
    saves the result as a CSV file.

    Args:
        data_name: Name of the data file (without extension)
        func: Function to call to generate data if file doesn't exist
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        DataFrame containing the requested data
    """
    dataframe = pd.DataFrame()
    # Get dataframe from CSV if it exists
    if os.path.isfile(f"{DATA_PATH}/{data_name}.csv"):
        dataframe = read_df_from_csv(f"{data_name}.csv")
    # Otherwise,
    if dataframe.empty:
        logger.debug(" * Calling %s()", func.__name__)
        dataframe = pd.DataFrame(func(*args, **kwargs))
        # Write dataframe to CSV file
        write_df_to_csv(dataframe, f"{data_name}.csv")
    return dataframe


def read_df_from_csv(file_name: str) -> pd.DataFrame:
    """Read a DataFrame from a CSV file.

    Args:
        file_name: Name of the CSV file to read

    Returns:
        DataFrame containing the file data
    """
    logger.debug("Attempting to read from %s/%s", DATA_PATH, file_name)
    dataframe = pd.read_csv(f"{DATA_PATH}/{file_name}", low_memory=False)
    return dataframe


def write_df_to_csv(dataframe: pd.DataFrame, file_name: str) -> pd.DataFrame:
    """Write a DataFrame to a CSV file.

    Args:
        dataframe: DataFrame to save
        file_name: Name of the file to save to

    Returns:
        The saved DataFrame
    """
    logger.debug("Attempting to write to %s/%s", DATA_PATH, file_name)
    dataframe.to_csv(f"{DATA_PATH}/{file_name}", index=False)
    logger.debug("Successfully wrote to %s/%s!", DATA_PATH, file_name)


def _parse_team(team_node):
    """Parse team information from a tournament game HTML node.

    Extracts team details including seed, name, score, and win status.

    Args:
        team_node: BeautifulSoup element containing the team information

    Returns:
        Dictionary containing structured team data
    """
    team = {}
    classes = team_node.get("class")
    team["won"] = (classes is not None) and ("winner" in team_node.get("class"))
    team_children = team_node.find_all(True, recursive=False)
    if len(team_children) >= 1:
        team["seed"] = team_children[0].get_text()
    if len(team_children) >= 2:
        team["name"] = team_children[1].get_text()
    if len(team_children) >= 3:
        team["score"] = team_children[2].get_text()
    return team
