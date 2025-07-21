# ABOUTME: Templates package initialization
# ABOUTME: Provides template system components for Python project creation

"""Templates package for project creation."""

from .engine import (
    RenderingError,
    TemplateEngine,
    TemplateEngineError,
    TemplateLoadError,
    VariableResolutionError,
)
from .loader import TemplateLoader
from .renderers import DirectoryRenderer, FileRenderer, ProjectRenderer
from .validator import TemplateValidationError, TemplateValidator, validate_template

__all__ = [
    # Core engine
    "TemplateEngine",
    "TemplateEngineError",
    "TemplateLoadError",
    "VariableResolutionError",
    "RenderingError",
    # Template loading
    "TemplateLoader",
    # Rendering
    "ProjectRenderer",
    "FileRenderer",
    "DirectoryRenderer",
    # Validation
    "TemplateValidator",
    "TemplateValidationError",
    "validate_template",
]
