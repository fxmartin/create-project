# ABOUTME: Recovery dialog for presenting error recovery options to users with AI assistance
# ABOUTME: Displays error details, recovery strategies, and allows users to choose recovery actions

"""Recovery dialog for error recovery during project generation.

This dialog presents users with recovery options when errors occur during
project generation, including AI-powered suggestions and multiple recovery
strategies.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QRadioButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...config.config_manager import ConfigManager
from ...core.error_recovery import RecoveryContext, RecoveryStrategy
from ..widgets.collapsible_section import CollapsibleSection


class RecoveryDialog(QDialog):
    """Dialog for presenting error recovery options to users."""

    # Signals
    recovery_selected = pyqtSignal(RecoveryStrategy)  # Emitted when user selects recovery
    ai_help_requested = pyqtSignal(RecoveryContext)  # Request AI help

    def __init__(
        self,
        context: RecoveryContext,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize recovery dialog.
        
        Args:
            context: Recovery context with error information
            config_manager: Configuration manager
            parent: Parent widget
        """
        super().__init__(parent)
        self.context = context
        self.config_manager = config_manager
        self.selected_strategy: Optional[RecoveryStrategy] = None

        self.setWindowTitle("Project Generation Error - Recovery Options")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._init_ui()
        self._populate_content()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Error summary
        self.error_summary = QLabel()
        self.error_summary.setWordWrap(True)
        self.error_summary.setStyleSheet("""
            QLabel {
                background-color: #ffebee;
                color: #c62828;
                padding: 15px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.error_summary)

        # Error details section
        self.details_section = CollapsibleSection("Error Details")
        self.error_details = QTextBrowser()
        self.error_details.setMaximumHeight(150)
        details_layout = QVBoxLayout()
        details_layout.addWidget(self.error_details)
        self.details_section.set_content_layout(details_layout)
        layout.addWidget(self.details_section)

        # Recovery options
        self.options_group = QGroupBox("Recovery Options")
        options_layout = QVBoxLayout()
        self.options_group.setLayout(options_layout)

        self.strategy_group = QButtonGroup(self)
        self.strategy_buttons = {}

        # Create radio buttons for each strategy
        strategies = [
            (RecoveryStrategy.RETRY_OPERATION, "Retry Operation",
             "Try the failed operation again (good for temporary errors)"),
            (RecoveryStrategy.PARTIAL_RECOVERY, "Partial Recovery",
             "Keep completed parts and retry from last successful step"),
            (RecoveryStrategy.SKIP_AND_CONTINUE, "Skip and Continue",
             "Skip the failed step and continue (may result in incomplete project)"),
            (RecoveryStrategy.FULL_ROLLBACK, "Full Rollback",
             "Remove all created files and start over"),
            (RecoveryStrategy.ABORT, "Abort",
             "Stop the process without cleanup"),
        ]

        for strategy, label, description in strategies:
            button = QRadioButton(label)
            button.setToolTip(description)
            self.strategy_buttons[strategy] = button
            self.strategy_group.addButton(button)

            # Add description label
            desc_label = QLabel(f"    {description}")
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; font-size: 11px;")

            options_layout.addWidget(button)
            options_layout.addWidget(desc_label)
            options_layout.addSpacing(5)

        layout.addWidget(self.options_group)

        # AI suggestions section (if available)
        self.ai_section = CollapsibleSection("AI Suggestions")
        self.ai_suggestions = QTextBrowser()
        self.ai_suggestions.setMaximumHeight(200)
        ai_layout = QVBoxLayout()
        ai_layout.addWidget(self.ai_suggestions)

        # Add "Get AI Help" button if AI is enabled
        if self._is_ai_enabled():
            self.ai_help_button = QPushButton("Get AI Help")
            self.ai_help_button.clicked.connect(self._on_ai_help_clicked)
            ai_layout.addWidget(self.ai_help_button)

        self.ai_section.set_content_layout(ai_layout)
        layout.addWidget(self.ai_section)

        # Progress information
        self.progress_section = CollapsibleSection("Progress Information")
        self.progress_info = QTextBrowser()
        self.progress_info.setMaximumHeight(150)
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(self.progress_info)
        self.progress_section.set_content_layout(progress_layout)
        layout.addWidget(self.progress_section)

        layout.addStretch()

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        # Rename OK button to "Execute Recovery"
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("Execute Recovery")

        layout.addWidget(self.button_box)

    def _populate_content(self) -> None:
        """Populate dialog with error and recovery information."""
        # Error summary
        error_type = type(self.context.error).__name__
        self.error_summary.setText(
            f"Error: {error_type} occurred during {self.context.current_phase}\n"
            f"Failed operation: {self.context.failed_operation}"
        )

        # Error details
        details_html = f"""
        <h4>Error Details</h4>
        <p><b>Type:</b> {error_type}</p>
        <p><b>Message:</b> {str(self.context.error)}</p>
        <p><b>Phase:</b> {self.context.current_phase}</p>
        <p><b>Template:</b> {self.context.template_name}</p>
        <p><b>Target Path:</b> {self.context.target_path}</p>
        """
        self.error_details.setHtml(details_html)

        # Set suggested strategy if available
        if self.context.suggested_strategy:
            button = self.strategy_buttons.get(self.context.suggested_strategy)
            if button:
                button.setChecked(True)

        # AI suggestions if available
        if self.context.ai_suggestions:
            self.ai_suggestions.setHtml(self._format_ai_suggestions(self.context.ai_suggestions))
            self.ai_section.expand()
        else:
            self.ai_section.collapse()

        # Progress information
        progress_html = self._generate_progress_html()
        self.progress_info.setHtml(progress_html)

    def _generate_progress_html(self) -> str:
        """Generate HTML for progress information."""
        html = ["<h4>Progress Information</h4>"]

        # Recovery points
        if self.context.recovery_points:
            html.append("<p><b>Recovery Points:</b></p><ul>")
            for point in self.context.recovery_points:
                status = "✓" if not point.state_data.get("skipped") else "⚠"
                html.append(
                    f"<li>{status} {point.phase}: {point.description} "
                    f"({len(point.created_paths)} files)</li>"
                )
            html.append("</ul>")

        # Partial results
        if self.context.partial_results:
            html.append("<p><b>Completed Operations:</b></p><ul>")
            for key, value in self.context.partial_results.items():
                if isinstance(value, bool) and value:
                    html.append(f"<li>✓ {key.replace('_', ' ').title()}</li>")
                elif isinstance(value, int) and value > 0:
                    html.append(f"<li>✓ {key.replace('_', ' ').title()}: {value}</li>")
            html.append("</ul>")

        return "".join(html)

    def _format_ai_suggestions(self, suggestions: str) -> str:
        """Format AI suggestions as HTML.
        
        Args:
            suggestions: Raw AI suggestions text
            
        Returns:
            Formatted HTML
        """
        # Basic markdown to HTML conversion
        lines = suggestions.split("\n")
        html_lines = ["<div style='font-family: monospace;'>"]

        for line in lines:
            if line.startswith("# "):
                html_lines.append(f"<h3>{line[2:]}</h3>")
            elif line.startswith("## "):
                html_lines.append(f"<h4>{line[3:]}</h4>")
            elif line.startswith("- ") or line.startswith("* "):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line.strip().startswith("```"):
                # Skip code blocks for now
                continue
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")

        html_lines.append("</div>")
        return "".join(html_lines)

    def _is_ai_enabled(self) -> bool:
        """Check if AI service is enabled."""
        if not self.config_manager:
            return False

        try:
            return self.config_manager.get("ai.enabled", False)
        except Exception:
            return False

    def _on_ai_help_clicked(self) -> None:
        """Handle AI help button click."""
        self.ai_help_requested.emit(self.context)

    def _on_accept(self) -> None:
        """Handle accept button click."""
        # Get selected strategy
        for strategy, button in self.strategy_buttons.items():
            if button.isChecked():
                self.selected_strategy = strategy
                break

        if self.selected_strategy:
            self.recovery_selected.emit(self.selected_strategy)
            self.accept()
        else:
            # Show error if no strategy selected
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Strategy Selected",
                "Please select a recovery strategy before proceeding.",
            )

    def get_selected_strategy(self) -> Optional[RecoveryStrategy]:
        """Get the selected recovery strategy.
        
        Returns:
            Selected strategy or None
        """
        return self.selected_strategy

    def update_ai_suggestions(self, suggestions: str) -> None:
        """Update AI suggestions in the dialog.
        
        Args:
            suggestions: New AI suggestions
        """
        self.context.ai_suggestions = suggestions
        self.ai_suggestions.setHtml(self._format_ai_suggestions(suggestions))
        self.ai_section.expand()

        # Update suggested strategy based on AI response
        if "retry" in suggestions.lower():
            self.strategy_buttons[RecoveryStrategy.RETRY_OPERATION].setChecked(True)
        elif "partial" in suggestions.lower() or "keep" in suggestions.lower():
            self.strategy_buttons[RecoveryStrategy.PARTIAL_RECOVERY].setChecked(True)
        elif "skip" in suggestions.lower():
            self.strategy_buttons[RecoveryStrategy.SKIP_AND_CONTINUE].setChecked(True)
        elif "rollback" in suggestions.lower() or "start over" in suggestions.lower():
            self.strategy_buttons[RecoveryStrategy.FULL_ROLLBACK].setChecked(True)
