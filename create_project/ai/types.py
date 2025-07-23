# ABOUTME: Common types and enumerations used across AI module
# ABOUTME: Provides shared definitions to avoid circular imports

"""
Common types and enumerations for AI module.

This module contains shared type definitions used across the AI module
to avoid circular import issues while maintaining type safety.
"""

from enum import Enum


class PromptType(Enum):
    """Types of AI prompts supported by the response generator."""

    ERROR_HELP = "error_help"
    SUGGESTIONS = "suggestions"
    EXPLANATION = "explanation"
    GENERIC_HELP = "generic_help"
