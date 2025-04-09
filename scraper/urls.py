"""Scraper application URL configuration.

This module defines the URL patterns for the scraper application,
mapping URLs to their corresponding view functions for data scraping endpoints.
"""

from django.urls import path

from scraper import views

# Django naming convention - keep as is
app_name = "scraper"  # pylint: disable=invalid-name

urlpatterns = [
    path("all/", views.scrape_all, name="scrape_all"),
    path("all/<int:start_year>/", views.scrape_all, name="scrape_all_year"),
    path("trank/", views.scrape_trank_view, name="scrape_trank"),
    path("trank/<int:start_year>/", views.scrape_trank_view, name="scrape_trank_year"),
    path("stats/", views.scrape_stats_view, name="scrape_stats"),
    path("stats/<int:start_year>/", views.scrape_stats_view, name="scrape_stats_year"),
    path("ratings/", views.scrape_ratings_view, name="scrape_ratings"),
    path("ratings/<int:start_year>/", views.scrape_ratings_view, name="scrape_ratings_year"),
    path("scores/", views.scrape_scores_view, name="scrape_scores"),
    path("scores/<int:start_year>/", views.scrape_scores_view, name="scrape_scores_year"),
    path("tasks/<str:task_id>/cancel/", views.cancel_task_view, name="cancel_task"),
    path("tasks/<str:task_id>/", views.task_status, name="task_status"),
    path("tasks/", views.recent_tasks, name="recent_tasks"),
]
