"""Core application unit tests.

This module contains test cases for the core application views and URLs,
ensuring proper functionality of the home and health endpoints.
"""

from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import resolve, reverse

from core.views import health, home


class CoreViewsTests(TestCase):
    """Tests for core views."""

    def setUp(self):
        """Set up the test client."""
        # Create test client
        self.client = Client()

    def test_home_view_returns_200_and_correct_template(self):
        """Test the home view returns successfully."""
        # Act
        response = self.client.get(reverse("core:home"))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")

    def test_health_view_returns_200_and_correct_data(self):
        """Test the health view returns correctly."""
        # Act
        response = self.client.get(reverse("core:health"))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["version"], "1.0.0")


class CoreURLsTests(TestCase):
    """Tests for URL routing in the core app."""

    def test_home_url_resolves_to_home_view(self):
        """Test the home URL resolves to the home view."""
        # Arrange
        url = reverse("core:home")

        # Act
        found = resolve(url)

        # Assert
        self.assertEqual(found.func, home)

    def test_health_url_resolves_to_health_view(self):
        """Test the health URL resolves to the health view."""
        # Arrange
        url = reverse("core:health")

        # Act
        found = resolve(url)

        # Assert
        self.assertEqual(found.func, health)


class HealthViewTests(TestCase):
    """Tests specifically for the health view function."""

    def test_health_response_has_json_content_type(self):
        """Test that the response content type is application/json."""
        # Act
        response = self.client.get(reverse("core:health"))

        # Assert
        self.assertEqual(response["Content-Type"], "application/json")

    @patch("core.views.logger")
    def test_health_logs_request(self, mock_logger):
        """Test that the logger is called when health endpoint is accessed."""
        # Act
        self.client.get(reverse("core:health"))

        # Assert
        mock_logger.debug.assert_called_once_with("Health check requested")
