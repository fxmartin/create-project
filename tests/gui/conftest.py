# ABOUTME: pytest configuration and fixtures for GUI testing
# ABOUTME: Provides Qt application setup and common test utilities

"""
pytest configuration for GUI tests.

This module provides:
- Qt application fixtures
- Common mock objects for GUI testing
- Helper functions for UI interaction
- Test data generators
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """
    Create a QApplication instance for the test session.

    This fixture ensures that only one QApplication instance exists
    during the entire test session, which is a Qt requirement.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app here, let pytest-qt handle it


@pytest.fixture
def mock_config_manager():
    """
    Create a mock ConfigManager for testing.

    Returns a ConfigManager mock with sensible defaults for GUI testing.
    """
    config = MagicMock()

    # Set up default configuration values
    config.get.side_effect = lambda key, default=None: {
        "default_author": "Test Author",
        "default_location": str(Path.home() / "projects"),
        "ai.enabled": True,
        "ai.ollama_url": "http://localhost:11434",
        "ai.model": "llama2",
        "templates.builtin_path": "templates/builtin",
        "templates.user_path": str(Path.home() / ".create-project" / "templates"),
    }.get(key, default)

    config.set = MagicMock()
    config.save = MagicMock()

    return config


@pytest.fixture
def mock_template_engine():
    """
    Create a mock TemplateEngine for testing.

    Returns a TemplateEngine mock with test templates.
    """
    engine = MagicMock()

    # Mock template data
    test_templates = [
        {
            "id": "python_library",
            "name": "Python Library",
            "description": "A reusable Python library with testing and documentation",
            "variables": ["project_name", "author", "version", "description"],
            "options": {
                "license": ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"],
                "init_git": True,
                "create_venv": True,
            },
        },
        {
            "id": "cli_single_package",
            "name": "CLI Application",
            "description": "Command-line application with argument parsing",
            "variables": ["project_name", "author", "version", "description"],
            "options": {
                "license": ["MIT", "Apache-2.0"],
                "init_git": True,
                "create_venv": True,
            },
        },
        {
            "id": "flask_web_app",
            "name": "Flask Web Application",
            "description": "Web application using Flask framework",
            "variables": ["project_name", "author", "version", "description"],
            "options": {
                "license": ["MIT"],
                "init_git": True,
                "create_venv": True,
                "include_docker": True,
            },
        },
    ]

    engine.list_templates.return_value = test_templates
    engine.get_template.side_effect = lambda template_id: next(
        (t for t in test_templates if t["id"] == template_id), None
    )
    engine.validate_template.return_value = {"valid": True, "errors": []}

    return engine


@pytest.fixture
def mock_ai_service():
    """
    Create a mock AI service for testing.

    Returns an AI service mock that simulates AI assistance.
    """
    ai_service = MagicMock()
    ai_service.is_available.return_value = True
    ai_service.get_error_help.return_value = "AI suggestion: Check your Python version and ensure all dependencies are installed."
    ai_service.get_suggestions.return_value = [
        "Try running with administrator privileges",
        "Check file permissions",
    ]

    return ai_service


@pytest.fixture
def wizard_test_data():
    """
    Provide test data for wizard testing.

    Returns a dictionary with valid test data for all wizard fields.
    """
    return {
        "project_name": "test_project",
        "author": "Test Author",
        "version": "0.1.0",
        "description": "A test project for GUI testing",
        "location": str(Path.home() / "test_projects"),
        "template": "python_library",
        "license": "MIT",
        "init_git": True,
        "create_venv": True,
    }


class QtBot:
    """
    Helper class extending qtbot functionality for common GUI test operations.
    """

    def __init__(self, qtbot):
        self.qtbot = qtbot

    def click_button(self, button):
        """Click a button and wait for events to process."""
        self.qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
        self.qtbot.wait(50)  # Short wait for UI updates

    def set_text(self, widget, text):
        """Set text in a widget and trigger validation."""
        widget.clear()
        self.qtbot.keyClicks(widget, text)
        self.qtbot.wait(50)

    def select_item(self, list_widget, index):
        """Select an item in a list widget."""
        item = list_widget.item(index)
        if item:
            list_widget.setCurrentItem(item)
            self.qtbot.wait(50)


@pytest.fixture
def qt_bot_helper(qtbot):
    """
    Create an enhanced qtbot helper with common operations.
    """
    return QtBot(qtbot)


# Skip GUI tests if running in headless environment
def pytest_collection_modifyitems(config, items):
    """
    Mark GUI tests to skip if no display is available.
    """
    import os

    if not os.environ.get("DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
        skip_gui = pytest.mark.skip(reason="No display available for GUI tests")
        for item in items:
            if "gui" in str(item.fspath):
                item.add_marker(skip_gui)
