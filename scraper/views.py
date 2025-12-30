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

from scraper.scores_scraper import scrape_scores
from scraper.task_manager import (
    Task,
    TaskCancelledError,
    TaskNotFoundError,
    cleanup_old_tasks,
    create_task,
    get_recent_tasks,
    get_task,
    run_task_in_thread,
)
from scraper.tr_scraper import scrape_ratings, scrape_stats
from scraper.utils import DataScrapingError

logger = logging.getLogger(__name__)


def _parse_year_param(value: str, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid year format for {name}.") from e


def _determine_year_range(
    request, path_start_year: int | None, path_end_year: int | None
) -> tuple[int, int]:
    """Determines the effective start and end years from query or path parameters."""
    current_year = settings.CURRENT_YEAR
    start_year_str = request.GET.get("start_year")
    end_year_str = request.GET.get("end_year")
    if start_year_str:
        start_year = _parse_year_param(start_year_str, "start_year")
    elif path_start_year is not None:
        start_year = int(path_start_year)
    else:
        start_year = current_year

    if end_year_str:
        end_year = _parse_year_param(end_year_str, "end_year")
    elif path_end_year is not None:
        end_year = int(path_end_year)
    else:
        end_year = current_year

    if start_year > end_year:
        raise ValueError("Start year cannot be after end year.")
    if end_year > current_year:
        raise ValueError(f"End year ({end_year}) cannot be after current year ({current_year}).")
    return start_year, end_year


def _scrape_single_year(task: Task, year: int, total_operations: int, operations_done: int) -> int:
    """Performs all scraping operations for a single year and updates progress."""
    operations = [
        ("Stats", scrape_stats),
        ("Ratings", scrape_ratings),
    ]

    for op_name, scrape_func in operations:
        if task.cancelled:
            raise TaskCancelledError(
                f"Task {task.id} cancelled before scraping {op_name} for {year}."
            )
        logger.debug("Task %s: Scraping %s for %d", task.id, op_name, year)
        scrape_func(year)
        operations_done += 1
        current_progress = (operations_done / total_operations) * 100
        task.update_progress(int(current_progress))
        logger.debug(
            "Task %s: Progress after %s(%d): %.2f%%",
            task.id,
            op_name,
            year,
            current_progress,
        )
    return operations_done


def _run_all_scraping_task(start_yr: int, end_yr: int, task_id: str):
    """Background task function to run all scraping operations."""
    task = None
    try:
        task = get_task(task_id)
        if not task:
            logger.error("Task %s not found inside _run_all_scraping_task", task_id)
            return

        years_to_process = [y for y in range(start_yr, end_yr + 1) if y != 2020]
        num_years = len(years_to_process)
        operations_per_year = 2  # Stats, Ratings
        total_operations = num_years * operations_per_year

        if total_operations == 0:
            logger.info(
                "Task %s: No years to process in the range %d-%d. Task complete.",
                task_id,
                start_yr,
                end_yr,
            )
            return

        logger.info(
            "Task %s: Processing %d years (%d total operations).",
            task_id,
            num_years,
            total_operations,
        )
        operations_done = 0
        for year in years_to_process:
            if task.cancelled:
                raise TaskCancelledError(f"Task {task.id} cancelled before processing year {year}.")
            logger.info("Task %s: Processing year %d...", task_id, year)
            operations_done = _scrape_single_year(task, year, total_operations, operations_done)
        logger.info("Task %s: Finished processing all years.", task_id)

    except TaskCancelledError as e:
        logger.info("Task %s cancelled: %s", task_id, e)
    except (DataScrapingError, requests.RequestException) as e:
        logger.exception("Scraping error during background scrape_all task %s", task_id)
        raise e
    except TaskNotFoundError:
        logger.error("Task %s was not found during execution.", task_id)
    except Exception as e:
        logger.exception("Unexpected error in background scrape_all task %s", task_id)
        raise DataScrapingError(f"Unexpected error: {str(e)}") from e


@csrf_exempt
@require_http_methods(["GET"])
def scrape_all(request, start_year=None, end_year=None):
    """Scrape all data endpoint."""
    try:
        effective_start_year, effective_end_year = _determine_year_range(
            request, start_year, end_year
        )
        logger.info(
            "Initiating background task for scraper:all for years %d to %d...",
            effective_start_year,
            effective_end_year,
        )
        cleanup_old_tasks()
        task = create_task(
            "scrape_all", {"start_year": effective_start_year, "end_year": effective_end_year}
        )
        run_task_in_thread(
            _run_all_scraping_task, task, effective_start_year, effective_end_year, task.id
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Scraping started in the background",
                "task_id": task.id,
                "status": task.status.value,
            }
        )

    except ValueError as e:
        logger.warning("Invalid year range in scrape_all: %s", str(e))
        return JsonResponse({"success": False, "error": str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        logger.exception("Unexpected error in scrape_all endpoint")
        return JsonResponse(
            {"success": False, "error": f"Server error: {str(e)}"},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def scrape_stats_view(request, start_year=None, end_year=None):
    """Scrape stats endpoint."""
    try:
        effective_start_year, effective_end_year = _determine_year_range(
            request, start_year, end_year
        )
        logger.info(
            "Starting background task for scraper:stats for years %d to %d...",
            effective_start_year,
            effective_end_year,
        )
        cleanup_old_tasks()
        task = create_task(
            "scrape_stats", {"start_year": effective_start_year, "end_year": effective_end_year}
        )
        run_task_in_thread(
            scrape_stats, task, effective_start_year, effective_end_year, task_id=task.id
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Stats scraping started",
                "task_id": task.id,
                "status": task.status.value,
            }
        )

    except ValueError as e:
        logger.warning("Invalid year range in scrape_stats: %s", str(e))
        return JsonResponse({"success": False, "error": str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        logger.exception("Unexpected error in scrape_stats endpoint")
        return JsonResponse(
            {"success": False, "error": f"Server error: {str(e)}"},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def scrape_ratings_view(request, start_year=None, end_year=None):
    """Scrape ratings endpoint."""
    try:
        effective_start_year, effective_end_year = _determine_year_range(
            request, start_year, end_year
        )
        logger.info(
            "Starting background task for scraper:ratings for years %d to %d...",
            effective_start_year,
            effective_end_year,
        )
        cleanup_old_tasks()
        task = create_task(
            "scrape_ratings", {"start_year": effective_start_year, "end_year": effective_end_year}
        )
        run_task_in_thread(
            scrape_ratings, task, effective_start_year, effective_end_year, task_id=task.id
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Ratings scraping started",
                "task_id": task.id,
                "status": task.status.value,
            }
        )

    except ValueError as e:
        logger.warning("Invalid year range in scrape_ratings: %s", str(e))
        return JsonResponse({"success": False, "error": str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        logger.exception("Unexpected error in scrape_ratings endpoint")
        return JsonResponse(
            {"success": False, "error": f"Server error: {str(e)}"},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def scrape_scores_view(request, start_year=None, end_year=None):
    """Scrape scores endpoint."""
    try:
        effective_start_year, effective_end_year = _determine_year_range(
            request, start_year, end_year
        )
        logger.info(
            "Starting background task for scraper:scores for years %d to %d...",
            effective_start_year,
            effective_end_year,
        )
        cleanup_old_tasks()
        task = create_task(
            "scrape_scores", {"start_year": effective_start_year, "end_year": effective_end_year}
        )
        run_task_in_thread(
            scrape_scores, task, effective_start_year, effective_end_year, task_id=task.id
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Scores scraping started",
                "task_id": task.id,
                "status": task.status.value,
            }
        )

    except ValueError as e:
        logger.warning("Invalid year range in scrape_scores: %s", str(e))
        return JsonResponse({"success": False, "error": str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        logger.exception("Unexpected error in scrape_scores endpoint")
        return JsonResponse(
            {"success": False, "error": f"Server error: {str(e)}"},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["POST"])
def cancel_task_view(_request, task_id):
    """Cancel a running or pending task."""
    try:
        task = get_task(task_id)
        task.cancel()
        return JsonResponse({"success": True, "message": f"Task {task_id} cancellation requested."})
    except TaskNotFoundError as e:
        logger.warning("Cancel request for non-existent task %s: %s", task_id, str(e))
        return JsonResponse({"success": False, "error": str(e)}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        logger.exception("Error cancelling task %s", task_id)
        return JsonResponse(
            {"success": False, "error": f"Server error: {str(e)}"},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def task_status(_request, task_id):
    """Get status of a specific task."""
    try:
        task = get_task(task_id)
        logger.debug("Retrieved status for task %s", task_id)
        return JsonResponse({"success": True, "task": task.to_dict()})
    except TaskNotFoundError as e:
        logger.warning("Task not found request: %s", str(e))
        return JsonResponse({"success": False, "error": str(e)}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        logger.exception("Unexpected error in task_status endpoint")
        return JsonResponse(
            {"success": False, "error": f"Server error: {str(e)}"},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@csrf_exempt
@require_http_methods(["GET"])
def recent_tasks(_request):
    """Get list of recent tasks."""
    try:
        tasks_list = get_recent_tasks(10)
        logger.debug("Retrieved %d recent tasks", len(tasks_list))
        return JsonResponse({"success": True, "tasks": tasks_list})
    except Exception as e:
        logger.exception("Unexpected error in recent_tasks endpoint")
        return JsonResponse(
            {"success": False, "error": f"Server error: {str(e)}"},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
