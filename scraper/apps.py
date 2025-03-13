"""Scraper application configuration module.

This module defines the Django app configuration for the scraper application,
which handles data scraping and processing for the March Madness project.
"""

from django.apps import AppConfig


class ScraperConfig(AppConfig):
    """Scraper application configuration class.

    Controls the Django app settings and behavior for the scraper application.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "scraper"
