# ABOUTME: Resources module containing icons, styles, and other UI assets
# ABOUTME: Provides centralized resource management for the GUI application

"""
Resources module for the Create Project application.

This module contains various resources used throughout the GUI:
- Icons for buttons, dialogs, and UI elements
- Style constants and themes
- Resource loading utilities with fallback support
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .icons import IconManager, get_icon
    from .styles import StyleManager, get_style_sheet

__all__ = ["IconManager", "get_icon", "StyleManager", "get_style_sheet"]
