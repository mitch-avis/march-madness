"""Core application URL configuration.

This module defines the URL patterns for the core application,
mapping URLs to their corresponding view functions.
"""

from django.urls import path

from . import views

# Django naming convention - keep as is
app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
]
