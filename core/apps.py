"""Core application configuration module.

This module defines the Django app configuration for the core application,
which handles the main functionality of the March Madness project.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Core application configuration class.

    Controls the Django app settings and behavior for the core application.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
