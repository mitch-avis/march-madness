"""Main URL configuration for the March Madness project.

This module defines the URL patterns for the entire project,
including patterns for the Django admin site and individual applications.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("scraper/", include("scraper.urls")),
]
