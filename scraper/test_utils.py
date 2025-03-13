"""Unit tests for scraper utility functions.

This module tests the scraper's utility functions including data processing,
file operations, and HTML parsing.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
from bs4 import BeautifulSoup
from django.conf import settings
from django.test import TestCase

from scraper.utils import (
    DataScrapingError,
    _parse_bracket_games,
    _parse_game,
    _parse_team,
    _scrape_year_scores,
    read_df_from_csv,
    read_write_data,
    write_df_to_csv,
)


class DataScrapingErrorTests(TestCase):
    """Tests for the DataScrapingError class"""

    def test_data_scraping_error_default_message(self):
        """Test that DataScrapingError has the correct default message"""
        # Act
        error = DataScrapingError()

        # Assert
        self.assertEqual(str(error), "Data scraping operation failed")

    def test_data_scraping_error_custom_message(self):
        """Test that DataScrapingError accepts a custom message"""
        # Act
        error = DataScrapingError("Failed to scrape ratings")

        # Assert
        self.assertEqual(str(error), "Failed to scrape ratings")
        self.assertEqual(error.message, "Failed to scrape ratings")


class FileOperationsTests(TestCase):
    """Tests for file reading and writing functions"""

    @patch("pandas.read_csv")
    def test_read_df_from_csv_calls_pandas_read_csv(self, mock_read_csv):
        """Test that read_df_from_csv calls pd.read_csv with correct path"""
        # Arrange
        mock_df = MagicMock()
        mock_read_csv.return_value = mock_df

        # Act
        result = read_df_from_csv("test_file.csv")

        # Assert
        expected_path = f"{settings.DATA_PATH}/test_file.csv"
        mock_read_csv.assert_called_once_with(expected_path, low_memory=False)
        self.assertEqual(result, mock_df)

    @patch("pandas.DataFrame.to_csv")
    def test_write_df_to_csv_calls_dataframe_to_csv(self, _mock_to_csv):
        """Test that write_df_to_csv calls df.to_csv with correct path"""
        # Arrange
        mock_df = MagicMock(spec=pd.DataFrame)

        # Act
        write_df_to_csv(mock_df, "test_output.csv")

        # Assert
        expected_path = f"{settings.DATA_PATH}/test_output.csv"
        mock_df.to_csv.assert_called_once_with(expected_path, index=False)

    @patch("os.path.isfile")
    @patch("scraper.utils.read_df_from_csv")
    @patch("scraper.utils.write_df_to_csv")
    def test_read_write_data_uses_existing_file(self, _mock_write_df, mock_read_df, mock_isfile):
        """Test that read_write_data uses existing file when available"""
        # Arrange
        mock_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        mock_isfile.return_value = True
        mock_read_df.return_value = mock_df
        mock_func = MagicMock()

        # Act
        result = read_write_data("test_data", mock_func, "arg1", kwarg1="value")

        # Assert
        mock_isfile.assert_called_once_with(f"{settings.DATA_PATH}/test_data.csv")
        mock_read_df.assert_called_once_with("test_data.csv")
        mock_func.assert_not_called()  # Function should not be called when file exists
        pd.testing.assert_frame_equal(result, mock_df)

    @patch("os.path.isfile")
    @patch("scraper.utils.read_df_from_csv")
    @patch("scraper.utils.write_df_to_csv")
    def test_read_write_data_generates_new_data(self, mock_write_df, mock_read_df, mock_isfile):
        """Test that read_write_data generates new data when file doesn't exist"""
        # Arrange
        mock_isfile.return_value = False
        mock_read_df.return_value = pd.DataFrame()  # Empty dataframe

        # Function should return a list of dicts that gets converted to DataFrame
        func_result = [{"col1": 10, "col2": 20}, {"col1": 30, "col2": 40}]
        mock_func = MagicMock(return_value=func_result)
        mock_func.__name__ = "mock_func"  # Set the __name__ attribute

        # Act
        read_write_data("test_data", mock_func, "arg1", kwarg1="value")

        # Assert
        mock_isfile.assert_called_once_with(f"{settings.DATA_PATH}/test_data.csv")
        mock_func.assert_called_once_with("arg1", kwarg1="value")

        # Check that the result was written to a file
        expected_df = pd.DataFrame(func_result)
        mock_write_df.assert_called_once()
        # Compare the first argument (DataFrame) of the first call
        called_df = mock_write_df.call_args[0][0]
        pd.testing.assert_frame_equal(called_df, expected_df)


class ScrapeYearScoresTests(TestCase):
    """Tests for the _scrape_year_scores function"""

    @patch("requests.Session")
    @patch("scraper.utils._parse_bracket_games")
    def test_scrape_year_scores_calls_parse_bracket_games(
        self, mock_parse_bracket_games, _mock_session
    ):
        """Test that _scrape_year_scores calls _parse_bracket_games correctly"""
        # Arrange
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <div id="brackets">
                    <div id="east">East Bracket</div>
                    <div id="west">West Bracket</div>
                </div>
            </body>
        </html>
        """
        mock_session_instance.get.return_value = mock_response

        # Mock parse_bracket_games to return some games
        mock_parse_bracket_games.side_effect = [
            [{"year": 2023, "bracket": "east", "game": 1}],
            [{"year": 2023, "bracket": "west", "game": 2}],
        ]

        # Act
        with patch(
            "scraper.utils.BeautifulSoup",
            return_value=BeautifulSoup(mock_response.text, "html.parser"),
        ):
            result = _scrape_year_scores(mock_session_instance, 2023)

        # Assert
        self.assertEqual(len(result), 2)  # Should have 2 games (one from each bracket)
        mock_parse_bracket_games.assert_called()
        self.assertEqual(mock_parse_bracket_games.call_count, 2)  # Called for each bracket

        # Check the arguments of the second call
        year_arg = mock_parse_bracket_games.call_args_list[1][0][0]
        self.assertEqual(year_arg, 2023)


class ParseBracketGamesTests(TestCase):
    """Tests for the _parse_bracket_games function"""

    @patch("scraper.utils._parse_game")
    def test_parse_bracket_games_calls_parse_game(self, mock_parse_game):
        """Test that _parse_bracket_games calls _parse_game correctly"""
        # Arrange
        year = 2023

        # Create a mock bracket with rounds and games
        bracket_html = """
        <div id="east">
            <div class="round">
                <div class="game">Game 1</div>
                <div class="game">Game 2</div>
            </div>
            <div class="round">
                <div class="game">Game 3</div>
            </div>
        </div>
        """
        bracket_element = BeautifulSoup(bracket_html, "html.parser").find("div")

        # Mock _parse_game to return game data
        mock_parse_game.side_effect = [
            {"year": 2023, "bracket": "east", "round": 1, "game_id": 1},
            {"year": 2023, "bracket": "east", "round": 1, "game_id": 2},
            {"year": 2023, "bracket": "east", "round": 2, "game_id": 3},
        ]

        # Act
        result = _parse_bracket_games(year, bracket_element)

        # Assert
        self.assertEqual(len(result), 3)  # Should parse all 3 games
        self.assertEqual(mock_parse_game.call_count, 3)

        # Check arguments of the calls to _parse_game
        first_call_args = mock_parse_game.call_args_list[0][0]
        self.assertEqual(first_call_args[0], 2023)  # year
        self.assertEqual(first_call_args[1], "east")  # bracket_id
        self.assertEqual(first_call_args[2], 1)  # round_num

        # Check the last game is from round 2
        last_call_args = mock_parse_game.call_args_list[2][0]
        self.assertEqual(last_call_args[2], 2)  # round_num


class ParseTeamTests(TestCase):
    """Additional tests for the _parse_team function"""

    def test_parse_team_with_missing_elements(self):
        """Test _parse_team with missing team elements"""
        # Arrange - Create a team node with only seed (no name or score)
        soup = BeautifulSoup("<div><span>4</span></div>", "html.parser")
        team_node = soup.find("div")

        # Act
        team = _parse_team(team_node)

        # Assert
        self.assertEqual(team["seed"], "4")
        self.assertNotIn("name", team)  # Name should not be present
        self.assertNotIn("score", team)  # Score should not be present
        self.assertFalse(team["won"])  # Should not be marked as winner

    def test_parse_team_with_no_children(self):
        """Test _parse_team with no child elements"""
        # Arrange
        soup = BeautifulSoup('<div class="loser"></div>', "html.parser")
        team_node = soup.find("div")

        # Act
        team = _parse_team(team_node)

        # Assert
        self.assertFalse(team["won"])  # Should not be marked as winner
        # Should not have any of the optional fields
        self.assertNotIn("seed", team)
        self.assertNotIn("name", team)
        self.assertNotIn("score", team)


class ParseGameTests(TestCase):
    """Additional tests for the _parse_game function"""

    def test_parse_game_with_no_location(self):
        """Test _parse_game with missing location information"""
        # Arrange
        mock_game_node = MagicMock()
        # Just 2 child elements (team A and B), no location
        mock_team_a = MagicMock()
        mock_team_b = MagicMock()
        mock_game_node.find_all.return_value = [mock_team_a, mock_team_b]

        year = 2023
        bracket = "Midwest"
        round_num = 2

        # Act
        with patch("scraper.utils._parse_team") as mock_parse_team:
            mock_parse_team.side_effect = [
                {"name": "Michigan", "seed": "1", "won": True},
                {"name": "Ohio", "seed": "8", "won": False},
            ]
            game = _parse_game(year, bracket, round_num, mock_game_node)

        # Assert
        self.assertEqual(game["year"], year)
        self.assertEqual(game["bracket"], bracket)
        self.assertEqual(game["round"], round_num)
        self.assertEqual(game["team_a"]["name"], "Michigan")
        self.assertEqual(game["team_b"]["name"], "Ohio")
        self.assertIsNone(game["location"])  # Location should be None

    def test_parse_game_with_only_one_team(self):
        """Test _parse_game with only one team (e.g., forfeit)"""
        # Arrange
        mock_game_node = MagicMock()
        # Just 1 child element (team A), no team B or location
        mock_team_a = MagicMock()
        mock_game_node.find_all.return_value = [mock_team_a]

        year = 2023
        bracket = "South"
        round_num = 1

        # Act
        with patch("scraper.utils._parse_team") as mock_parse_team:
            # pylint: disable=duplicate-code
            mock_parse_team.return_value = {"name": "Duke", "seed": "2", "won": True}
            game = _parse_game(year, bracket, round_num, mock_game_node)

        # Assert
        self.assertEqual(game["year"], year)
        self.assertEqual(game["bracket"], bracket)
        self.assertEqual(game["round"], round_num)
        self.assertEqual(game["team_a"]["name"], "Duke")
        self.assertNotIn("team_b", game)  # No team B should be present
        self.assertIsNone(game["location"])  # Location should be None
