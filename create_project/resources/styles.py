# ABOUTME: Style management system with theme support and constants
# ABOUTME: Provides centralized styling for consistent UI appearance

"""Style management module for the Create Project application.

This module provides a centralized system for managing styles and themes
used throughout the GUI. It includes:
- Color constants and palettes
- Font definitions
- Spacing and sizing constants
- Theme management
- QSS stylesheet generation
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtGui import QColor, QFont, QPalette

logger = logging.getLogger(__name__)

# Style directory path
STYLE_DIR = Path(__file__).parent / "styles"

# Color Palettes
COLORS = {
    "light": {
        # Primary colors
        "primary": "#2196F3",
        "primary_dark": "#1976D2",
        "primary_light": "#64B5F6",
        
        # Secondary colors
        "secondary": "#FFC107",
        "secondary_dark": "#FFA000",
        "secondary_light": "#FFD54F",
        
        # Status colors
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
        "info": "#2196F3",
        
        # Neutral colors
        "background": "#FAFAFA",
        "surface": "#FFFFFF",
        "text_primary": "#212121",
        "text_secondary": "#757575",
        "text_disabled": "#BDBDBD",
        "border": "#E0E0E0",
        "hover": "#F5F5F5",
        "selected": "#E3F2FD",
    },
    "dark": {
        # Primary colors
        "primary": "#2196F3",
        "primary_dark": "#1565C0",
        "primary_light": "#42A5F5",
        
        # Secondary colors
        "secondary": "#FFC107",
        "secondary_dark": "#F57C00",
        "secondary_light": "#FFB300",
        
        # Status colors
        "success": "#66BB6A",
        "warning": "#FFA726",
        "error": "#EF5350",
        "info": "#42A5F5",
        
        # Neutral colors
        "background": "#121212",
        "surface": "#1E1E1E",
        "text_primary": "#FFFFFF",
        "text_secondary": "#B0B0B0",
        "text_disabled": "#606060",
        "border": "#333333",
        "hover": "#2A2A2A",
        "selected": "#1565C0",
    }
}

# Font definitions
FONTS = {
    "default": {
        "family": "Segoe UI, Roboto, Arial, sans-serif",
        "size": 10,
    },
    "heading": {
        "family": "Segoe UI, Roboto, Arial, sans-serif",
        "size": 14,
        "weight": QFont.Weight.Bold,
    },
    "subheading": {
        "family": "Segoe UI, Roboto, Arial, sans-serif",
        "size": 12,
        "weight": QFont.Weight.Medium,
    },
    "monospace": {
        "family": "Consolas, Monaco, 'Courier New', monospace",
        "size": 10,
    },
    "small": {
        "family": "Segoe UI, Roboto, Arial, sans-serif",
        "size": 9,
    },
}

# Spacing constants
SPACING = {
    "tiny": 4,
    "small": 8,
    "medium": 16,
    "large": 24,
    "xlarge": 32,
}

# Size constants
SIZES = {
    "button_height": 32,
    "input_height": 32,
    "icon_small": 16,
    "icon_medium": 24,
    "icon_large": 32,
    "border_radius": 4,
    "dialog_min_width": 400,
    "dialog_min_height": 300,
}


class StyleManager:
    """Manages application styles and themes."""

    _instance: Optional[StyleManager] = None
    _cache: Dict[str, str] = {}

    def __new__(cls) -> StyleManager:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize style manager."""
        if self._initialized:
            return

        self._initialized = True
        self._theme = "light"
        self._custom_styles = {}
        
        # Create style directory if it doesn't exist
        STYLE_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Style manager initialized with theme: {self._theme}")

    def get_color(self, name: str, theme: Optional[str] = None) -> str:
        """Get a color value by name.

        Args:
            name: Color name
            theme: Optional theme override

        Returns:
            Color hex string
        """
        theme_name = theme or self._theme
        theme_colors = COLORS.get(theme_name, COLORS["light"])
        return theme_colors.get(name, "#000000")

    def get_font(self, name: str = "default") -> QFont:
        """Get a font by name.

        Args:
            name: Font name

        Returns:
            QFont instance
        """
        font_def = FONTS.get(name, FONTS["default"])
        font = QFont(font_def["family"])
        font.setPointSize(font_def["size"])
        if "weight" in font_def:
            font.setWeight(font_def["weight"])
        return font

    def get_spacing(self, size: str = "medium") -> int:
        """Get spacing value by size.

        Args:
            size: Size name

        Returns:
            Spacing in pixels
        """
        return SPACING.get(size, SPACING["medium"])

    def get_size(self, name: str) -> int:
        """Get size constant by name.

        Args:
            name: Size name

        Returns:
            Size in pixels
        """
        return SIZES.get(name, 0)

    def get_stylesheet(self, component: Optional[str] = None) -> str:
        """Get QSS stylesheet for a component or the entire application.

        Args:
            component: Optional component name

        Returns:
            QSS stylesheet string
        """
        cache_key = f"{self._theme}/{component or 'global'}"
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Generate stylesheet
        if component:
            stylesheet = self._generate_component_stylesheet(component)
        else:
            stylesheet = self._generate_global_stylesheet()
        
        # Cache and return
        self._cache[cache_key] = stylesheet
        return stylesheet

    def _generate_global_stylesheet(self) -> str:
        """Generate global application stylesheet.

        Returns:
            QSS stylesheet string
        """
        colors = COLORS[self._theme]
        
        return f"""
/* Global Application Stylesheet */
QWidget {{
    background-color: {colors['background']};
    color: {colors['text_primary']};
    font-family: {FONTS['default']['family']};
    font-size: {FONTS['default']['size']}pt;
}}

/* Buttons */
QPushButton {{
    background-color: {colors['surface']};
    border: 1px solid {colors['border']};
    border-radius: {SIZES['border_radius']}px;
    padding: {SPACING['small']}px {SPACING['medium']}px;
    min-height: {SIZES['button_height']}px;
}}

QPushButton:hover {{
    background-color: {colors['hover']};
}}

QPushButton:pressed {{
    background-color: {colors['selected']};
}}

QPushButton:disabled {{
    color: {colors['text_disabled']};
    border-color: {colors['text_disabled']};
}}

QPushButton[primary="true"] {{
    background-color: {colors['primary']};
    color: white;
    border: none;
}}

QPushButton[primary="true"]:hover {{
    background-color: {colors['primary_dark']};
}}

/* Input fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {colors['surface']};
    border: 1px solid {colors['border']};
    border-radius: {SIZES['border_radius']}px;
    padding: {SPACING['small']}px;
    min-height: {SIZES['input_height']}px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, 
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {colors['primary']};
}}

/* Lists and Trees */
QListWidget, QTreeWidget, QTableWidget {{
    background-color: {colors['surface']};
    border: 1px solid {colors['border']};
    border-radius: {SIZES['border_radius']}px;
    outline: none;
}}

QListWidget::item, QTreeWidget::item, QTableWidget::item {{
    padding: {SPACING['small']}px;
}}

QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {{
    background-color: {colors['hover']};
}}

QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {{
    background-color: {colors['selected']};
    color: {colors['text_primary']};
}}

/* Labels */
QLabel {{
    color: {colors['text_primary']};
}}

QLabel[secondary="true"] {{
    color: {colors['text_secondary']};
}}

QLabel[error="true"] {{
    color: {colors['error']};
}}

/* Group Boxes */
QGroupBox {{
    border: 1px solid {colors['border']};
    border-radius: {SIZES['border_radius']}px;
    margin-top: {SPACING['small']}px;
    padding-top: {SPACING['medium']}px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: {SPACING['small']}px;
    padding: 0 {SPACING['tiny']}px;
    background-color: {colors['background']};
}}

/* Tabs */
QTabWidget::pane {{
    border: 1px solid {colors['border']};
    background-color: {colors['surface']};
}}

QTabBar::tab {{
    background-color: {colors['background']};
    padding: {SPACING['small']}px {SPACING['medium']}px;
    margin-right: {SPACING['tiny']}px;
}}

QTabBar::tab:selected {{
    background-color: {colors['surface']};
    border-bottom: 2px solid {colors['primary']};
}}

/* Progress bars */
QProgressBar {{
    border: 1px solid {colors['border']};
    border-radius: {SIZES['border_radius']}px;
    text-align: center;
    background-color: {colors['surface']};
}}

QProgressBar::chunk {{
    background-color: {colors['primary']};
    border-radius: {SIZES['border_radius']}px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    width: 12px;
    background-color: {colors['background']};
}}

QScrollBar::handle:vertical {{
    background-color: {colors['border']};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors['text_secondary']};
}}

/* Dialogs */
QDialog {{
    background-color: {colors['background']};
}}

/* Message Boxes */
QMessageBox {{
    background-color: {colors['background']};
}}
        """.strip()

    def _generate_component_stylesheet(self, component: str) -> str:
        """Generate stylesheet for a specific component.

        Args:
            component: Component name

        Returns:
            QSS stylesheet string
        """
        # Add component-specific styles here
        return ""

    def set_theme(self, theme: str) -> None:
        """Set the current theme.

        Args:
            theme: Theme name ("light" or "dark")
        """
        if theme in COLORS and theme != self._theme:
            self._theme = theme
            # Clear cache to regenerate with new theme
            self._cache.clear()
            logger.info(f"Theme changed to: {theme}")

    def apply_palette(self, app) -> None:
        """Apply theme colors to application palette.

        Args:
            app: QApplication instance
        """
        colors = COLORS[self._theme]
        palette = QPalette()
        
        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(colors["background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text_primary"]))
        
        # Base colors (for input widgets)
        palette.setColor(QPalette.ColorRole.Base, QColor(colors["surface"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["hover"]))
        
        # Text colors
        palette.setColor(QPalette.ColorRole.Text, QColor(colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(colors["text_secondary"]))
        
        # Button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(colors["surface"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text_primary"]))
        
        # Highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["primary"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        
        app.setPalette(palette)


# Convenience functions
_manager = StyleManager()


def get_color(name: str) -> str:
    """Get a color value by name.

    Args:
        name: Color name

    Returns:
        Color hex string
    """
    return _manager.get_color(name)


def get_font(name: str = "default") -> QFont:
    """Get a font by name.

    Args:
        name: Font name

    Returns:
        QFont instance
    """
    return _manager.get_font(name)


def get_spacing(size: str = "medium") -> int:
    """Get spacing value by size.

    Args:
        size: Size name

    Returns:
        Spacing in pixels
    """
    return _manager.get_spacing(size)


def get_style_sheet(component: Optional[str] = None) -> str:
    """Get QSS stylesheet.

    Args:
        component: Optional component name

    Returns:
        QSS stylesheet string
    """
    return _manager.get_stylesheet(component)


def set_theme(theme: str) -> None:
    """Set the global theme.

    Args:
        theme: Theme name
    """
    _manager.set_theme(theme)


def apply_theme(app) -> None:
    """Apply theme to application.

    Args:
        app: QApplication instance
    """
    _manager.apply_palette(app)
    app.setStyleSheet(_manager.get_stylesheet())