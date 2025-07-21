# ABOUTME: Dialogs module containing modal dialogs for settings and error handling
# ABOUTME: Provides settings management, error display, and AI help dialogs

"""
Dialogs module for the Create Project application.

This module contains various dialog windows used throughout the application:
- Settings dialog for configuration management
- Error dialog with progressive disclosure
- AI help dialog for assistance suggestions
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .settings import SettingsDialog
    from .error import ErrorDialog
    from .ai_help import AIHelpDialog

__all__ = [
    "SettingsDialog",
    "ErrorDialog",
    "AIHelpDialog"
]