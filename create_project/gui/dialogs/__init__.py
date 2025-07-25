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

from .ai_help import AIHelpDialog
from .error import ErrorDialog

# Import implemented components
from .settings import SettingsDialog

__all__ = ["SettingsDialog", "ErrorDialog", "AIHelpDialog"]
