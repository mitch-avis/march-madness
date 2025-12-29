"""Scraper utility module."""

import logging
import os
from datetime import date, timedelta

import pandas as pd
import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Constants
CURRENT_YEAR = settings.CURRENT_YEAR
DATA_PATH = settings.DATA_PATH
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


def get_end_day(year: int) -> int:
    """Return the day-of-month in March used for end-of-season snapshots.

    Historically this corresponds to the first-round Thursday date (3rd Thursday
    of March) for the NCAA tournament. Specific years can be overridden via
    END_DATES.
    """

    override = END_DATES.get(year)
    if override is not None:
        return override

    march_first = date(year, 3, 1)
    thursday = 3  # Monday=0
    days_until_first_thursday = (thursday - march_first.weekday()) % 7
    first_thursday = march_first + timedelta(days=days_until_first_thursday)
    third_thursday = first_thursday + timedelta(days=14)
    return third_thursday.day


REQUEST_TIMEOUT = 15  # seconds
RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],  # Common transient errors
)
HTTP_ADAPTER = HTTPAdapter(max_retries=RETRY_STRATEGY)


class DataScrapingError(Exception):
    """Exception raised when data scraping operations fail."""

    def __init__(self, message="Data scraping operation failed"):
        self.message = message
        super().__init__(self.message)


def create_session() -> requests.Session:
    """Creates a requests session with retry logic."""
    session = requests.Session()
    session.mount("https://", HTTP_ADAPTER)
    session.mount("http://", HTTP_ADAPTER)
    return session


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
    """Read a DataFrame from a CSV file."""
    full_path = os.path.join(DATA_PATH, file_name)
    logger.debug("Attempting to read from %s", full_path)
    try:
        dataframe = pd.read_csv(full_path, low_memory=False)
        return dataframe
    except FileNotFoundError:
        logger.warning("CSV file not found: %s", full_path)
        return pd.DataFrame()  # Return empty DataFrame if file not found
    except Exception as e:
        logger.error("Failed to read DataFrame from %s: %s", full_path, e)
        raise  # Re-raise other exceptions


def write_df_to_csv(dataframe: pd.DataFrame, file_name: str) -> None:
    """Write a DataFrame to a CSV file."""
    full_path = os.path.join(DATA_PATH, file_name)
    logger.debug("Attempting to write to %s", full_path)
    try:
        dataframe.to_csv(full_path, index=False)
        logger.debug("Successfully wrote to %s!", full_path)
    except Exception as e:
        logger.error("Failed to write DataFrame to %s: %s", full_path, e)
        raise
