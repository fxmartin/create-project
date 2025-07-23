# ABOUTME: Collapsible section widget for grouping content with expand/collapse functionality
# ABOUTME: Provides animated transitions and customizable styling for section headers

"""CollapsibleSection widget for grouping content.

This widget provides a collapsible container with a clickable header
that expands/collapses the content area with smooth animations.
"""

from typing import Optional

from PyQt6.QtCore import QPropertyAnimation, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    """A collapsible section widget with title and content.
    
    This widget provides a clickable header that expands/collapses
    a content area with smooth animations. Useful for organizing
    UI elements into logical groups that can be hidden when not needed.
    
    Signals:
        toggled: Emitted when section is expanded/collapsed (bool)
    """
    
    toggled = pyqtSignal(bool)  # True = expanded, False = collapsed
    
    def __init__(
        self, 
        title: str, 
        parent: Optional[QWidget] = None,
        collapsed: bool = False
    ) -> None:
        """Initialize the collapsible section.
        
        Args:
            title: Section title displayed in the header
            parent: Parent widget
            collapsed: Whether to start in collapsed state
        """
        super().__init__(parent)
        self._is_collapsed = collapsed
        self._animation = QPropertyAnimation(self, b"minimumHeight")
        self._animation.setDuration(200)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header button
        self._header = QPushButton(title)
        self._header.setCheckable(True)
        self._header.setChecked(not collapsed)
        self._header.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                border: 1px solid #ccc;
                background-color: #f0f0f0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                border-bottom: none;
            }
            QPushButton::indicator {
                width: 0;
                height: 0;
            }
        """)
        
        # Add arrow indicator to text
        self._update_header_text(title)
        self._header.toggled.connect(self._toggle_content)
        layout.addWidget(self._header)
        
        # Content frame
        self._content_frame = QFrame()
        self._content_frame.setFrameStyle(QFrame.Shape.Box)
        self._content_frame.setStyleSheet("border: 1px solid #ccc; border-top: none;")
        self._content_layout = QVBoxLayout(self._content_frame)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._content_frame)
        
        # Apply initial state
        if collapsed:
            self._content_frame.hide()
            
    def add_content(self, widget: QWidget) -> None:
        """Add a widget to the content area.
        
        Args:
            widget: Widget to add to content area
        """
        self._content_layout.addWidget(widget)
        
    def add_layout(self, layout: QVBoxLayout) -> None:
        """Add a layout to the content area.
        
        Args:
            layout: Layout to add to content area
        """
        self._content_layout.addLayout(layout)
        
    def set_content_layout(self, layout: QVBoxLayout) -> None:
        """Replace the content layout.
        
        Args:
            layout: New layout for content area
        """
        # Remove existing layout
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Set new layout
        self._content_layout = layout
        self._content_frame.setLayout(layout)
        
    def is_collapsed(self) -> bool:
        """Check if the section is collapsed.
        
        Returns:
            True if section is collapsed
        """
        return self._is_collapsed
        
    def set_collapsed(self, collapsed: bool) -> None:
        """Set the collapsed state.
        
        Args:
            collapsed: Whether to collapse the section
        """
        if self._is_collapsed != collapsed:
            self._header.setChecked(not collapsed)
            
    def set_title(self, title: str) -> None:
        """Update the section title.
        
        Args:
            title: New title for the section
        """
        self._update_header_text(title)
        
    def _update_header_text(self, title: str) -> None:
        """Update header text with arrow indicator.
        
        Args:
            title: Base title text
        """
        arrow = "▼" if not self._is_collapsed else "▶"
        self._header.setText(f"{arrow} {title}")
        
    def _toggle_content(self, checked: bool) -> None:
        """Toggle content visibility.
        
        Args:
            checked: Whether section is expanded
        """
        self._is_collapsed = not checked
        
        # Update arrow
        title = self._header.text()[2:]  # Remove old arrow
        self._update_header_text(title)
        
        # Show/hide content
        if self._is_collapsed:
            self._content_frame.hide()
        else:
            self._content_frame.show()
            
        # Emit signal
        self.toggled.emit(not self._is_collapsed)
        
    def clear_content(self) -> None:
        """Remove all widgets from the content area."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()