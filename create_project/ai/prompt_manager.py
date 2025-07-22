# ABOUTME: Prompt template manager for AI assistance with dynamic loading and caching
# ABOUTME: Manages Jinja2 templates for different AI response scenarios with validation and custom template support

"""
Prompt template manager for AI assistance.

This module provides the PromptManager class which handles loading, validation,
and rendering of Jinja2 templates for AI prompts. It supports both built-in
templates and custom user templates with caching for performance.

The manager handles:
- Template discovery and loading from filesystem
- Template validation and syntax checking
- Dynamic template selection based on error type
- Variable injection with proper escaping
- Template caching for performance
- Support for custom user templates
"""

from pathlib import Path
from typing import Any, Dict, Optional, Set

from jinja2 import Environment, FileSystemLoader, Template, meta, select_autoescape
from jinja2 import TemplateError as Jinja2TemplateError
from structlog import get_logger

from .exceptions import AIError
from .types import PromptType

logger = get_logger(__name__)


class PromptManager:
    """Manages AI prompt templates with validation and caching.

    This class provides a centralized way to manage Jinja2 templates used for
    generating AI prompts. It supports loading templates from the filesystem,
    validating their syntax, caching compiled templates, and rendering them
    with context variables.

    Attributes:
        template_dir: Directory containing template files
        custom_template_dir: Optional directory for user custom templates
        cache_enabled: Whether to cache compiled templates
        _env: Jinja2 environment
        _template_cache: Cache of compiled templates
        _required_vars: Mapping of template types to required variables
    """

    # Default template directory relative to this file
    DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"

    # File extension for templates
    TEMPLATE_EXT = ".j2"

    # Required variables for each template type
    REQUIRED_VARS = {
        PromptType.ERROR_HELP: {"error_message", "error_type"},
        PromptType.SUGGESTIONS: {"project_type"},
        PromptType.EXPLANATION: {"topic"},
        PromptType.GENERIC_HELP: {"request"},
    }

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        custom_template_dir: Optional[Path] = None,
        cache_enabled: bool = True,
    ) -> None:
        """Initialize prompt manager.

        Args:
            template_dir: Directory containing built-in templates
            custom_template_dir: Directory for user custom templates
            cache_enabled: Whether to enable template caching
        """
        self.template_dir = template_dir or self.DEFAULT_TEMPLATE_DIR
        self.custom_template_dir = custom_template_dir
        self.cache_enabled = cache_enabled

        # Ensure template directory exists
        if not self.template_dir.exists():
            raise AIError(f"Template directory not found: {self.template_dir}")

        # Initialize Jinja2 environment
        search_paths = []
        if custom_template_dir and custom_template_dir.exists():
            # Custom templates take precedence
            search_paths.append(str(custom_template_dir))
        search_paths.append(str(self.template_dir))

        self._env = Environment(
            loader=FileSystemLoader(search_paths),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            cache_size=50 if cache_enabled else 0,
        )

        # Template cache
        self._template_cache: Dict[str, Template] = {}

        # Validate all built-in templates on initialization
        self._validate_builtin_templates()

        logger.info(
            "Prompt manager initialized",
            template_dir=str(self.template_dir),
            custom_dir=str(custom_template_dir) if custom_template_dir else None,
            cache_enabled=cache_enabled,
        )

    def _validate_builtin_templates(self) -> None:
        """Validate all built-in templates exist and have correct syntax."""
        for prompt_type in PromptType:
            template_name = f"{prompt_type.value}{self.TEMPLATE_EXT}"
            template_path = self.template_dir / template_name

            if not template_path.exists():
                raise AIError(f"Required template not found: {template_name}")

            try:
                # Try to load and compile template
                template = self._env.get_template(template_name)

                # Extract variables used in template
                source = self._env.loader.get_source(self._env, template_name)[0]
                ast = self._env.parse(source)
                variables = meta.find_undeclared_variables(ast)

                # Check required variables are referenced
                required = self.REQUIRED_VARS.get(prompt_type, set())
                missing = required - variables
                if missing:
                    logger.warning(
                        "Template missing required variables",
                        template=template_name,
                        missing=list(missing),
                        required=list(required),
                    )

                # Cache if enabled
                if self.cache_enabled:
                    self._template_cache[prompt_type.value] = template

                logger.debug(
                    "Template validated",
                    template=template_name,
                    variables=list(variables),
                )

            except Jinja2TemplateError as e:
                raise AIError(f"Template syntax error in {template_name}: {e}")

    def get_template(self, prompt_type: PromptType) -> Template:
        """Get a compiled template by type.

        Args:
            prompt_type: Type of prompt template to retrieve

        Returns:
            Compiled Jinja2 template

        Raises:
            AIError: If template not found or has syntax errors
        """
        # Check cache first
        if self.cache_enabled and prompt_type.value in self._template_cache:
            return self._template_cache[prompt_type.value]

        template_name = f"{prompt_type.value}{self.TEMPLATE_EXT}"

        try:
            template = self._env.get_template(template_name)

            # Cache if enabled
            if self.cache_enabled:
                self._template_cache[prompt_type.value] = template

            return template

        except Jinja2TemplateError as e:
            logger.error(
                "Failed to load template", template=template_name, error=str(e)
            )
            raise AIError(f"Template loading failed for {template_name}: {e}")

    def render_prompt(
        self,
        prompt_type: PromptType,
        context: Dict[str, Any],
        validate_required: bool = True,
    ) -> str:
        """Render a prompt template with given context.

        Args:
            prompt_type: Type of prompt to render
            context: Context variables for template
            validate_required: Whether to validate required variables

        Returns:
            Rendered prompt string

        Raises:
            AIError: If rendering fails or required variables missing
        """
        # Validate required variables if requested
        if validate_required:
            required = self.REQUIRED_VARS.get(prompt_type, set())
            missing = required - set(context.keys())
            if missing:
                raise AIError(
                    f"Missing required variables for {prompt_type.value}: {missing}"
                )

        try:
            template = self.get_template(prompt_type)
            rendered = template.render(**context)

            logger.debug(
                "Prompt rendered successfully",
                prompt_type=prompt_type.value,
                context_keys=list(context.keys()),
                rendered_length=len(rendered),
            )

            return rendered

        except Jinja2TemplateError as e:
            logger.error(
                "Template rendering failed", prompt_type=prompt_type.value, error=str(e)
            )
            raise AIError(f"Failed to render {prompt_type.value} template: {e}")

    def get_template_variables(self, prompt_type: PromptType) -> Set[str]:
        """Get all variables used in a template.

        Args:
            prompt_type: Type of prompt template

        Returns:
            Set of variable names used in template
        """
        template_name = f"{prompt_type.value}{self.TEMPLATE_EXT}"
        source = self._env.loader.get_source(self._env, template_name)[0]
        ast = self._env.parse(source)
        return meta.find_undeclared_variables(ast)

    def add_custom_template(
        self, name: str, content: str, required_vars: Optional[Set[str]] = None
    ) -> None:
        """Add a custom template programmatically.

        Args:
            name: Template name (without extension)
            content: Template content
            required_vars: Optional set of required variables

        Raises:
            AIError: If template has syntax errors
        """
        if not self.custom_template_dir:
            raise AIError("No custom template directory configured")

        # Ensure custom directory exists
        self.custom_template_dir.mkdir(parents=True, exist_ok=True)

        # Validate template syntax
        try:
            template = self._env.from_string(content)

            # Extract variables
            ast = self._env.parse(content)
            variables = meta.find_undeclared_variables(ast)

            # Check required variables if specified
            if required_vars:
                missing = required_vars - variables
                if missing:
                    logger.warning(
                        "Custom template missing required variables",
                        template=name,
                        missing=list(missing),
                    )

        except Jinja2TemplateError as e:
            raise AIError(f"Invalid template syntax: {e}")

        # Write template file
        template_path = self.custom_template_dir / f"{name}{self.TEMPLATE_EXT}"
        template_path.write_text(content, encoding="utf-8")

        # Clear template cache to pick up new template
        if self.cache_enabled:
            self._template_cache.pop(name, None)

        # Clear environment cache
        self._env.cache.clear()

        logger.info(
            "Custom template added",
            name=name,
            path=str(template_path),
            variables=list(variables),
        )

    def list_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all available templates with metadata.

        Returns:
            Dictionary mapping template names to their metadata
        """
        templates = {}

        # List built-in templates
        for prompt_type in PromptType:
            template_name = f"{prompt_type.value}{self.TEMPLATE_EXT}"
            template_path = self.template_dir / template_name

            if template_path.exists():
                try:
                    variables = self.get_template_variables(prompt_type)
                    templates[prompt_type.value] = {
                        "type": "builtin",
                        "path": str(template_path),
                        "variables": list(variables),
                        "required": list(self.REQUIRED_VARS.get(prompt_type, set())),
                    }
                except Exception as e:
                    logger.warning(
                        "Failed to get template info",
                        template=template_name,
                        error=str(e),
                    )

        # List custom templates if directory exists
        if self.custom_template_dir and self.custom_template_dir.exists():
            for template_file in self.custom_template_dir.glob(f"*{self.TEMPLATE_EXT}"):
                name = template_file.stem
                try:
                    # Load template to get variables
                    source = self._env.loader.get_source(self._env, template_file.name)[
                        0
                    ]
                    ast = self._env.parse(source)
                    variables = meta.find_undeclared_variables(ast)

                    templates[name] = {
                        "type": "custom",
                        "path": str(template_file),
                        "variables": list(variables),
                        "required": [],  # No enforced requirements for custom
                    }
                except Exception as e:
                    logger.warning(
                        "Failed to get custom template info",
                        template=template_file.name,
                        error=str(e),
                    )

        return templates

    def select_template_for_error(self, error: Exception) -> PromptType:
        """Select the best template type based on error type.

        Args:
            error: The exception that occurred

        Returns:
            Most appropriate prompt type for the error
        """
        # Map error types to prompt types
        error_type = type(error).__name__

        # Could be extended with more sophisticated mapping
        error_mappings = {
            "TemplateError": PromptType.ERROR_HELP,
            "ValidationError": PromptType.ERROR_HELP,
            "PathError": PromptType.ERROR_HELP,
            "GitError": PromptType.ERROR_HELP,
            "VirtualEnvError": PromptType.ERROR_HELP,
        }

        # Check if we have a specific mapping
        for error_pattern, prompt_type in error_mappings.items():
            if error_pattern in error_type:
                return prompt_type

        # Default to error help
        return PromptType.ERROR_HELP

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()
        self._env.cache.clear()
        logger.debug("Template cache cleared")
