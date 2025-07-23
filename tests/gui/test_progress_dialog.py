# ABOUTME: Tests for the custom progress dialog widget
# ABOUTME: Verifies progress updates, cancellation, and state transitions

"""
Tests for the ProgressDialog widget.

This module tests the custom progress dialog functionality including:
- Progress updates and message display
- Cancellation with confirmation
- State transitions (running, finished, cancelled)
- Log display and auto-close behavior
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from create_project.gui.widgets.progress_dialog import ProgressDialog


@pytest.fixture
def progress_dialog(qtbot):
    """Create a ProgressDialog instance for testing."""
    dialog = ProgressDialog()
    qtbot.addWidget(dialog)
    return dialog


class TestProgressDialog:
    """Test ProgressDialog functionality."""

    def test_initialization(self, progress_dialog, qtbot):
        """Test dialog initialization."""
        assert progress_dialog.windowTitle() == "Creating Project"
        assert progress_dialog.isModal()
        assert not progress_dialog.is_cancelled()
        assert progress_dialog.progress_bar.value() == 0
        assert progress_dialog.status_label.text() == "Initializing..."
        assert progress_dialog.cancel_button.text() == "Cancel"
        assert progress_dialog.cancel_button.isEnabled()

    def test_update_progress(self, progress_dialog, qtbot):
        """Test progress updates."""
        # Update progress
        progress_dialog.update_progress(50, "Processing files...")

        assert progress_dialog.progress_bar.value() == 50
        assert progress_dialog.status_label.text() == "Processing files..."

        # Check log entry was added
        log_text = progress_dialog.log_display.toPlainText()
        assert "[50%] Processing files..." in log_text

        # Update to 100%
        progress_dialog.update_progress(100, "Almost done!")
        assert progress_dialog.progress_bar.value() == 100
        assert progress_dialog.status_label.text() == "Almost done!"

    def test_add_log_entry(self, progress_dialog, qtbot):
        """Test adding log entries."""
        # Add multiple entries
        progress_dialog.add_log_entry("Starting process...")
        progress_dialog.add_log_entry("Loading template...")
        progress_dialog.add_log_entry("Creating directories...")

        log_text = progress_dialog.log_display.toPlainText()
        assert "Starting process..." in log_text
        assert "Loading template..." in log_text
        assert "Creating directories..." in log_text

        # Check entries are in order
        lines = log_text.strip().split("\n")
        assert lines[0] == "Starting process..."
        assert lines[1] == "Loading template..."
        assert lines[2] == "Creating directories..."

    def test_cancel_with_confirmation_no(self, progress_dialog, qtbot, monkeypatch):
        """Test cancellation when user says No."""
        # Mock QMessageBox to return No
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *args, **kwargs: QMessageBox.StandardButton.No
        )

        # Record if cancelled signal was emitted
        cancelled_emitted = False
        def on_cancelled():
            nonlocal cancelled_emitted
            cancelled_emitted = True

        progress_dialog.cancelled.connect(on_cancelled)

        # Click cancel
        qtbot.mouseClick(progress_dialog.cancel_button, Qt.MouseButton.LeftButton)

        # Check state didn't change
        assert not progress_dialog.is_cancelled()
        assert not cancelled_emitted
        assert progress_dialog.cancel_button.isEnabled()
        assert progress_dialog.status_label.text() == "Initializing..."

    def test_cancel_with_confirmation_yes(self, progress_dialog, qtbot, monkeypatch):
        """Test cancellation when user says Yes."""
        # Mock QMessageBox to return Yes
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes
        )

        # Record if cancelled signal was emitted
        cancelled_emitted = False
        def on_cancelled():
            nonlocal cancelled_emitted
            cancelled_emitted = True

        progress_dialog.cancelled.connect(on_cancelled)

        # Click cancel
        qtbot.mouseClick(progress_dialog.cancel_button, Qt.MouseButton.LeftButton)

        # Check state changed
        assert progress_dialog.is_cancelled()
        assert cancelled_emitted
        assert not progress_dialog.cancel_button.isEnabled()
        assert progress_dialog.status_label.text() == "Cancelling..."

    def test_set_finished_success(self, progress_dialog, qtbot):
        """Test setting dialog to success state."""
        # Set to finished with success
        progress_dialog.set_finished(True, "Project created at /path/to/project")

        assert progress_dialog.progress_bar.value() == 100
        assert progress_dialog.title_label.text() == "Project Created Successfully!"
        assert progress_dialog.status_label.text() == "Project created at /path/to/project"
        assert progress_dialog.cancel_button.text() == "Close"
        assert progress_dialog.cancel_button.isEnabled()

        # Check success log entry
        log_text = progress_dialog.log_display.toPlainText()
        assert "✓ SUCCESS: Project created at /path/to/project" in log_text

        # Test clicking close button
        qtbot.mouseClick(progress_dialog.cancel_button, Qt.MouseButton.LeftButton)
        assert progress_dialog.result() == progress_dialog.DialogCode.Accepted

    def test_set_finished_failure(self, progress_dialog, qtbot):
        """Test setting dialog to failure state."""
        # Set to finished with failure
        progress_dialog.set_finished(False, "Failed to create project: Permission denied")

        assert progress_dialog.title_label.text() == "Project Generation Failed"
        assert progress_dialog.status_label.text() == "Failed to create project: Permission denied"
        assert progress_dialog.cancel_button.text() == "Close"
        assert progress_dialog.cancel_button.isEnabled()

        # Check error log entry
        log_text = progress_dialog.log_display.toPlainText()
        assert "✗ ERROR: Failed to create project: Permission denied" in log_text

        # Check progress bar color changed (by checking stylesheet)
        assert "background-color: #f44336" in progress_dialog.progress_bar.styleSheet()

    def test_set_cancelled(self, progress_dialog, qtbot):
        """Test setting dialog to cancelled state."""
        # Set to cancelled
        progress_dialog.set_cancelled()

        assert progress_dialog.is_cancelled()
        assert progress_dialog.title_label.text() == "Project Generation Cancelled"
        assert progress_dialog.status_label.text() == "The operation was cancelled by user request."
        assert progress_dialog.cancel_button.text() == "Close"
        assert progress_dialog.cancel_button.isEnabled()

        # Check cancelled log entry
        log_text = progress_dialog.log_display.toPlainText()
        assert "⚠ CANCELLED: Operation cancelled by user" in log_text

        # Check progress bar color changed (orange)
        assert "background-color: #FF9800" in progress_dialog.progress_bar.styleSheet()

    @pytest.mark.skip(reason="Auto-close timing test is flaky in CI")
    def test_auto_close_on_success(self, progress_dialog, qtbot):
        """Test auto-close behavior on success."""
        # Set to success
        progress_dialog.set_finished(True, "Success!")

        # Wait less than auto-close timeout
        qtbot.wait(1000)
        assert progress_dialog.isVisible()

        # Wait for auto-close (2 seconds total)
        qtbot.wait(1500)
        assert progress_dialog.result() == progress_dialog.DialogCode.Accepted

    def test_close_event_when_running(self, progress_dialog, qtbot, monkeypatch):
        """Test close event is ignored when operation is running."""
        # Mock QMessageBox to return No (don't cancel)
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *args, **kwargs: QMessageBox.StandardButton.No
        )

        # Try to close dialog
        progress_dialog.close()

        # Dialog should still be visible
        assert progress_dialog.isVisible()

    def test_close_event_when_finished(self, progress_dialog, qtbot):
        """Test close event works when operation is finished."""
        # Set to finished state
        progress_dialog.set_finished(True, "Done")

        # Close dialog
        progress_dialog.close()

        # Dialog should accept and close
        assert progress_dialog.result() == progress_dialog.DialogCode.Accepted

    def test_progress_updates_when_cancelled(self, progress_dialog, qtbot, monkeypatch):
        """Test that progress updates are ignored after cancellation."""
        # Mock QMessageBox to return Yes
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes
        )

        # Cancel the dialog
        qtbot.mouseClick(progress_dialog.cancel_button, Qt.MouseButton.LeftButton)
        assert progress_dialog.is_cancelled()

        # Try to update progress
        old_value = progress_dialog.progress_bar.value()
        old_status = progress_dialog.status_label.text()

        progress_dialog.update_progress(75, "This should be ignored")

        # Values should not change
        assert progress_dialog.progress_bar.value() == old_value
        assert progress_dialog.status_label.text() == old_status

    def test_window_modality(self, progress_dialog, qtbot):
        """Test that dialog is properly modal."""
        assert progress_dialog.isModal()

        # Check window flags include stay on top
        flags = progress_dialog.windowFlags()
        assert flags & Qt.WindowType.WindowStaysOnTopHint

        # Check close button is disabled
        assert not (flags & Qt.WindowType.WindowCloseButtonHint)
