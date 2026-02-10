"""Task management module for background processing.

Provides functionality to track and manage asynchronous scraping tasks.
"""

import logging
import secrets
import threading
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Global tasks registry
tasks: dict[str, "Task"] = {}


class TaskError(Exception):
    """Base exception for task-related errors."""

    def __init__(self, message="Task operation failed"):
        """Initialize the error with a message."""
        self.message = message
        super().__init__(self.message)


class TaskNotFoundError(TaskError):
    """Exception raised when a requested task is not found."""

    def __init__(self, message="Task not found"):
        """Initialize the error with a message."""
        super().__init__(message)


class TaskStatus(Enum):
    """Status of a background task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class Task:
    """Represents a background task with status tracking."""

    def __init__(self, task_type: str, params: dict | None = None):
        """Initialize a new task.

        Args:
            task_type: Type of task (e.g., "scrape_stats")
            params: Parameters used for the task

        """
        self.id: str = str(secrets.token_urlsafe(6))
        self.task_type: str = task_type
        self.status: TaskStatus = TaskStatus.PENDING
        self.created_at: str = datetime.now().isoformat()
        self.started_at: str | None = None
        self.completed_at: str | None = None
        self.params: dict = params or {}
        self.error: str | None = None
        self.progress: int = 0
        self.cancelled: bool = False
        logger.debug(
            "Task %s initialized (Type: %s, Params: %s)", self.id, self.task_type, self.params
        )

    def start(self):
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now().isoformat()
        logger.info("Task %s started.", self.id)

    def complete(self, success: bool, error: str | None = None):
        """Mark task as completed.

        Args:
            success: Whether the task completed successfully
            error: Error message if task failed

        """
        if self.status != TaskStatus.CANCELLED:
            self.status = TaskStatus.SUCCESS if success else TaskStatus.FAILURE
            self.completed_at = datetime.now().isoformat()
            self.error = error
            self.progress = 100
            if success:
                logger.info("Task %s completed successfully.", self.id)
            else:
                logger.error("Task %s failed: %s", self.id, self.error)

    def update_progress(self, progress: int):
        """Update task progress percentage.

        Args:
            progress: Progress percentage (0-100)

        """
        if self.status != TaskStatus.CANCELLED:
            self.progress = min(99, max(0, progress))  # Cap between 0-99 (100 is for completion)
            logger.debug("Task %s progress updated to %d%%", self.id, self.progress)

    def cancel(self):
        """Mark the task for cancellation."""
        if self.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            self.cancelled = True
            self.status = TaskStatus.CANCELLED
            self.completed_at = datetime.now().isoformat()
            self.error = "Task cancelled by user."
            logger.info("Task %s marked for cancellation.", self.id)
        else:
            logger.debug(
                "Attempted to cancel task %s but status was %s.", self.id, self.status.value
            )

    def to_dict(self) -> dict:
        """Convert task to dictionary representation.

        Returns:
            Dictionary with task properties

        """
        return {
            "id": self.id,
            "type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "params": self.params,
            "error": self.error,
            "progress": self.progress,
        }


def create_task(task_type: str, params: dict | None = None) -> Task:
    """Create and register a new task.

    Args:
        task_type: Type of task
        params: Task parameters

    Returns:
        Newly created task

    """
    task = Task(task_type, params)
    tasks[task.id] = task
    logger.info("Created and registered task %s (Type: %s)", task.id, task.task_type)
    return task


def get_task(task_id: str) -> Task:
    """Get task by ID.

    Args:
        task_id: Task identifier

    Returns:
        Task if found.

    Raises:
        TaskNotFoundError: If the task ID is not found.

    """
    task = tasks.get(task_id)
    if not task:
        logger.debug("Attempted to get non-existent task ID: %s", task_id)
        raise TaskNotFoundError(f"Task with ID {task_id} not found")
    logger.debug("Retrieved task %s", task_id)
    return task


class TaskCancelledError(Exception):
    """Raised when a task is cancelled during execution."""


def get_recent_tasks(limit: int = 10) -> list[dict]:
    """Get recent tasks, sorted by creation time.

    Args:
        limit: Maximum number of tasks to return

    Returns:
        List of task dictionaries

    """
    logger.debug("Retrieving recent tasks (limit: %d)", limit)
    sorted_tasks = sorted(tasks.values(), key=lambda t: t.created_at, reverse=True)
    return [task.to_dict() for task in sorted_tasks[:limit]]


def cleanup_old_tasks():
    """Remove completed tasks older than 1 hour."""
    current_time = datetime.now()
    task_ids_to_remove = []
    logger.debug("Starting cleanup of old tasks.")

    for task_id, task in list(tasks.items()):  # Iterate over a copy for safe deletion
        if task.completed_at:
            try:
                completed_time = datetime.fromisoformat(task.completed_at)
                # If completed more than 1 hour ago
                if (current_time - completed_time).total_seconds() > 3600:
                    task_ids_to_remove.append(task_id)
                    logger.debug(
                        "Marking task %s for cleanup (completed at %s)", task_id, task.completed_at
                    )
            except ValueError:
                logger.warning(
                    "Task %s has invalid completed_at format: %s. Skipping cleanup check.",
                    task_id,
                    task.completed_at,
                )

    removed_count = 0
    for task_id in task_ids_to_remove:
        try:
            del tasks[task_id]
            removed_count += 1
            logger.debug("Removed task %s during cleanup.", task_id)
        except KeyError:
            # Should not happen if iterating correctly, but good for robustness
            logger.warning("Task %s already removed before cleanup.", task_id)

    if removed_count > 0:
        logger.info("Cleaned up %d old tasks.", removed_count)
    else:
        logger.debug("No old tasks found to clean up.")


def run_task_in_thread(func, task: Task, *args, **kwargs):
    """Run a function in a background thread with task tracking.

    Args:
        func: Function to run
        task: Task object to track status
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    """

    def wrapped_func():
        logger.debug("Starting thread for task %s", task.id)
        try:
            if task.cancelled:
                logger.info("Task %s was cancelled before starting execution.", task.id)
                return
            task.start()
            func(*args, **kwargs)
            if not task.cancelled:
                task.complete(True)
            else:
                logger.info(
                    "Task %s was cancelled during execution, before explicit completion.", task.id
                )
        except TaskCancelledError as e:
            logger.info("Task %s execution cancelled by TaskCancelledError: %s", task.id, e)
        except Exception as e:
            logger.exception("Unhandled error during task %s execution.", task.id)
            if task.status != TaskStatus.CANCELLED:
                task.complete(False, str(e))
        finally:
            logger.debug("Thread for task %s finished.", task.id)

    thread = threading.Thread(target=wrapped_func)
    thread.daemon = True
    thread.start()
    logger.debug("Thread created and started for task %s", task.id)
    return thread
