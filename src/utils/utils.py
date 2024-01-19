import os

import pandas as pd

from src import log
from src.config.definitions import Definitions
from src.config.env_config import Config

CURRENT_YEAR = Config.CURRENT_YEAR
DATA_PATH = Config.DATA_PATH
SITE_URL_PREFIX = Definitions.TR_CB_STATS_URL
STAT_NAMES = Definitions.TR_STATS
END_DATES = Definitions.END_DATES


def scrape_stats(start_year: int):
    for year in range(start_year, CURRENT_YEAR + 1):
        if year == 2020:
            continue
        all_stats = pd.DataFrame()
        for stat_name in STAT_NAMES:
            url = f"{SITE_URL_PREFIX}/{stat_name}?date={year}-03-{END_DATES[year]}"
            log.debug("Scraping from URL: %s", url)
            page = pd.read_html(url)
            current_stat = page[0]
            current_stat = current_stat.loc[:, ["Team", str(year - 1)]]
            current_stat = current_stat.rename(columns={str(year - 1): stat_name})
            if all_stats.empty:
                all_stats = current_stat
            else:
                all_stats = pd.merge(all_stats, current_stat, on="Team")
            # log.debug("Dataframe:\n%s", all_stats)
            log.debug("Successfully scraped %s", stat_name)
        log.debug("Done scraping stats for %s", year)
        write_df_to_csv(all_stats, f"TeamRankings{year}.csv")


def read_write_data(data_name: str, func, *args, **kwargs) -> pd.DataFrame:
    dataframe = pd.DataFrame()
    # Get dataframe from CSV if it exists
    if os.path.isfile(f"{DATA_PATH}/{data_name}.csv"):
        dataframe = read_df_from_csv(f"{data_name}.csv")
    # Otherwise,
    if dataframe.empty:
        log.debug(" * Calling %s()", func.__name__)
        dataframe = pd.DataFrame(func(*args, **kwargs))
        # Write dataframe to CSV file
        write_df_to_csv(dataframe, f"{data_name}.csv")
    return dataframe


def read_df_from_csv(file_name: str) -> pd.DataFrame:
    log.debug("Attempting to read from %s/%s", DATA_PATH, file_name)
    dataframe = pd.read_csv(f"{DATA_PATH}/{file_name}", low_memory=False)
    return dataframe


def write_df_to_csv(dataframe: pd.DataFrame, file_name: str) -> pd.DataFrame:
    log.debug("Attempting to write to %s/%s", DATA_PATH, file_name)
    dataframe.to_csv(f"{DATA_PATH}/{file_name}", index=False)
