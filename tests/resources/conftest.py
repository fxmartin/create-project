# ABOUTME: pytest configuration for resource tests
# ABOUTME: Provides Qt application setup for icon and style tests

"""
pytest configuration for resource tests.

This module provides Qt application fixtures needed for QPixmap/QIcon operations.
"""

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """
    Create a QApplication instance for the test session.
    
    This fixture ensures that only one QApplication instance exists
    during the entire test session, which is required for Qt graphics operations.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app here, let pytest-qt handle it


@pytest.fixture(autouse=True)
def qt_app(qapp):
    """
    Ensure QApplication is available for all resource tests.
    
    This fixture is automatically used for all tests in this directory,
    preventing crashes when creating QPixmap/QIcon objects.
    """
    yield qapp