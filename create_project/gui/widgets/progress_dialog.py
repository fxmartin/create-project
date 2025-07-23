# ABOUTME: Custom progress dialog for project generation with enhanced status updates
# ABOUTME: Provides modal dialog with progress bar, status messages, cancel confirmation, and thread-safe updates

"""
Custom progress dialog for project generation.

This module provides an enhanced progress dialog that displays detailed
progress during project generation, with support for status updates,
cancellation with confirmation, and thread-safe operations.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QDialogButtonBox,
    QWidget,
)
from PyQt6.QtGui import QFont, QIcon

from structlog import get_logger

logger = get_logger(__name__)


class ProgressDialog(QDialog):
    """Enhanced progress dialog for project generation.
    
    Features:
    - Modal dialog with progress bar
    - Status message updates
    - Detailed log display
    - Cancel button with confirmation
    - Thread-safe update methods
    - Auto-close on completion
    
    Signals:
        cancelled: Emitted when user confirms cancellation
    """
    
    cancelled = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the progress dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._cancelled = False
        self._finished = False
        self._auto_close_timer: Optional[QTimer] = None
        
        self._setup_ui()
        self._apply_styles()
        
        logger.debug("ProgressDialog initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Creating Project")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Remove window close button to force use of Cancel
        self.setWindowFlags(
            self.windowFlags() 
            & ~Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Title label
        self.title_label = QLabel("Project Generation in Progress")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Details section
        details_label = QLabel("Details:")
        details_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(details_label)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(150)
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_display)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Add some stretch at the bottom
        layout.addStretch()
    
    def _apply_styles(self) -> None:
        """Apply visual styles to the dialog."""
        self.setStyleSheet("""
            ProgressDialog {
                background-color: white;
            }
            
            QLabel {
                color: #333;
            }
            
            QProgressBar {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                text-align: center;
                height: 24px;
            }
            
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
            
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #999;
            }
        """)
    
    @pyqtSlot()
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self._finished:
            self.accept()
            return
        
        # Show confirmation dialog
        reply = QMessageBox.warning(
            self,
            "Cancel Project Generation",
            "Are you sure you want to cancel project generation?\n\n"
            "This will stop the process and may leave the project in an incomplete state.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logger.info("User confirmed cancellation")
            self._cancelled = True
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling...")
            self.cancelled.emit()
    
    def update_progress(self, percentage: int, message: str) -> None:
        """Update progress bar and status message.
        
        Thread-safe method to update progress.
        
        Args:
            percentage: Progress percentage (0-100)
            message: Status message to display
        """
        if self._cancelled:
            return
            
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
        
        # Add to log display
        self.add_log_entry(f"[{percentage}%] {message}")
        
        logger.debug("Progress updated", percentage=percentage, message=message)
    
    def add_log_entry(self, entry: str) -> None:
        """Add entry to the log display.
        
        Thread-safe method to add log entries.
        
        Args:
            entry: Log entry to add
        """
        # Append to log and scroll to bottom
        self.log_display.append(entry)
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def set_finished(self, success: bool, message: str) -> None:
        """Set dialog to finished state.
        
        Args:
            success: Whether generation was successful
            message: Final status message
        """
        self._finished = True
        
        if success:
            self.progress_bar.setValue(100)
            self.title_label.setText("Project Created Successfully!")
            self.status_label.setText(message)
            self.cancel_button.setText("Close")
            self.cancel_button.setEnabled(True)
            
            # Add success entry to log
            self.add_log_entry(f"\n✓ SUCCESS: {message}")
            
            # Auto-close after 2 seconds
            self._auto_close_timer = QTimer()
            self._auto_close_timer.timeout.connect(self.accept)
            self._auto_close_timer.start(2000)
            
        else:
            self.title_label.setText("Project Generation Failed")
            self.status_label.setText(message)
            self.cancel_button.setText("Close")
            self.cancel_button.setEnabled(True)
            
            # Add error entry to log  
            self.add_log_entry(f"\n✗ ERROR: {message}")
            
            # Change progress bar color to red
            self.progress_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #f44336;
                }
            """)
        
        logger.info("Progress dialog finished", success=success, message=message)
    
    def set_cancelled(self) -> None:
        """Set dialog to cancelled state."""
        self._finished = True
        self._cancelled = True
        
        self.title_label.setText("Project Generation Cancelled")
        self.status_label.setText("The operation was cancelled by user request.")
        self.cancel_button.setText("Close")
        self.cancel_button.setEnabled(True)
        
        # Add cancelled entry to log
        self.add_log_entry("\n⚠ CANCELLED: Operation cancelled by user")
        
        # Change progress bar color to orange
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk {
                background-color: #FF9800;
            }
        """)
        
        logger.info("Progress dialog cancelled")
    
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled.
        
        Returns:
            True if user cancelled the operation
        """
        return self._cancelled
    
    def closeEvent(self, event) -> None:
        """Handle close event.
        
        Prevents closing while operation is in progress.
        """
        if not self._finished:
            event.ignore()
            self._on_cancel_clicked()
        else:
            if self._auto_close_timer:
                self._auto_close_timer.stop()
            super().closeEvent(event)