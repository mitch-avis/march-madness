"""Unit tests for scraper view functions.

This module tests the HTTP endpoints provided by the scraper application,
ensuring proper handling of requests, errors, and background task management.
"""

from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from scraper.task_manager import TaskNotFoundError, TaskStatus, tasks


class ScrapeAllViewTests(TestCase):
    """Tests for the scrape_all view function."""

    def setUp(self):
        """Set up test client and clear tasks registry."""
        self.client = Client()
        tasks.clear()

    def tearDown(self):
        """Clean up tasks registry after tests."""
        tasks.clear()

    @patch("scraper.views.run_task_in_thread")
    @patch("scraper.views.create_task")
    @patch("scraper.views.cleanup_old_tasks")
    def test_scrape_all_success_response(self, mock_cleanup, mock_create, mock_run):
        """Test successful response from scrape_all view."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status.value = TaskStatus.PENDING.value
        mock_create.return_value = mock_task

        # Act
        response = self.client.get(reverse("scraper:scrape_all"))

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["task_id"], "test-task-id")
        self.assertEqual(data["status"], TaskStatus.PENDING.value)
        mock_cleanup.assert_called_once()
        mock_create.assert_called_once_with(
            "scrape_all",
            {"start_year": settings.CURRENT_YEAR, "end_year": settings.CURRENT_YEAR},
        )
        mock_run.assert_called_once()

    @patch("scraper.views.run_task_in_thread")
    @patch("scraper.views.create_task")
    def test_scrape_all_with_custom_year(self, mock_create, _mock_run):
        """Test scrape_all with a custom year parameter."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status.value = TaskStatus.PENDING.value
        mock_create.return_value = mock_task

        # Act
        response = self.client.get(reverse("scraper:scrape_all_year", args=[2023]))

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        mock_create.assert_called_once_with(
            "scrape_all", {"start_year": 2023, "end_year": settings.CURRENT_YEAR}
        )

    def test_scrape_all_with_invalid_year(self):
        """Test scrape_all with an invalid year parameter."""
        # Act
        response = self.client.get(reverse("scraper:scrape_all") + "?start_year=invalid")

        # Assert
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid year format", data["error"])

    @patch("scraper.views.create_task")
    def test_scrape_all_with_unexpected_error(self, mock_create):
        """Test scrape_all with an unexpected error during processing."""
        # Arrange
        mock_create.side_effect = Exception("Unexpected error")

        # Act
        response = self.client.get(reverse("scraper:scrape_all"))

        # Assert
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])


class ScrapeStatsViewTests(TestCase):
    """Tests for the scrape_stats_view function."""

    def setUp(self):
        """Set up test client and clear tasks registry."""
        self.client = Client()
        tasks.clear()

    def tearDown(self):
        """Clean up tasks registry after tests."""
        tasks.clear()

    @patch("scraper.views.run_task_in_thread")
    @patch("scraper.views.create_task")
    def test_scrape_stats_view_success(self, mock_create, mock_run):
        """Test successful response from scrape_stats_view."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "stats-task-id"
        mock_task.status.value = TaskStatus.PENDING.value
        mock_create.return_value = mock_task

        # Act
        response = self.client.get(reverse("scraper:scrape_stats"))

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["task_id"], "stats-task-id")
        self.assertEqual(data["status"], TaskStatus.PENDING.value)
        mock_create.assert_called_once_with(
            "scrape_stats",
            {"start_year": settings.CURRENT_YEAR, "end_year": settings.CURRENT_YEAR},
        )
        mock_run.assert_called_once()

    @patch("scraper.views.run_task_in_thread")
    @patch("scraper.views.create_task")
    def test_scrape_stats_view_custom_year(self, mock_create, _mock_run):
        """Test scrape_stats_view with a custom year parameter."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "stats-task-id"
        mock_task.status.value = TaskStatus.PENDING.value
        mock_create.return_value = mock_task

        # Act
        response = self.client.get(reverse("scraper:scrape_stats_year", args=[2022]))

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        mock_create.assert_called_once_with(
            "scrape_stats", {"start_year": 2022, "end_year": settings.CURRENT_YEAR}
        )

    def test_scrape_stats_view_invalid_year(self):
        """Test scrape_stats_view with an invalid year parameter."""
        # Act
        response = self.client.get(reverse("scraper:scrape_stats") + "?start_year=abc")

        # Assert
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid year format", data["error"])

    @patch("scraper.views.create_task")
    def test_scrape_stats_view_unexpected_error(self, mock_create):
        """Test scrape_stats_view with an unexpected error during processing."""
        # Arrange
        mock_create.side_effect = Exception("Unexpected error")

        # Act
        response = self.client.get(reverse("scraper:scrape_stats"))

        # Assert
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])


class ScrapeRatingsViewTests(TestCase):
    """Tests for the scrape_ratings_view function."""

    def setUp(self):
        """Set up test client and clear tasks registry."""
        self.client = Client()
        tasks.clear()

    def tearDown(self):
        """Clean up tasks registry after tests."""
        tasks.clear()

    @patch("scraper.views.run_task_in_thread")
    @patch("scraper.views.create_task")
    def test_scrape_ratings_view_success(self, mock_create, mock_run):
        """Test successful response from scrape_ratings_view."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "ratings-task-id"
        mock_task.status.value = TaskStatus.PENDING.value
        mock_create.return_value = mock_task

        # Act
        response = self.client.get(reverse("scraper:scrape_ratings"))

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["task_id"], "ratings-task-id")
        mock_create.assert_called_once_with(
            "scrape_ratings",
            {"start_year": settings.CURRENT_YEAR, "end_year": settings.CURRENT_YEAR},
        )
        mock_run.assert_called_once()

    def test_scrape_ratings_view_invalid_year(self):
        """Test scrape_ratings_view with an invalid year parameter."""
        # Act
        response = self.client.get(reverse("scraper:scrape_ratings") + "?start_year=invalid")

        # Assert
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])


class ScrapeScoresViewTests(TestCase):
    """Tests for the scrape_scores_view function."""

    def setUp(self):
        """Set up test client and clear tasks registry."""
        self.client = Client()
        tasks.clear()

    def tearDown(self):
        """Clean up tasks registry after tests."""
        tasks.clear()

    @patch("scraper.views.run_task_in_thread")
    @patch("scraper.views.create_task")
    def test_scrape_scores_view_success(self, mock_create, _mock_run):
        """Test successful response from scrape_scores_view."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "scores-task-id"
        mock_task.status.value = TaskStatus.PENDING.value
        mock_create.return_value = mock_task

        # Act
        response = self.client.get(reverse("scraper:scrape_scores"))

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["task_id"], "scores-task-id")
        mock_create.assert_called_once_with(
            "scrape_scores",
            {"start_year": settings.CURRENT_YEAR, "end_year": settings.CURRENT_YEAR},
        )

    @patch("scraper.views.create_task")
    def test_scrape_scores_view_unexpected_error(self, mock_create):
        """Test scrape_scores_view with an unexpected error during processing."""
        # Arrange
        mock_create.side_effect = Exception("Unexpected error")

        # Act
        response = self.client.get(reverse("scraper:scrape_scores"))

        # Assert
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data["success"])


class TaskStatusViewTests(TestCase):
    """Tests for the task_status view function."""

    def setUp(self):
        """Set up test client and clear tasks registry."""
        self.client = Client()
        tasks.clear()

    def tearDown(self):
        """Clean up tasks registry after tests."""
        tasks.clear()

    @patch("scraper.views.get_task")
    def test_task_status_success(self, mock_get_task):
        """Test successful response when retrieving task status."""
        # Arrange
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "id": "test-task-id",
            "type": "scrape_all",
            "status": "running",
            "progress": 50,
        }
        mock_get_task.return_value = mock_task

        # Act
        response = self.client.get(reverse("scraper:task_status", args=["test-task-id"]))

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["task"]["id"], "test-task-id")
        self.assertEqual(data["task"]["status"], "running")
        mock_get_task.assert_called_once_with("test-task-id")

    @patch("scraper.views.get_task")
    def test_task_status_not_found(self, mock_get_task):
        """Test response when task is not found."""
        # Arrange
        mock_get_task.side_effect = TaskNotFoundError("Task not found")

        # Act
        response = self.client.get(reverse("scraper:task_status", args=["nonexistent-task"]))

        # Assert
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Task not found", data["error"])

    @patch("scraper.views.get_task")
    def test_task_status_unexpected_error(self, mock_get_task):
        """Test response when unexpected error occurs."""
        # Arrange
        mock_get_task.side_effect = Exception("Unexpected error")

        # Act
        response = self.client.get(reverse("scraper:task_status", args=["test-task-id"]))

        # Assert
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])


class RecentTasksViewTests(TestCase):
    """Tests for the recent_tasks view function."""

    def setUp(self):
        """Set up test client and clear tasks registry."""
        self.client = Client()
        tasks.clear()

    def tearDown(self):
        """Clean up tasks registry after tests."""
        tasks.clear()

    @patch("scraper.views.get_recent_tasks")
    def test_recent_tasks_success(self, mock_get_recent):
        """Test successful response when retrieving recent tasks."""
        # Arrange
        mock_tasks = [
            {"id": "task-1", "type": "scrape_all", "status": "success"},
            {"id": "task-2", "type": "scrape_stats", "status": "running"},
        ]
        mock_get_recent.return_value = mock_tasks

        # Act
        response = self.client.get(reverse("scraper:recent_tasks"))

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["tasks"]), 2)
        self.assertEqual(data["tasks"][0]["id"], "task-1")
        self.assertEqual(data["tasks"][1]["id"], "task-2")
        mock_get_recent.assert_called_once_with(10)

    @patch("scraper.views.get_recent_tasks")
    def test_recent_tasks_unexpected_error(self, mock_get_recent):
        """Test response when unexpected error occurs."""
        # Arrange
        mock_get_recent.side_effect = Exception("Unexpected error")

        # Act
        response = self.client.get(reverse("scraper:recent_tasks"))

        # Assert
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data["success"])
