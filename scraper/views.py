"""Scraper application views module.

This module contains the view functions for the scraper application,
providing HTTP endpoints to trigger data scraping operations.
"""

import logging
from http import HTTPStatus

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# pylint: disable=duplicate-code
from .task_manager import (
    TaskNotFoundError,
    cleanup_old_tasks,
    create_task,
    get_recent_tasks,
    get_task,
    run_task_in_thread,
)
from .utils import DataScrapingError, scrape_ratings, scrape_scores, scrape_stats

logger = logging.getLogger(__name__)
CURRENT_YEAR = settings.CURRENT_YEAR


@csrf_exempt  # Add CSRF exemption for API endpoints
@require_http_methods(["GET"])
def scrape_all(request, start_year=CURRENT_YEAR):
    """Scrape all data endpoint.

    Starts background tasks to gather team stats and ratings data.

    Args:
        _request: Django request object (unused)
        start_year (int): The year to begin scraping data from

    Returns:
        JsonResponse: Task ID and status information
    """
    try:
        logger.debug("Starting background task for scraper:all...")
        # Check if start_year is in query string
        if "start_year" in request.GET:
            start_year = request.GET["start_year"]

        # Try to convert to int (will raise ValueError if invalid)
        start_year = int(start_year)

        # Clean up older tasks
        cleanup_old_tasks()

        # Create a new task
        task = create_task("scrape_all", {"start_year": start_year})

        # Run the task in the background
        def run_all_scraping(year, task_id):
            """Run all scraping operations"""
            try:
                task = get_task(task_id)

                # Update the utility functions to accept task_id parameter
                scrape_stats(year, task_id)
                task.update_progress(33)  # 1/3 of the work done

                scrape_ratings(year, task_id)
                task.update_progress(66)  # 2/3 of the work done

                scrape_scores(year, task_id)
                # No need to update progress here, as task completion will set it to 100
            except (DataScrapingError, requests.RequestException) as e:
                logger.exception("Error in background scrape_all task")
                raise e
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.exception("Unexpected error in background scrape_all task")
                raise DataScrapingError(f"Unexpected error: {str(e)}") from e

        run_task_in_thread(run_all_scraping, task, start_year, task.id)

        return JsonResponse(
            {
                "success": True,
                "message": "Scraping started in the background",
                "task_id": task.id,
                "status": task.status.value,
            }
        )
    except ValueError as e:
        logger.error("Invalid year format in scrape_all endpoint: %s", str(e))
        return JsonResponse(
            {
                "success": False,
                "error": f"Invalid year format: {str(e)}",
            },
            status=HTTPStatus.BAD_REQUEST,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error in scrape_all endpoint")
        return JsonResponse(
            {
                "success": False,
                "error": f"Server error: {str(e)}",
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def scrape_stats_view(request, start_year=CURRENT_YEAR):
    """Scrape stats endpoint.

    Starts a background task to scrape team statistics data.

    Args:
        _request: Django request object (unused)
        start_year (int): The year to begin scraping stats from

    Returns:
        JsonResponse: Task ID and status information
    """
    try:
        logger.debug("Starting background task for scraper:stats...")
        # Check if start_year is in query string
        if "start_year" in request.GET:
            start_year = request.GET["start_year"]

        # Try to convert to int (will raise ValueError if invalid)
        start_year = int(start_year)

        # Clean up older tasks
        cleanup_old_tasks()

        # Create a new task
        task = create_task("scrape_stats", {"start_year": start_year})

        # Run the task in the background
        run_task_in_thread(scrape_stats, task, start_year, task.id)

        return JsonResponse(
            {
                "success": True,
                "message": "Stats scraping started in the background",
                "task_id": task.id,
                "status": task.status.value,
            }
        )
    except ValueError as e:
        logger.error("Invalid year format in scrape_stats endpoint: %s", str(e))
        return JsonResponse(
            {
                "success": False,
                "error": f"Invalid year format: {str(e)}",
            },
            status=HTTPStatus.BAD_REQUEST,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error in scrape_stats endpoint")
        return JsonResponse(
            {
                "success": False,
                "error": f"Server error: {str(e)}",
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def scrape_ratings_view(request, start_year=CURRENT_YEAR):
    """Scrape ratings endpoint.

    Starts a background task to scrape team rating data.

    Args:
        _request: Django request object (unused)
        start_year (int): The year to begin scraping ratings from

    Returns:
        JsonResponse: Task ID and status information
    """
    try:
        logger.debug("Starting background task for scraper:ratings...")
        # Check if start_year is in query string
        if "start_year" in request.GET:
            start_year = request.GET["start_year"]

        # Try to convert to int (will raise ValueError if invalid)
        start_year = int(start_year)

        # Clean up older tasks
        cleanup_old_tasks()

        # Create a new task
        task = create_task("scrape_ratings", {"start_year": start_year})

        # Run the task in the background
        run_task_in_thread(scrape_ratings, task, start_year, task.id)

        return JsonResponse(
            {
                "success": True,
                "message": "Ratings scraping started in the background",
                "task_id": task.id,
                "status": task.status.value,
            }
        )
    except ValueError as e:
        logger.error("Invalid year format in scrape_ratings endpoint: %s", str(e))
        return JsonResponse(
            {
                "success": False,
                "error": f"Invalid year format: {str(e)}",
            },
            status=HTTPStatus.BAD_REQUEST,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error in scrape_ratings endpoint")
        return JsonResponse(
            {
                "success": False,
                "error": f"Server error: {str(e)}",
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def scrape_scores_view(_request, start_year=CURRENT_YEAR):
    """Scrape scores endpoint.

    Starts a background task to scrape game scores data.

    Args:
        _request: Django request object (unused)
        start_year (int): The year to begin scraping scores from

    Returns:
        JsonResponse: Task ID and status information
    """
    try:
        logger.debug("Starting background task for scraper:scores...")
        start_year = int(start_year)

        # Clean up older tasks
        cleanup_old_tasks()

        # Create a new task
        task = create_task("scrape_scores", {"start_year": start_year})

        # Run the task in the background
        run_task_in_thread(scrape_scores, task, start_year, task.id)

        return JsonResponse(
            {
                "success": True,
                "message": "Scores scraping started in the background",
                "task_id": task.id,
                "status": task.status.value,
            }
        )
    except ValueError as e:
        logger.error("Invalid year format in scrape_scores endpoint: %s", str(e))
        return JsonResponse(
            {
                "success": False,
                "error": f"Invalid year format: {str(e)}",
            },
            status=HTTPStatus.BAD_REQUEST,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error in scrape_scores endpoint")
        return JsonResponse(
            {
                "success": False,
                "error": f"Server error: {str(e)}",
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def task_status(_request, task_id):
    """Get status of a specific task.

    Args:
        _request: Django request object (unused)
        task_id: ID of the task to check

    Returns:
        JsonResponse: Task status and details
    """
    try:
        task = get_task(task_id)
        if not task:
            return JsonResponse(
                {"success": False, "error": "Task not found"}, status=HTTPStatus.NOT_FOUND
            )

        return JsonResponse({"success": True, "task": task.to_dict()})
    except TaskNotFoundError as e:
        logger.warning("Task not found: %s", str(e))
        return JsonResponse({"success": False, "error": str(e)}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error in task_status endpoint")
        return JsonResponse(
            {
                "success": False,
                "error": f"Server error: {str(e)}",
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def recent_tasks(_request):
    """Get list of recent tasks.

    Args:
        _request: Django request object (unused)

    Returns:
        JsonResponse: List of recent tasks
    """
    try:
        tasks = get_recent_tasks(10)
        return JsonResponse({"success": True, "tasks": tasks})
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error in recent_tasks endpoint")
        return JsonResponse(
            {
                "success": False,
                "error": f"Server error: {str(e)}",
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
