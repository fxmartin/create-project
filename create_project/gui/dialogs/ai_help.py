# ABOUTME: GUI dialog for displaying AI-powered help suggestions
# ABOUTME: Provides streaming display, markdown rendering, and retry functionality

"""AI Help Dialog implementation for displaying AI-powered suggestions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from create_project.ai.ai_service import AIService

logger = logging.getLogger(__name__)


class AIQueryWorker(QThread):
    """Worker thread for querying AI service."""

    # Signals
    response_chunk = pyqtSignal(str)  # Emitted for each chunk of response
    response_complete = pyqtSignal(str)  # Emitted when response is complete
    error_occurred = pyqtSignal(str)  # Emitted on error

    def __init__(
        self,
        ai_service: AIService,
        error: Exception,
        context: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        """Initialize AI query worker.

        Args:
            ai_service: AI service instance
            error: Exception that occurred
            context: Additional context for AI
            parent: Parent widget
        """
        super().__init__(parent)
        self.ai_service = ai_service
        self.error = error
        self.context = context
        self._should_stop = False

    def stop(self) -> None:
        """Request the worker to stop."""
        self._should_stop = True

    def run(self) -> None:
        """Run the AI query in the background thread."""
        try:
            # Check if streaming is supported
            if hasattr(self.ai_service, "stream_help_response"):
                # Use streaming response
                full_response = []
                for chunk in self.ai_service.stream_help_response(
                    error=self.error,
                    template=self.context.get("template"),
                    project_vars=self.context.get("project_vars", {}),
                    target_path=self.context.get("target_path"),
                    options=self.context.get("options", {}),
                    attempted_operations=self.context.get("attempted_operations", []),
                    partial_results=self.context.get("partial_results", {}),
                ):
                    if self._should_stop:
                        return
                    full_response.append(chunk)
                    self.response_chunk.emit(chunk)

                self.response_complete.emit("".join(full_response))
            else:
                # Use non-streaming response
                response = self.ai_service.generate_help_response(
                    error=self.error,
                    template=self.context.get("template"),
                    project_vars=self.context.get("project_vars", {}),
                    target_path=self.context.get("target_path"),
                    options=self.context.get("options", {}),
                    attempted_operations=self.context.get("attempted_operations", []),
                    partial_results=self.context.get("partial_results", {}),
                )
                self.response_complete.emit(response)

        except Exception as e:
            logger.error(f"Error querying AI service: {e}")
            self.error_occurred.emit(str(e))


class AIHelpDialog(QDialog):
    """Dialog for displaying AI-powered help suggestions."""

    def __init__(
        self,
        ai_service: AIService,
        error: Exception,
        context: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize AI help dialog.

        Args:
            ai_service: AI service instance
            error: Exception that occurred
            context: Additional context for AI
            parent: Parent widget
        """
        super().__init__(parent)
        self.ai_service = ai_service
        self.error = error
        self.context = context or {}
        self.worker: AIQueryWorker | None = None

        self.setWindowTitle("AI Assistant")
        self.setModal(True)
        self.resize(700, 500)

        self._setup_ui()
        self._start_query()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()
        self.status_label = QLabel("Consulting AI assistant...")
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Loading indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)

        # Response display
        self.response_browser = QTextBrowser()
        self.response_browser.setOpenExternalLinks(True)
        font = QFont()
        font.setFamily("Consolas, Monaco, 'Courier New', monospace")
        self.response_browser.setFont(font)
        layout.addWidget(self.response_browser)

        # Action buttons
        button_layout = QHBoxLayout()

        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self._copy_response)
        self.copy_button.setEnabled(False)
        button_layout.addWidget(self.copy_button)

        self.retry_button = QPushButton("Try Again")
        self.retry_button.clicked.connect(self._retry_query)
        self.retry_button.setEnabled(False)
        button_layout.addWidget(self.retry_button)

        button_layout.addStretch()

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _start_query(self) -> None:
        """Start the AI query in a background thread."""
        logger.info("Starting AI query for error help")

        # Clear previous content
        self.response_browser.clear()
        self.progress_bar.setVisible(True)
        self.status_label.setText("Consulting AI assistant...")
        self.copy_button.setEnabled(False)
        self.retry_button.setEnabled(False)

        # Create and start worker thread
        self.worker = AIQueryWorker(
            self.ai_service, self.error, self.context, self
        )
        self.worker.response_chunk.connect(self._handle_response_chunk)
        self.worker.response_complete.connect(self._handle_response_complete)
        self.worker.error_occurred.connect(self._handle_error)
        self.worker.start()

    def _handle_response_chunk(self, chunk: str) -> None:
        """Handle a chunk of streaming response.

        Args:
            chunk: Response chunk
        """
        # Append chunk to browser
        cursor = self.response_browser.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.response_browser.setTextCursor(cursor)

        # Auto-scroll to bottom
        scrollbar = self.response_browser.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def _handle_response_complete(self, response: str) -> None:
        """Handle complete AI response.

        Args:
            response: Complete response text
        """
        logger.info("AI response received successfully")

        # Update UI
        self.progress_bar.setVisible(False)
        self.status_label.setText("AI suggestion received:")

        # Set complete response (in case it wasn't streamed)
        if not self.response_browser.toPlainText():
            self._set_response_html(response)

        # Enable action buttons
        self.copy_button.setEnabled(True)
        self.retry_button.setEnabled(True)

    def _handle_error(self, error_msg: str) -> None:
        """Handle AI query error.

        Args:
            error_msg: Error message
        """
        logger.error(f"AI query failed: {error_msg}")

        # Update UI
        self.progress_bar.setVisible(False)
        self.status_label.setText("Failed to get AI suggestion")

        # Show error in browser
        self.response_browser.setHtml(
            f"""
            <div style="color: #dc3545;">
                <h3>Unable to get AI suggestion</h3>
                <p>{error_msg}</p>
                <p>Please check your AI service configuration and try again.</p>
            </div>
            """
        )

        # Enable retry button
        self.retry_button.setEnabled(True)

    def _set_response_html(self, response: str) -> None:
        """Set response with basic markdown to HTML conversion.

        Args:
            response: Response text (potentially markdown)
        """
        # Basic markdown to HTML conversion
        html = response

        # Convert code blocks
        html = html.replace(
            "```python",
            '<pre style="background: #f4f4f4; padding: 10px; '
            'border-radius: 5px;"><code>',
        )
        html = html.replace("```", "</code></pre>")

        # Convert inline code
        import re
        html = re.sub(
            r"`([^`]+)`",
            r'<code style="background: #f4f4f4; padding: 2px 4px; '
            r'border-radius: 3px;">\1</code>',
            html,
        )

        # Convert headers
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Convert bold
        html = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", html)

        # Convert italic
        html = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", html)

        # Convert line breaks
        html = html.replace("\n", "<br>")

        # Wrap in basic HTML
        full_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                pre {{ overflow-x: auto; }}
                code {{ font-family: 'Consolas', 'Monaco', monospace; }}
            </style>
        </head>
        <body>
            {html}
        </body>
        </html>
        """

        self.response_browser.setHtml(full_html)

    def _copy_response(self) -> None:
        """Copy AI response to clipboard."""
        response = self.response_browser.toPlainText()
        if response:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(response)
                self.status_label.setText("Response copied to clipboard!")

                # Reset status after 2 seconds
                QTimer.singleShot(
                    2000, lambda: self.status_label.setText("AI suggestion received:")
                )

    def _retry_query(self) -> None:
        """Retry the AI query."""
        logger.info("Retrying AI query")

        # Stop current worker if running
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        # Start new query
        self._start_query()

    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event."""
        # Stop worker thread if running
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        super().closeEvent(event)

