# ABOUTME: Error dialog with progressive disclosure and AI help integration
# ABOUTME: Provides clear error display with expandable details and assistance options

"""
Error dialog for the Create Project application.

This module provides an error dialog with progressive disclosure that displays
error information clearly and offers AI-powered assistance when available.
The dialog supports expandable details, clipboard operations, and error reporting.

The dialog is designed to:
- Display errors clearly with appropriate severity indicators
- Provide progressive disclosure for technical details
- Integrate with AI service for intelligent assistance
- Support various user actions (copy, save, report)
"""

import sys
import traceback
from datetime import datetime
from typing import Any, Optional

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from structlog import get_logger

from ...config.config_manager import ConfigManager
from ...core.exceptions import ProjectGenerationError
from ..widgets.collapsible_section import CollapsibleSection

logger = get_logger(__name__)


class ErrorDialog(QDialog):
    """Error dialog with progressive disclosure and AI assistance.

    This dialog displays error information with expandable details and
    provides AI-powered help when available. It supports various user
    actions including copying error details and reporting issues.

    The dialog features:
    - Clear error message display with severity indicators
    - Expandable stack trace and technical details
    - AI help integration with graceful degradation
    - Clipboard operations for error sharing
    - Professional styling with proper spacing
    """

    # Signals
    help_requested = pyqtSignal(Exception, dict)  # error, context
    retry_requested = pyqtSignal()

    def __init__(
        self,
        error: Exception,
        context: Optional[dict[str, Any]] = None,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the error dialog.

        Args:
            error: The exception that occurred
            context: Additional context about the error
            config_manager: Configuration manager for settings
            parent: Parent widget
        """
        super().__init__(parent)
        self.error = error
        self.context = context or {}
        self.config_manager = config_manager
        self.logger = logger.bind(
            component="error_dialog", error_type=type(error).__name__
        )

        # Get error details
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.stack_trace = self._get_stack_trace()
        self.timestamp = datetime.now()

        # Initialize UI
        self._init_ui()
        self._load_error_details()

        self.logger.info(
            "Error dialog created",
            error_type=self.error_type,
            has_context=bool(context),
        )

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Error")
        self.setModal(True)
        self.resize(600, 400)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Error header
        header_layout = QHBoxLayout()

        # Error icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self._set_error_icon()
        header_layout.addWidget(self.icon_label)

        # Error summary
        summary_layout = QVBoxLayout()

        # Error type label
        self.type_label = QLabel(f"<b>{self.error_type}</b>")
        summary_layout.addWidget(self.type_label)

        # Error message
        self.message_label = QLabel(self.error_message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("color: #d32f2f;")
        summary_layout.addWidget(self.message_label)

        # Timestamp
        time_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label = QLabel(f"<i>Occurred at: {time_str}</i>")
        self.time_label.setStyleSheet("color: #666;")
        summary_layout.addWidget(self.time_label)

        header_layout.addLayout(summary_layout, 1)
        layout.addLayout(header_layout)

        # Context information (if available)
        if self.context:
            context_section = self._create_context_section()
            layout.addWidget(context_section)

        # Stack trace (collapsible)
        self.details_section = self._create_details_section()
        layout.addWidget(self.details_section)

        # Action buttons
        action_layout = QHBoxLayout()

        # Copy button
        self.copy_btn = QPushButton("Copy Error")
        self.copy_btn.clicked.connect(self._copy_error_details)
        action_layout.addWidget(self.copy_btn)

        # AI Help button (only if AI available)
        if self._is_ai_available():
            self.help_btn = QPushButton("Get AI Help")
            self.help_btn.clicked.connect(self._request_ai_help)
            action_layout.addWidget(self.help_btn)

        # Report button
        self.report_btn = QPushButton("Report Issue")
        self.report_btn.clicked.connect(self._report_issue)
        action_layout.addWidget(self.report_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)

        # Add retry button for certain errors
        if self._can_retry():
            self.retry_btn = self.button_box.addButton(
                "Retry", QDialogButtonBox.ButtonRole.ActionRole
            )
            self.retry_btn.clicked.connect(self._handle_retry)

        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _set_error_icon(self) -> None:
        """Set appropriate icon based on error severity."""
        # Use built-in Qt icons or custom icons
        icon_style = self.icon_label.style()
        if isinstance(self.error, Warning):
            icon = icon_style.standardIcon(
                icon_style.StandardPixmap.SP_MessageBoxWarning
            )
        elif isinstance(self.error, (OSError, IOError, PermissionError)):
            icon = icon_style.standardIcon(
                icon_style.StandardPixmap.SP_DialogCancelButton
            )
        else:
            icon = icon_style.standardIcon(
                icon_style.StandardPixmap.SP_MessageBoxCritical
            )

        pixmap = icon.pixmap(48, 48)
        self.icon_label.setPixmap(pixmap)

    def _create_context_section(self) -> CollapsibleSection:
        """Create collapsible section for error context."""
        section = CollapsibleSection("Error Context")

        # Create context display
        context_browser = QTextBrowser()
        context_browser.setMaximumHeight(150)

        # Format context information
        context_html = "<table style='width: 100%;'>"
        for key, value in self.context.items():
            # Skip internal keys
            if key.startswith("_"):
                continue

            # Format key nicely
            display_key = key.replace("_", " ").title()

            # Format value
            if isinstance(value, (list, dict)):
                display_value = f"<pre>{value}</pre>"
            else:
                display_value = str(value)

            context_html += f"""
            <tr>
                <td style='font-weight: bold; padding-right: 10px;'>{display_key}:</td>
                <td>{display_value}</td>
            </tr>
            """

        context_html += "</table>"
        context_browser.setHtml(context_html)

        section.add_content(context_browser)
        section.set_collapsed(False)  # Show context by default

        return section

    def _create_details_section(self) -> CollapsibleSection:
        """Create collapsible section for stack trace."""
        section = CollapsibleSection("Technical Details")

        # Create stack trace display
        self.stack_browser = QTextBrowser()
        self.stack_browser.setMinimumHeight(200)
        self.stack_browser.setPlainText(self.stack_trace)

        # Use monospace font for stack trace
        font = self.stack_browser.font()
        font.setFamily("Courier New, Consolas, monospace")
        font.setPointSize(9)
        self.stack_browser.setFont(font)

        section.add_content(self.stack_browser)
        section.set_collapsed(True)  # Collapsed by default

        return section

    def _get_stack_trace(self) -> str:
        """Get formatted stack trace."""
        if hasattr(self.error, "__traceback__") and self.error.__traceback__:
            return "".join(
                traceback.format_exception(
                    type(self.error), self.error, self.error.__traceback__
                )
            )
        else:
            # If no traceback, create a minimal trace with error info and current stack
            error_info = f"{type(self.error).__name__}: {self.error}\n\n"
            current_stack = "Current call stack:\n" + "".join(
                traceback.format_stack()[:-1]
            )  # Exclude this method
            return error_info + current_stack

    def _load_error_details(self) -> None:
        """Load additional error details if available."""
        # Add any error-specific details
        if isinstance(self.error, ProjectGenerationError):
            # Add project generation specific context
            if hasattr(self.error, "template_name"):
                self.context["Template"] = self.error.template_name
            if hasattr(self.error, "operation"):
                self.context["Operation"] = self.error.operation

    def _is_ai_available(self) -> bool:
        """Check if AI service is available."""
        if not self.config_manager:
            return False

        # Check AI configuration
        ai_enabled = self.config_manager.get_setting("ai.enabled", default=True)
        return ai_enabled

    def _can_retry(self) -> bool:
        """Check if the error is retryable."""
        # Certain errors can be retried
        retryable_errors = (OSError, IOError, ConnectionError, TimeoutError)
        return isinstance(self.error, retryable_errors)

    def _copy_error_details(self) -> None:
        """Copy error details to clipboard."""
        # Format error details
        details = f"""Error Report
==============
Type: {self.error_type}
Message: {self.error_message}
Time: {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

Context:
--------
"""

        # Add context
        for key, value in self.context.items():
            if not key.startswith("_"):
                details += f"{key}: {value}\n"

        # Add stack trace
        details += f"\nStack Trace:\n{'-' * 50}\n{self.stack_trace}"

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(details)

        # Show feedback
        self.copy_btn.setText("Copied!")
        QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copy Error"))

        self.logger.info("Error details copied to clipboard")

    def _request_ai_help(self) -> None:
        """Request AI help for the error."""
        self.logger.info("AI help requested")

        # Disable button during request
        self.help_btn.setEnabled(False)
        self.help_btn.setText("Getting help...")

        # Emit signal for parent to handle
        self.help_requested.emit(self.error, self.context)

        # Re-enable after delay (parent should handle actual response)
        QTimer.singleShot(3000, self._reset_help_button)

    def _reset_help_button(self) -> None:
        """Reset help button state."""
        if hasattr(self, "help_btn"):
            self.help_btn.setEnabled(True)
            self.help_btn.setText("Get AI Help")

    def _report_issue(self) -> None:
        """Open GitHub issue template with error details."""
        # Format issue URL
        repo_url = "https://github.com/username/create-project"  # TODO: Get from config

        # Create issue title
        title = f"Error: {self.error_type} - {self.error_message[:50]}"

        # Create issue body
        body = f"""## Error Report

**Error Type:** `{self.error_type}`
**Error Message:** {self.error_message}
**Occurred At:** {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

### Context
{self._format_context_for_issue()}

### Stack Trace
```
{self.stack_trace}
```

### Steps to Reproduce
1. [Please describe the steps that led to this error]
2. 
3. 

### Expected Behavior
[What should have happened instead?]

### Environment
- OS: {sys.platform}
- Python: {sys.version.split()[0]}
- Application Version: [version]
"""

        # URL encode the parameters
        from urllib.parse import quote

        issue_url = f"{repo_url}/issues/new?title={quote(title)}&body={quote(body)}"

        # Open in browser
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(issue_url))

        self.logger.info("GitHub issue template opened")

    def _format_context_for_issue(self) -> str:
        """Format context for GitHub issue."""
        lines = []
        for key, value in self.context.items():
            if not key.startswith("_"):
                lines.append(f"- **{key}:** {value}")
        return "\n".join(lines) if lines else "No additional context available"

    def _handle_retry(self) -> None:
        """Handle retry button click."""
        self.logger.info("Retry requested")
        self.retry_requested.emit()
        self.accept()

    def show_ai_response(self, response: str) -> None:
        """Show AI response in the dialog.

        Args:
            response: AI-generated help text
        """
        # Could show inline or open AI help dialog
        # For now, we'll add it to the context section
        if response:
            # Create AI help section
            ai_section = CollapsibleSection("AI Assistance")

            ai_browser = QTextBrowser()
            ai_browser.setHtml(f"<div style='padding: 10px;'>{response}</div>")
            ai_browser.setMinimumHeight(150)

            ai_section.add_content(ai_browser)
            ai_section.set_collapsed(False)

            # Insert before details section
            layout = self.layout()
            details_index = layout.indexOf(self.details_section)
            layout.insertWidget(details_index, ai_section)

            self.logger.info("AI response displayed")
