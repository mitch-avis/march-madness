"""Unit tests for task manager module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase

# pylint: disable=duplicate-code
from scraper.task_manager import (
    Task,
    TaskError,
    TaskNotFoundError,
    TaskStatus,
    cleanup_old_tasks,
    create_task,
    get_recent_tasks,
    get_task,
    run_task_in_thread,
    tasks,
)


class TaskTests(TestCase):
    """Tests for the Task class"""

    def setUp(self):
        """Reset the tasks registry before each test"""
        tasks.clear()

    def test_task_initialization(self):
        """Test that a task is properly initialized with default values"""
        # Act
        task = Task("test_task", {"param": "value"})

        # Assert
        self.assertEqual(task.task_type, "test_task")
        self.assertEqual(task.params, {"param": "value"})
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertIsNone(task.started_at)
        self.assertIsNone(task.completed_at)
        self.assertEqual(task.progress, 0)
        self.assertIsNone(task.error)

    def test_task_start_updates_status_and_timestamp(self):
        """Test that starting a task updates its status and timestamp"""
        # Arrange
        task = Task("test_task")

        # Act
        task.start()

        # Assert
        self.assertEqual(task.status, TaskStatus.RUNNING)
        self.assertIsNotNone(task.started_at)
        # Verify timestamp format is ISO
        try:
            datetime.fromisoformat(task.started_at)
            format_valid = True
        except ValueError:
            format_valid = False
        self.assertTrue(format_valid, "Started timestamp is not in ISO format")

    def test_task_complete_success_updates_status(self):
        """Test that completing a task successfully updates status"""
        # Arrange
        task = Task("test_task")

        # Act
        task.complete(True)

        # Assert
        self.assertEqual(task.status, TaskStatus.SUCCESS)
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(task.progress, 100)
        self.assertIsNone(task.error)

    def test_task_complete_failure_updates_status_and_error(self):
        """Test that completing a task with failure sets error message"""
        # Arrange
        task = Task("test_task")
        error_msg = "Task failed"

        # Act
        task.complete(False, error_msg)

        # Assert
        self.assertEqual(task.status, TaskStatus.FAILURE)
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.error, error_msg)

    def test_task_update_progress_within_bounds(self):
        """Test that updating progress works within expected bounds"""
        # Arrange
        task = Task("test_task")

        # Act & Assert - Test progress updates
        task.update_progress(50)
        self.assertEqual(task.progress, 50)

        # Test upper bound cap at 99
        task.update_progress(150)
        self.assertEqual(task.progress, 99)

        # Test lower bound at 0
        task.update_progress(-10)
        self.assertEqual(task.progress, 0)

    def test_task_to_dict_returns_all_fields(self):
        """Test that to_dict returns all task fields in a dictionary"""
        # Arrange
        task = Task("test_task", {"param": "value"})
        task.start()
        task.update_progress(75)

        # Act
        task_dict = task.to_dict()

        # Assert
        self.assertEqual(task_dict["id"], task.id)
        self.assertEqual(task_dict["type"], "test_task")
        self.assertEqual(task_dict["status"], TaskStatus.RUNNING.value)
        self.assertEqual(task_dict["params"], {"param": "value"})
        self.assertEqual(task_dict["progress"], 75)
        self.assertIsNone(task_dict["error"])
        self.assertIsNotNone(task_dict["created_at"])
        self.assertIsNotNone(task_dict["started_at"])
        self.assertIsNone(task_dict["completed_at"])


class TaskManagerFunctionsTests(TestCase):
    """Tests for the task manager utility functions"""

    def setUp(self):
        """Reset the tasks registry before each test"""
        tasks.clear()

    def test_create_task_adds_to_registry(self):
        """Test that create_task adds the task to the registry"""
        # Act
        task = create_task("test_task", {"year": 2023})

        # Assert
        self.assertIn(task.id, tasks)
        self.assertEqual(tasks[task.id], task)
        self.assertEqual(task.task_type, "test_task")
        self.assertEqual(task.params, {"year": 2023})

    def test_get_task_returns_correct_task(self):
        """Test that get_task returns the correct task by ID"""
        # Arrange
        task = create_task("test_task")

        # Act
        retrieved_task = get_task(task.id)

        # Assert
        self.assertEqual(retrieved_task, task)

    def test_get_task_raises_error_for_nonexistent_task(self):
        """Test that get_task raises an error for a nonexistent task ID"""
        # Act & Assert
        with self.assertRaises(TaskNotFoundError):
            get_task("nonexistent-id")

    def test_get_recent_tasks_returns_sorted_tasks(self):
        """Test that get_recent_tasks returns tasks sorted by creation time"""
        # Arrange
        task1 = create_task("task1")
        task2 = create_task("task2")
        task3 = create_task("task3")

        # Act
        recent_tasks = get_recent_tasks()

        # Assert - Task order should be 3, 2, 1 (most recent first)
        self.assertEqual(len(recent_tasks), 3)
        self.assertEqual(recent_tasks[0]["id"], task3.id)
        self.assertEqual(recent_tasks[1]["id"], task2.id)
        self.assertEqual(recent_tasks[2]["id"], task1.id)

    def test_get_recent_tasks_respects_limit(self):
        """Test that get_recent_tasks respects the limit parameter"""
        # Arrange
        for i in range(5):
            create_task(f"task{i}")

        # Act
        recent_tasks = get_recent_tasks(limit=3)

        # Assert
        self.assertEqual(len(recent_tasks), 3)

    def test_cleanup_old_tasks_removes_completed_tasks(self):
        """Test that cleanup_old_tasks removes old completed tasks"""
        # Arrange
        task1 = create_task("old_task")
        task1.start()
        task1.complete(True)

        task2 = create_task("recent_task")
        task2.start()
        task2.complete(True)

        task3 = create_task("pending_task")

        # Mock the completed_at timestamp for task1 to be over 1 hour old
        one_hour_ago = (datetime.now() - timedelta(hours=2)).isoformat()
        tasks[task1.id].completed_at = one_hour_ago

        # Act
        cleanup_old_tasks()

        # Assert
        self.assertNotIn(task1.id, tasks)  # Old task should be removed
        self.assertIn(task2.id, tasks)  # Recent task should remain
        self.assertIn(task3.id, tasks)  # Pending task should remain

    @patch("threading.Thread")
    def test_run_task_in_thread_starts_thread(self, mock_thread):
        """Test that run_task_in_thread starts a thread with the function"""
        # Arrange
        task = create_task("test_task")
        mock_func = MagicMock()
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Act
        result = run_task_in_thread(mock_func, task, "arg1", kwarg1="value1")

        # Assert
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        self.assertEqual(result, mock_thread_instance)

    def test_run_task_in_thread_executes_function(self):
        """Test that run_task_in_thread actually executes the function"""
        # Arrange
        task = create_task("test_task")
        result_container = {"was_called": False}

        def test_function(arg1, kwarg1=None):
            result_container["was_called"] = True
            result_container["arg1"] = arg1
            result_container["kwarg1"] = kwarg1
            # Complete the task to avoid waiting for thread
            task.complete(True)

        # Act
        thread = run_task_in_thread(test_function, task, "arg1", kwarg1="value1")
        # Wait for thread to complete
        thread.join(timeout=1.0)

        # Assert
        self.assertTrue(result_container["was_called"])
        self.assertEqual(result_container["arg1"], "arg1")
        self.assertEqual(result_container["kwarg1"], "value1")
        self.assertEqual(task.status, TaskStatus.SUCCESS)


class TaskExceptionsTests(TestCase):
    """Tests for the task manager exception classes"""

    def test_task_error_has_correct_message(self):
        """Test that TaskError has the correct error message"""
        # Arrange & Act
        error = TaskError("Custom error message")

        # Assert
        self.assertEqual(str(error), "Custom error message")
        self.assertEqual(error.message, "Custom error message")

    def test_task_not_found_error_has_correct_message(self):
        """Test that TaskNotFoundError has the correct error message"""
        # Arrange & Act
        error = TaskNotFoundError("Task ID abc123 not found")

        # Assert
        self.assertEqual(str(error), "Task ID abc123 not found")
