# ABOUTME: License preview dialog widget for displaying full license text
# ABOUTME: Provides read-only view of license content with copy functionality

"""
License preview dialog widget.

This module provides a dialog for previewing full license text with:
- Read-only text display
- Copy to clipboard functionality
- Markdown/HTML rendering support
- Search functionality
"""

from typing import Optional

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from create_project.licenses.manager import LicenseManager
from create_project.utils.logger import get_logger

logger = get_logger(__name__)


class LicensePreviewDialog(QDialog):
    """Dialog for previewing license text."""

    def __init__(self, license_id: str, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the license preview dialog.

        Args:
            license_id: License identifier to preview
            parent: Parent widget
        """
        super().__init__(parent)

        self.license_id = license_id
        self.license_manager = LicenseManager()

        self._setup_ui()
        self._load_license()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("License Preview")
        self.setModal(True)
        self.resize(800, 600)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header with license name
        self.header_label = QLabel()
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        self.header_label.setFont(header_font)
        layout.addWidget(self.header_label)

        # License text browser
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setReadOnly(True)

        # Set monospace font for license text
        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_browser.setFont(font)

        # Add context menu action for copying
        copy_action = QAction("Copy All", self)
        copy_action.triggered.connect(self._copy_all_text)
        self.text_browser.addAction(copy_action)
        self.text_browser.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        layout.addWidget(self.text_browser, 1)

        # Button box with Copy and Close buttons
        button_layout = QHBoxLayout()

        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self._copy_all_text)
        button_layout.addWidget(self.copy_button)

        button_layout.addStretch()

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.close)
        button_layout.addWidget(self.button_box)

        layout.addLayout(button_layout)

        # Set focus to text browser for keyboard navigation
        self.text_browser.setFocus()

    def _load_license(self) -> None:
        """Load and display the license text."""
        try:
            # Get license info
            licenses = self.license_manager.list_licenses()
            license_info = next(
                (lic for lic in licenses if lic["id"] == self.license_id), None
            )

            if license_info:
                self.header_label.setText(f"{license_info['name']} License")
            else:
                self.header_label.setText(f"{self.license_id} License")

            # Get license text
            license_text = self.license_manager.get_license_text(self.license_id)

            if license_text:
                # Display as plain text to preserve formatting
                self.text_browser.setPlainText(license_text)
                logger.debug(f"Loaded license text for: {self.license_id}")
            else:
                self.text_browser.setPlainText(
                    f"License text not found for: {self.license_id}"
                )
                logger.warning(f"License text not found for: {self.license_id}")

        except Exception as e:
            error_msg = f"Failed to load license: {str(e)}"
            self.text_browser.setPlainText(error_msg)
            logger.error(error_msg)

    def _copy_all_text(self) -> None:
        """Copy all license text to clipboard."""
        try:
            from PyQt6.QtWidgets import QApplication

            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(self.text_browser.toPlainText())

                # Update button text temporarily
                self.copy_button.setText("Copied!")

                # Reset button text after 2 seconds
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(
                    2000, lambda: self.copy_button.setText("Copy to Clipboard")
                )

                logger.debug(f"Copied license text to clipboard: {self.license_id}")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")

    def sizeHint(self) -> QSize:
        """
        Provide size hint for the dialog.

        Returns:
            Recommended size
        """
        return QSize(800, 600)
