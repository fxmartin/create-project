# ABOUTME: Test suite for AI help dialog functionality
# ABOUTME: Tests streaming responses, error handling, and user interactions

"""Test suite for AI help dialog."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog

from create_project.gui.dialogs.ai_help import AIHelpDialog, AIQueryWorker


class MockAIService:
    """Mock AI service for testing."""

    def __init__(self, response: str = "Test AI response", *, should_error: bool = False):
        self.response = response
        self.should_error = should_error
        self.generate_help_response_called = False
        self.stream_help_response_called = False

    def generate_help_response(self, **kwargs: Any) -> str:
        """Mock generate help response."""
        self.generate_help_response_called = True
        if self.should_error:
            raise Exception("AI service error")
        return self.response

    def stream_help_response(self, **kwargs: Any) -> Generator[str, None, None]:
        """Mock stream help response."""
        self.stream_help_response_called = True
        if self.should_error:
            raise Exception("AI service error")

        # Simulate streaming by yielding chunks
        words = self.response.split()
        for word in words:
            yield word + " "


@pytest.fixture
def mock_ai_service() -> MockAIService:
    """Create mock AI service."""
    return MockAIService()


@pytest.fixture
def test_error() -> Exception:
    """Create test exception."""
    return ValueError("Test error message")


@pytest.fixture
def test_context() -> dict[str, Any]:
    """Create test context."""
    return {
        "template": "python_package",
        "project_vars": {"name": "test_project", "author": "Test Author"},
        "target_path": "/test/path",
        "options": {"git": True, "venv": "uv"},
    }


class TestAIQueryWorker:
    """Test AI query worker thread."""

    def test_worker_init(
        self, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test worker initialization."""
        worker = AIQueryWorker(mock_ai_service, test_error, {})
        assert worker.ai_service == mock_ai_service
        assert worker.error == test_error
        assert worker.context == {}
        assert not worker._should_stop

    def test_worker_stop(
        self, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test worker stop request."""
        worker = AIQueryWorker(mock_ai_service, test_error, {})
        worker.stop()
        assert worker._should_stop

    @pytest.mark.skip(reason="Requires Qt event loop")
    def test_worker_streaming_response(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test worker with streaming response."""
        mock_ai_service.response = "This is a test response"
        worker = AIQueryWorker(mock_ai_service, test_error, {})

        chunks = []
        complete_response = []

        with qtbot.waitSignals([worker.response_chunk, worker.response_complete], timeout=1000):
            worker.response_chunk.connect(chunks.append)
            worker.response_complete.connect(complete_response.append)
            worker.start()

        assert len(chunks) > 0
        assert len(complete_response) == 1
        assert complete_response[0] == "This is a test response "

    @pytest.mark.skip(reason="Requires Qt event loop")
    def test_worker_non_streaming_response(
        self, qtbot: Any, test_error: Exception
    ) -> None:
        """Test worker with non-streaming response."""
        # Create AI service without stream_help_response method
        ai_service = MagicMock()
        ai_service.generate_help_response.return_value = "Non-streaming response"
        delattr(ai_service, "stream_help_response")

        worker = AIQueryWorker(ai_service, test_error, {})

        complete_response = []

        with qtbot.waitSignal(worker.response_complete, timeout=1000):
            worker.response_complete.connect(complete_response.append)
            worker.start()

        assert len(complete_response) == 1
        assert complete_response[0] == "Non-streaming response"

    @pytest.mark.skip(reason="Requires Qt event loop")
    def test_worker_error_handling(
        self, qtbot: Any, test_error: Exception
    ) -> None:
        """Test worker error handling."""
        ai_service = MockAIService(should_error=True)
        worker = AIQueryWorker(ai_service, test_error, {})

        errors = []

        with qtbot.waitSignal(worker.error_occurred, timeout=1000):
            worker.error_occurred.connect(errors.append)
            worker.start()

        assert len(errors) == 1
        assert "AI service error" in errors[0]


class TestAIHelpDialog:
    """Test AI help dialog."""

    def test_dialog_init(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test dialog initialization."""
        dialog = AIHelpDialog(mock_ai_service, test_error)
        qtbot.addWidget(dialog)

        assert dialog.ai_service == mock_ai_service
        assert dialog.error == test_error
        assert dialog.context == {}
        assert dialog.windowTitle() == "AI Assistant"
        assert dialog.isModal()

    def test_dialog_ui_elements(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test dialog UI elements."""
        dialog = AIHelpDialog(mock_ai_service, test_error)
        qtbot.addWidget(dialog)

        # Check UI elements exist
        assert dialog.status_label is not None
        assert dialog.progress_bar is not None
        assert dialog.response_browser is not None
        assert dialog.copy_button is not None
        assert dialog.retry_button is not None
        assert dialog.button_box is not None

        # Check initial states
        assert dialog.status_label.text() == "Consulting AI assistant..."
        assert dialog.progress_bar.isVisible()
        assert not dialog.copy_button.isEnabled()
        assert not dialog.retry_button.isEnabled()

    @pytest.mark.skip(reason="Requires Qt event loop")
    def test_successful_response(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test successful AI response handling."""
        mock_ai_service.response = "## Solution\n\nHere's how to fix the error:\n\n```python\nprint('Fixed!')\n```"

        dialog = AIHelpDialog(mock_ai_service, test_error)
        qtbot.addWidget(dialog)
        dialog.show()

        # Wait for response
        qtbot.wait(500)  # Give time for worker to complete

        # Check UI updates
        assert not dialog.progress_bar.isVisible()
        assert dialog.status_label.text() == "AI suggestion received:"
        assert dialog.copy_button.isEnabled()
        assert dialog.retry_button.isEnabled()

        # Check response content
        response_text = dialog.response_browser.toPlainText()
        assert "Solution" in response_text
        assert "Fixed!" in response_text

    @pytest.mark.skip(reason="Requires Qt event loop")
    def test_error_response(
        self, qtbot: Any, test_error: Exception
    ) -> None:
        """Test error response handling."""
        ai_service = MockAIService(should_error=True)

        dialog = AIHelpDialog(ai_service, test_error)
        qtbot.addWidget(dialog)
        dialog.show()

        # Wait for error
        qtbot.wait(500)

        # Check UI updates
        assert not dialog.progress_bar.isVisible()
        assert dialog.status_label.text() == "Failed to get AI suggestion"
        assert not dialog.copy_button.isEnabled()
        assert dialog.retry_button.isEnabled()

        # Check error display
        html = dialog.response_browser.toHtml()
        assert "Unable to get AI suggestion" in html
        assert "AI service error" in html

    def test_copy_to_clipboard(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test copy to clipboard functionality."""
        dialog = AIHelpDialog(mock_ai_service, test_error)
        qtbot.addWidget(dialog)

        # Set some response text
        dialog.response_browser.setText("Test response to copy")
        dialog.copy_button.setEnabled(True)

        # Click copy button
        with patch.object(QApplication, "clipboard") as mock_clipboard:
            clipboard_mock = MagicMock()
            mock_clipboard.return_value = clipboard_mock

            dialog._copy_response()

            clipboard_mock.setText.assert_called_once_with("Test response to copy")
            assert dialog.status_label.text() == "Response copied to clipboard!"

    @pytest.mark.skip(reason="Requires Qt event loop")
    def test_retry_functionality(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test retry functionality."""
        dialog = AIHelpDialog(mock_ai_service, test_error)
        qtbot.addWidget(dialog)
        dialog.show()

        # Wait for initial response
        qtbot.wait(500)

        # Enable retry button and clear response
        dialog.retry_button.setEnabled(True)
        dialog.response_browser.clear()

        # Click retry
        qtbot.mouseClick(dialog.retry_button, Qt.MouseButton.LeftButton)

        # Wait for new response
        qtbot.wait(500)

        # Check that new query was started
        assert dialog.progress_bar.isVisible()
        assert dialog.status_label.text() == "Consulting AI assistant..."

    def test_markdown_conversion(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test markdown to HTML conversion."""
        dialog = AIHelpDialog(mock_ai_service, test_error)
        qtbot.addWidget(dialog)

        # Test various markdown elements
        markdown = """# Header 1
## Header 2
### Header 3

This is **bold** and this is *italic*.

Here's some `inline code`.

```python
def test():
    print("Code block")
```
"""

        dialog._set_response_html(markdown)
        html = dialog.response_browser.toHtml()

        # Check conversions
        assert "<h1>Header 1</h1>" in html
        assert "<h2>Header 2</h2>" in html
        assert "<h3>Header 3</h3>" in html
        assert "<b>bold</b>" in html
        assert "<i>italic</i>" in html
        assert "<code style=" in html
        assert "<pre style=" in html
        assert "def test():" in html

    def test_close_event_stops_worker(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test that closing dialog stops worker thread."""
        dialog = AIHelpDialog(mock_ai_service, test_error)
        qtbot.addWidget(dialog)

        # Create mock worker
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        dialog.worker = mock_worker

        # Close dialog
        dialog.close()

        # Check worker was stopped
        mock_worker.stop.assert_called_once()
        mock_worker.wait.assert_called_once()

    def test_dialog_with_context(
        self,
        qtbot: Any,
        mock_ai_service: MockAIService,
        test_error: Exception,
        test_context: dict[str, Any],
    ) -> None:
        """Test dialog with context information."""
        dialog = AIHelpDialog(mock_ai_service, test_error, test_context)
        qtbot.addWidget(dialog)

        assert dialog.context == test_context
        assert dialog.worker is not None

    def test_dialog_result(
        self, qtbot: Any, mock_ai_service: MockAIService, test_error: Exception
    ) -> None:
        """Test dialog result on close."""
        dialog = AIHelpDialog(mock_ai_service, test_error)
        qtbot.addWidget(dialog)

        # Click close button
        close_button = dialog.button_box.button(
            dialog.button_box.StandardButton.Close
        )
        assert close_button is not None

        qtbot.mouseClick(close_button, Qt.MouseButton.LeftButton)

        assert dialog.result() == QDialog.DialogCode.Rejected

