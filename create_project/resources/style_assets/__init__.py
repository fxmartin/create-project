# ABOUTME: Styles module containing Qt stylesheets for UI theming
# ABOUTME: Provides consistent visual styling across all widgets

"""
Styles module for the Create Project application.

This module manages Qt stylesheets (QSS) for consistent visual appearance.
Supports multiple themes and platform-specific adjustments.
"""

from ..styles import (
    COLORS,
    FONTS,
    SIZES,
    SPACING,
    StyleManager,
    get_color,
    get_font,
    get_spacing,
    get_style_sheet,
    set_theme,
    apply_theme,
)

__all__ = [
    "COLORS",
    "FONTS", 
    "SIZES",
    "SPACING",
    "StyleManager",
    "get_color",
    "get_font", 
    "get_spacing",
    "get_style_sheet",
    "set_theme",
    "apply_theme",
]
