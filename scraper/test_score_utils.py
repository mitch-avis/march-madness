"""Unit tests for score scraper utility functions."""

from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from django.test import TestCase

from scraper.scores_scraper import (
    _parse_bracket_games,
    _parse_game,
    _parse_team,
    _scrape_year_scores,
)

MOCK_TASK_ID = "abcdef"


class ScrapeYearScoresTests(TestCase):
    """Tests for the _scrape_year_scores function"""

    @patch("requests.Session")
    @patch("scraper.scores_scraper._parse_bracket_games")
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
            "scraper.scores_scraper.BeautifulSoup",
            return_value=BeautifulSoup(mock_response.text, "html.parser"),
        ):
            result = _scrape_year_scores(mock_session_instance, 2023, MOCK_TASK_ID)

        # Assert
        self.assertEqual(len(result), 2)  # Should have 2 games (one from each bracket)
        mock_parse_bracket_games.assert_called()
        self.assertEqual(mock_parse_bracket_games.call_count, 2)  # Called for each bracket

        # Check the arguments of the second call
        year_arg = mock_parse_bracket_games.call_args_list[1][0][0]
        self.assertEqual(year_arg, 2023)


class ParseBracketGamesTests(TestCase):
    """Tests for the _parse_bracket_games function"""

    @patch("scraper.scores_scraper._parse_game")
    def test_parse_bracket_games_calls_parse_game(self, mock_parse_game):
        """Test that _parse_bracket_games calls _parse_game correctly"""
        # Arrange
        year = 2023

        # Create a mock bracket with rounds and games
        bracket_html = """
        <div id="east">
            <div class="round1">
                <div><span>Game 1</span></div>
                <div><span>Game 2</span></div>
            </div>
            <div class="round2">
                <div><span>Game 3</span></div>
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
        result = _parse_bracket_games(year, bracket_element, MOCK_TASK_ID)

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
        team = _parse_team(team_node, MOCK_TASK_ID)

        # Assert
        self.assertIsNone(team)

    def test_parse_team_with_no_children(self):
        """Test _parse_team with no child elements"""
        # Arrange
        soup = BeautifulSoup('<div class="loser"></div>', "html.parser")
        team_node = soup.find("div")

        # Act
        team = _parse_team(team_node, MOCK_TASK_ID)

        # Assert
        self.assertIsNone(team)


class ParseGameTests(TestCase):
    """Additional tests for the _parse_game function"""

    def test_parse_team_extracts_correct_team_data(self):
        """Test team parsing function extracts seed, name, score, and winning status"""
        # Arrange
        soup = BeautifulSoup(
            '<div class="winner"><span>1</span><span>Duke</span><span>78</span></div>',
            "html.parser",
        )
        team_node = soup.find("div")

        # Act
        team = _parse_team(team_node, MOCK_TASK_ID)

        # Assert
        self.assertIsNotNone(team)
        assert team is not None
        self.assertTrue(team["won"])
        self.assertEqual(team["seed"], 1)
        self.assertEqual(team["name"], "Duke")
        self.assertEqual(team["score"], 78)

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
        mock_location.find.return_value = mock_location_link

        year = 2025
        bracket = "East"
        round_num = 1

        # Act
        with patch("scraper.scores_scraper._parse_team") as mock_parse_team:
            mock_parse_team.side_effect = [
                {"name": "Duke", "seed": 1, "won": True, "score": 78},
                {"name": "UNC", "seed": 2, "won": False, "score": 74},
            ]
            # pylint: disable=duplicate-code
            game = _parse_game(year, bracket, round_num, mock_game_node, MOCK_TASK_ID)

        # Assert
        self.assertIsNotNone(game)
        assert game is not None
        self.assertEqual(game["year"], year)
        self.assertEqual(game["bracket"], bracket)
        self.assertEqual(game["round"], round_num)
        self.assertEqual(game["team_a"]["name"], "Duke")
        self.assertEqual(game["team_b"]["name"], "UNC")
        self.assertEqual(game["location"], "New Orleans")

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
        with patch("scraper.scores_scraper._parse_team") as mock_parse_team:
            mock_parse_team.side_effect = [
                {"name": "Michigan", "seed": 1, "won": True},
                {"name": "Ohio", "seed": 8, "won": False},
            ]
            game = _parse_game(year, bracket, round_num, mock_game_node, MOCK_TASK_ID)

        # Assert
        self.assertIsNotNone(game)
        assert game is not None
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
        game = _parse_game(year, bracket, round_num, mock_game_node, MOCK_TASK_ID)

        # Assert
        self.assertIsNone(game)
