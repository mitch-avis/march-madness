"""Task management module for background processing.

Provides functionality to track and manage asynchronous scraping tasks.
"""

import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

# Global tasks registry
tasks = {}


class TaskError(Exception):
    """Base exception for task-related errors."""

    def __init__(self, message="Task operation failed"):
        self.message = message
        super().__init__(self.message)


class TaskNotFoundError(TaskError):
    """Exception raised when a requested task is not found."""

    def __init__(self, message="Task not found"):
        super().__init__(message)


class TaskStatus(Enum):
    """Status of a background task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class Task:  # pylint: disable=too-many-instance-attributes
    """Represents a background task with status tracking."""

    def __init__(self, task_type: str, params: Optional[Dict] = None):
        """Initialize a new task.

        Args:
            task_type: Type of task (e.g., "scrape_stats")
            params: Parameters used for the task
        """
        self.id = str(uuid.uuid4())
        self.task_type = task_type
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.params = params or {}
        self.error = None
        self.progress = 0

    def start(self):
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now().isoformat()

    def complete(self, success: bool, error: str = None):
        """Mark task as completed.

        Args:
            success: Whether the task completed successfully
            error: Error message if task failed
        """
        self.status = TaskStatus.SUCCESS if success else TaskStatus.FAILURE
        self.completed_at = datetime.now().isoformat()
        self.error = error
        self.progress = 100

    def update_progress(self, progress: int):
        """Update task progress percentage.

        Args:
            progress: Progress percentage (0-100)
        """
        self.progress = min(99, max(0, progress))  # Cap between 0-99 (100 is for completion)

    def to_dict(self) -> Dict:
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


def create_task(task_type: str, params: Optional[Dict] = None) -> Task:
    """Create and register a new task.

    Args:
        task_type: Type of task
        params: Task parameters

    Returns:
        Newly created task
    """
    task = Task(task_type, params)
    tasks[task.id] = task
    return task


def get_task(task_id: str) -> Optional[Task]:
    """Get task by ID.

    Args:
        task_id: Task identifier

    Returns:
        Task if found, None otherwise
    """
    task = tasks.get(task_id)
    if not task:
        raise TaskNotFoundError(f"Task with ID {task_id} not found")
    return task


def get_recent_tasks(limit: int = 10) -> List[Dict]:
    """Get recent tasks, sorted by creation time.

    Args:
        limit: Maximum number of tasks to return

    Returns:
        List of task dictionaries
    """
    sorted_tasks = sorted(tasks.values(), key=lambda t: t.created_at, reverse=True)
    return [task.to_dict() for task in sorted_tasks[:limit]]


def cleanup_old_tasks():
    """Remove completed tasks older than 1 hour."""
    current_time = datetime.now()
    task_ids_to_remove = []

    for task_id, task in tasks.items():
        if task.completed_at:
            completed_time = datetime.fromisoformat(task.completed_at)
            # If completed more than 1 hour ago
            if (current_time - completed_time).total_seconds() > 3600:
                task_ids_to_remove.append(task_id)

    for task_id in task_ids_to_remove:
        del tasks[task_id]


def run_task_in_thread(func, task: Task, *args, **kwargs):
    """Run a function in a background thread with task tracking.

    Args:
        func: Function to run
        task: Task object to track status
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    """

    def wrapped_func():
        task.start()
        try:
            func(*args, **kwargs)
            task.complete(True)
        except Exception as e:
            task.complete(False, str(e))
            raise

    thread = threading.Thread(target=wrapped_func)
    thread.daemon = True
    thread.start()
    return thread
