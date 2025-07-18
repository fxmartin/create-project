# ABOUTME: Templates package initialization
# ABOUTME: Provides template system components for Python project creation

"""Templates package for project creation."""

from .validator import TemplateValidationError, TemplateValidator, validate_template

__all__ = [
    "TemplateValidator",
    "TemplateValidationError",
    "validate_template",
]
