# ABOUTME: Templates package initialization
# ABOUTME: Provides template system components for Python project creation

"""Templates package for project creation."""

from .engine import TemplateEngine, TemplateEngineError, TemplateLoadError, VariableResolutionError, RenderingError
from .loader import TemplateLoader
from .renderers import ProjectRenderer, FileRenderer, DirectoryRenderer
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
