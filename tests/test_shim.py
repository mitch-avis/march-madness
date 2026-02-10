"""Shim tests to keep pytest tools expecting tests/ happy."""

from importlib import import_module


def test_shim_imports_project_tests() -> None:
    """Ensure test modules are importable from their current locations."""
    module_names = [
        "core.tests",
        "scraper.test_score_utils",
        "scraper.test_task_manager",
        "scraper.test_utils",
        "scraper.test_views",
    ]
    for module_name in module_names:
        assert import_module(module_name)
