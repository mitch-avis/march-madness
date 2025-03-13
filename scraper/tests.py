"""Scraper application unit tests.

This module contains test cases for the scraper application utilities and views,
ensuring proper functionality of the data scraping and processing endpoints.
"""

from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from django.test import TestCase

from scraper.utils import _parse_game, _parse_team


class ScraperUtilsTests(TestCase):
    """Tests for scraper utility functions"""

    def test_parse_team_extracts_correct_team_data(self):
        """Test team parsing function extracts seed, name, score, and winning status"""
        # Arrange
        soup = BeautifulSoup(
            '<div class="winner"><span>1</span><span>Duke</span><span>78</span></div>',
            "html.parser",
        )
        team_node = soup.find("div")

        # Act
        team = _parse_team(team_node)

        # Assert
        self.assertTrue(team["won"])
        self.assertEqual(team["seed"], "1")
        self.assertEqual(team["name"], "Duke")
        self.assertEqual(team["score"], "78")

    def test_parse_game_extracts_correct_game_data(self):
        """Test game parsing function extracts year, bracket, round, teams, and location"""
        # Arrange
        mock_game_node = MagicMock()
        mock_team_a = MagicMock()
        mock_team_b = MagicMock()
        mock_location = MagicMock()

        mock_game_node.find_all.return_value = [mock_team_a, mock_team_b, mock_location]

        mock_location_link = MagicMock()
        mock_location_link.get_text.return_value = "at New Orleans"
        mock_location.contents = [mock_location_link]

        year = 2025
        bracket = "East"
        round_num = 1

        # Act
        with patch("scraper.utils._parse_team") as mock_parse_team:
            mock_parse_team.side_effect = [
                {"name": "Duke", "seed": "1", "won": True, "score": "78"},
                {"name": "UNC", "seed": "2", "won": False, "score": "74"},
            ]
            # pylint: disable=duplicate-code
            game = _parse_game(year, bracket, round_num, mock_game_node)

        # Assert
        self.assertEqual(game["year"], year)
        self.assertEqual(game["bracket"], bracket)
        self.assertEqual(game["round"], round_num)
        self.assertEqual(game["team_a"]["name"], "Duke")
        self.assertEqual(game["team_b"]["name"], "UNC")
        self.assertEqual(game["location"], "New Orleans")
