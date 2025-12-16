"""
Module to aggregate/concatenate scraped datasets for a given year.

This module reads the three CSV files for a given year:
    - TRank{year}.csv
    - TeamRankingsRatings{year}.csv
    - TeamRankingsStats{year}.csv

It verifies that each file exists and contains data; otherwise, it raises an exception
indicating the missing dataset and year. Then it merges the datasets on the "Team" column,
standardizes team names using a TEAM_ALIASES mapping, and saves a combined CSV file named
"Combined<year>.csv" in the DATA_PATH folder.
"""

import pandas as pd

from scraper.utils import read_df_from_csv, write_df_to_csv

# A constant mapping canonical team names to a set of known aliases.
TEAM_ALIASES = {
    "Michigan St.": {"Michigan St.", "Michigan State", "Mich St", "MSU"},
    "Duke": {"Duke"},
    "UNC": {"North Carolina", "UNC", "Tar Heels"},
    # Add additional teams and their aliases here...
}


class MissingDatasetError(Exception):
    """Exception raised when a required scraped dataset is missing."""


def standardize_team_name(team_name: str) -> str:
    """
    Standardize the team name using the TEAM_ALIASES mapping.

    If the team name is found in any alias set, the canonical name is returned.
    Otherwise, the original team name is retained.
    """
    for canonical, aliases in TEAM_ALIASES.items():
        if team_name.strip() in aliases:
            return canonical
    return team_name.strip()


def aggregate_year_data(year: int) -> pd.DataFrame:
    """
    Aggregate the three datasets (TRank, TeamRankingsRatings, TeamRankingsStats)
    for the given year.

    Reads the individual CSV files from DATA_PATH, verifies they contain data,
    then merges them on the "Team" column using an outer join.

    Standardizes team names based on TEAM_ALIASES.

    Saves the combined DataFrame as "Combined<year>.csv".
    Throws MissingDatasetError if any required dataset is empty.
    """
    # Define expected filenames
    trank_file = f"TRank{year}.csv"
    ratings_file = f"TeamRankingsRatings{year}.csv"
    stats_file = f"TeamRankingsStats{year}.csv"

    # Read the CSV files using the utility function.
    df_trank = read_df_from_csv(trank_file)
    if df_trank.empty:
        raise MissingDatasetError(
            f"Dataset '{trank_file}' for year {year} is missing. Please (re)scrape it."
        )

    df_ratings = read_df_from_csv(ratings_file)
    if df_ratings.empty:
        raise MissingDatasetError(
            f"Dataset '{ratings_file}' for year {year} is missing. Please (re)scrape it."
        )

    df_stats = read_df_from_csv(stats_file)
    if df_stats.empty:
        raise MissingDatasetError(
            f"Dataset '{stats_file}' for year {year} is missing. Please (re)scrape it."
        )

    # Merge datasets on the "Team" column. We assume that each CSV has a "Team" column.
    combined = pd.merge(df_trank, df_ratings, on="Team", how="outer")
    combined = pd.merge(combined, df_stats, on="Team", how="outer")

    # Standardize team names using TEAM_ALIASES mapping.
    if "Team" in combined.columns:
        combined["Team"] = combined["Team"].apply(standardize_team_name)

    # Save the combined data to a CSV file, e.g. "Combined2008.csv"
    combined_filename = f"Combined{year}.csv"
    write_df_to_csv(combined, combined_filename)

    return combined


def aggregate_all_years(start_year: int, end_year: int) -> None:
    """
    Aggregate datasets for each year from start_year to end_year.

    Iterates over each year and calls aggregate_year_data.
    Any missing dataset will result in an exception.
    """
    for year in range(start_year, end_year + 1):
        try:
            aggregate_year_data(year)
            print(f"Aggregated data for year {year} saved successfully.")
        except MissingDatasetError as e:
            print(f"Error for year {year}: {str(e)}")
            # Optionally, re-raise the error if you want to stop processing further years.
            raise


# Example usage:
if __name__ == "__main__":
    try:
        # For demonstration, aggregate from START_YEAR defined in settings to the current year.
        from django.conf import settings

        start = settings.START_YEAR
        end = settings.CURRENT_SEASON
        aggregate_all_years(start, end)
    except Exception as e:
        print(f"Aggregation failed: {e}")
