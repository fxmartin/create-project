# ABOUTME: Comprehensive test suite for error dialog functionality
# ABOUTME: Tests dialog creation, display, actions, and AI integration

"""Test suite for the error dialog."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QTextBrowser

from create_project.config.config_manager import ConfigManager
from create_project.core.exceptions import ProjectGenerationError
from create_project.gui.dialogs.error import ErrorDialog


class TestErrorDialog:
    """Test cases for ErrorDialog."""

    def test_dialog_creation(self, qtbot):
        """Test basic dialog creation."""
        error = ValueError("Test error message")
        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Error"
        assert dialog.isModal()
        assert dialog.error_type == "ValueError"
        assert dialog.error_message == "Test error message"

    def test_dialog_with_context(self, qtbot):
        """Test dialog creation with context."""
        error = RuntimeError("Operation failed")
        context = {
            "operation": "Creating project",
            "template": "python-library",
            "path": "/test/path",
        }

        dialog = ErrorDialog(error, context=context)
        qtbot.addWidget(dialog)

        assert dialog.context == context
        # Context section should be created
        from create_project.gui.widgets.collapsible_section import CollapsibleSection

        sections = dialog.findChildren(CollapsibleSection)
        # Debug: print what sections we find
        section_texts = [s._header.text() for s in sections]
        assert len(sections) > 0, (
            f"No CollapsibleSection widgets found. Widget count: {len(list(dialog.children()))}"
        )
        assert any("Error Context" in text for text in section_texts), (
            f"Found sections: {section_texts}"
        )

    def test_error_icon_selection(self, qtbot):
        """Test appropriate icon selection based on error type."""
        # Test warning icon
        warning = Warning("Test warning")
        dialog = ErrorDialog(warning)
        qtbot.addWidget(dialog)
        assert dialog.icon_label.pixmap() is not None

        # Test permission error icon
        perm_error = PermissionError("Access denied")
        dialog2 = ErrorDialog(perm_error)
        qtbot.addWidget(dialog2)
        assert dialog2.icon_label.pixmap() is not None

        # Test generic error icon
        generic_error = Exception("Generic error")
        dialog3 = ErrorDialog(generic_error)
        qtbot.addWidget(dialog3)
        assert dialog3.icon_label.pixmap() is not None

    def test_stack_trace_display(self, qtbot):
        """Test stack trace is properly displayed."""
        try:
            raise ValueError("Test error with traceback")
        except ValueError as e:
            dialog = ErrorDialog(e)
            qtbot.addWidget(dialog)

            # Check stack trace is captured
            assert "ValueError: Test error with traceback" in dialog.stack_trace
            assert "test_stack_trace_display" in dialog.stack_trace

            # Check it's displayed in the browser
            stack_browser = dialog.stack_browser
            assert isinstance(stack_browser, QTextBrowser)
            assert dialog.stack_trace in stack_browser.toPlainText()

    def test_timestamp_display(self, qtbot):
        """Test timestamp is shown correctly."""
        error = ValueError("Test error")
        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        # Check timestamp is recent
        assert isinstance(dialog.timestamp, datetime)
        time_diff = datetime.now() - dialog.timestamp
        assert time_diff.total_seconds() < 1  # Within 1 second

        # Check it's displayed
        assert "Occurred at:" in dialog.time_label.text()

    def test_copy_error_details(self, qtbot):
        """Test copying error details to clipboard."""
        error = ValueError("Test error")
        context = {"operation": "test operation"}

        dialog = ErrorDialog(error, context=context)
        qtbot.addWidget(dialog)

        # Mock clipboard
        with patch.object(QApplication, "clipboard") as mock_clipboard:
            mock_clip_instance = MagicMock()
            mock_clipboard.return_value = mock_clip_instance

            # Click copy button
            dialog.copy_btn.click()

            # Check clipboard was called
            mock_clip_instance.setText.assert_called_once()
            copied_text = mock_clip_instance.setText.call_args[0][0]

            # Verify content
            assert "ValueError" in copied_text
            assert "Test error" in copied_text
            assert "operation: test operation" in copied_text
            assert "Stack Trace:" in copied_text

    def test_copy_button_feedback(self, qtbot):
        """Test copy button shows feedback."""
        error = ValueError("Test error")
        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        # Mock clipboard
        with patch.object(QApplication, "clipboard"):
            # Initial text
            assert dialog.copy_btn.text() == "Copy Error"

            # Click copy
            dialog.copy_btn.click()

            # Should show feedback
            assert dialog.copy_btn.text() == "Copied!"

            # Wait for reset - need longer wait in test environment
            qtbot.wait(2500)
            assert dialog.copy_btn.text() == "Copy Error"

    def test_ai_help_availability(self, qtbot):
        """Test AI help button visibility based on config."""
        error = ValueError("Test error")

        # Test with AI enabled
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_setting.return_value = True

        dialog = ErrorDialog(error, config_manager=config_manager)
        qtbot.addWidget(dialog)

        # Should have help button
        assert hasattr(dialog, "help_btn")
        assert dialog.help_btn.text() == "Get AI Help"

        # Test with AI disabled
        config_manager.get_setting.return_value = False

        dialog2 = ErrorDialog(error, config_manager=config_manager)
        qtbot.addWidget(dialog2)

        # Should not have help button
        assert not hasattr(dialog2, "help_btn")

    def test_ai_help_request(self, qtbot):
        """Test AI help request functionality."""
        error = ValueError("Test error")
        context = {"operation": "test"}

        config_manager = Mock(spec=ConfigManager)
        config_manager.get_setting.return_value = True

        dialog = ErrorDialog(error, context, config_manager)
        qtbot.addWidget(dialog)

        # Connect signal spy
        with qtbot.waitSignal(dialog.help_requested) as blocker:
            dialog.help_btn.click()

        # Check signal was emitted with correct args
        assert blocker.args[0] is error
        assert blocker.args[1] == context

        # Check button state changed
        assert not dialog.help_btn.isEnabled()
        assert dialog.help_btn.text() == "Getting help..."

    def test_retry_button_for_retryable_errors(self, qtbot):
        """Test retry button appears for retryable errors."""
        # Test with retryable error
        io_error = OSError("Disk full")
        dialog = ErrorDialog(io_error)
        qtbot.addWidget(dialog)

        # Should have retry button
        assert hasattr(dialog, "retry_btn")
        assert dialog.retry_btn.text() == "Retry"

        # Test with non-retryable error
        value_error = ValueError("Invalid value")
        dialog2 = ErrorDialog(value_error)
        qtbot.addWidget(dialog2)

        # Should not have retry button
        assert not hasattr(dialog2, "retry_btn")

    def test_retry_signal(self, qtbot):
        """Test retry signal emission."""
        error = ConnectionError("Network error")
        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        # Connect signal spy
        with qtbot.waitSignal(dialog.retry_requested) as blocker:
            dialog.retry_btn.click()

        # Dialog should accept (close with success)
        assert dialog.result() == dialog.DialogCode.Accepted

    def test_report_issue_button(self, qtbot):
        """Test report issue functionality."""
        error = ValueError("Test error")
        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        # Mock QDesktopServices
        with patch("PyQt6.QtGui.QDesktopServices.openUrl") as mock_open:
            dialog.report_btn.click()

            # Check URL was opened
            mock_open.assert_called_once()
            url = mock_open.call_args[0][0]

            # Check URL contains error info
            url_str = url.toString()
            assert "issues/new" in url_str
            assert "ValueError" in url_str

    def test_project_generation_error_context(self, qtbot):
        """Test special handling for ProjectGenerationError."""
        # Create error with additional attributes
        error = ProjectGenerationError("Generation failed")
        error.template_name = "python-library"
        error.operation = "Creating directories"

        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        # Check context was enriched
        assert dialog.context.get("Template") == "python-library"
        assert dialog.context.get("Operation") == "Creating directories"

    def test_collapsible_sections(self, qtbot):
        """Test collapsible sections functionality."""
        error = ValueError("Test error")
        context = {"test": "context"}

        dialog = ErrorDialog(error, context)
        qtbot.addWidget(dialog)

        # Context section should be expanded by default
        from create_project.gui.widgets.collapsible_section import CollapsibleSection

        context_sections = [
            w
            for w in dialog.findChildren(CollapsibleSection)
            if "Error Context" in w._header.text()
        ]
        assert len(context_sections) == 1
        assert not context_sections[0].is_collapsed()

        # Details section should be collapsed by default
        assert "Technical Details" in dialog.details_section._header.text()
        assert dialog.details_section.is_collapsed()

    def test_show_ai_response(self, qtbot):
        """Test displaying AI response."""
        error = ValueError("Test error")
        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        # Show AI response
        ai_response = "<p>This error occurred because...</p>"
        dialog.show_ai_response(ai_response)

        # Check AI section was added
        from create_project.gui.widgets.collapsible_section import CollapsibleSection

        ai_sections = [
            w
            for w in dialog.findChildren(CollapsibleSection)
            if "AI Assistance" in w._header.text()
        ]
        assert len(ai_sections) == 1
        assert not ai_sections[0].is_collapsed()

    def test_dialog_buttons(self, qtbot):
        """Test dialog button box."""
        error = ValueError("Test error")
        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        # Should have close button
        close_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Close)
        assert close_button is not None

        # Clicking close should reject dialog
        with qtbot.waitSignal(dialog.rejected):
            close_button.click()

    def test_error_without_traceback(self, qtbot):
        """Test handling errors without traceback."""
        # Create error without raising it
        error = ValueError("Test error")
        dialog = ErrorDialog(error)
        qtbot.addWidget(dialog)

        # Should still have stack trace (current stack)
        assert dialog.stack_trace
        assert "test_error_without_traceback" in dialog.stack_trace
