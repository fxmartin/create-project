# ABOUTME: Core template engine for processing YAML templates with Jinja2
# ABOUTME: Manages template loading, variable resolution, and project structure generation

"""
Template Engine

The core engine responsible for processing YAML templates and generating
project structures. Integrates with the existing template schema system
and provides Jinja2-based templating with variable substitution.
"""

import threading
from pathlib import Path
from typing import Any, Dict, Optional, Set, Union

import jinja2
import yaml
from jinja2 import Environment, FileSystemLoader, meta
from pydantic import ValidationError

from ..config.config_manager import ConfigManager
from ..utils.logger import get_logger
from .schema.template import Template
from .schema.variables import TemplateVariable


class TemplateEngineError(Exception):
    """Base exception for template engine errors."""

    pass


class TemplateLoadError(TemplateEngineError):
    """Exception raised when template loading fails."""

    pass


class VariableResolutionError(TemplateEngineError):
    """Exception raised when variable resolution fails."""

    pass


class RenderingError(TemplateEngineError):
    """Exception raised when template rendering fails."""

    pass


class TemplateEngine:
    """Core template engine for processing templates and generating projects."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the template engine.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(__name__)

        # Template cache for performance
        self._template_cache: Dict[str, Template] = {}
        self._cache_lock = threading.RLock()

        # Jinja2 environment for rendering
        self._setup_jinja_environment()

        self.logger.info("Template engine initialized")

    def _setup_jinja_environment(self) -> None:
        """Set up Jinja2 environment with custom configuration."""
        # Get template directories from config
        template_dirs = self.config_manager.get_setting(
            "templates.directories", ["templates"]
        )

        # Create Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=False,  # We control the content
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=jinja2.StrictUndefined,  # Fail on undefined variables
        )

        # Add custom filters
        self._register_custom_filters()

        self.logger.debug(
            f"Jinja2 environment configured with directories: {template_dirs}"
        )

    def _register_custom_filters(self) -> None:
        """Register custom Jinja2 filters for template processing."""

        def slugify(value: str) -> str:
            """Convert string to slug format."""
            import re

            value = re.sub(r"[^\w\s-]", "", str(value)).strip().lower()
            return re.sub(r"[\s_-]+", "-", value)

        def snake_case(value: str) -> str:
            """Convert string to snake_case."""
            import re

            value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", str(value))
            value = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", value)
            return value.lower()

        def pascal_case(value: str) -> str:
            """Convert string to PascalCase."""
            return "".join(word.capitalize() for word in str(value).split("_"))

        def camel_case(value: str) -> str:
            """Convert string to camelCase."""
            pascal = pascal_case(value)
            return pascal[0].lower() + pascal[1:] if pascal else ""

        # Register filters
        self.jinja_env.filters.update(
            {
                "slugify": slugify,
                "snake_case": snake_case,
                "pascal_case": pascal_case,
                "camel_case": camel_case,
            }
        )

        self.logger.debug("Custom Jinja2 filters registered")

    def load_template(self, template_path: Union[str, Path]) -> Template:
        """Load a template from YAML file.

        Args:
            template_path: Path to the template YAML file

        Returns:
            Parsed Template object

        Raises:
            TemplateLoadError: If template loading or validation fails
        """
        template_path = Path(template_path)
        cache_key = str(template_path.absolute())

        # Check cache first
        with self._cache_lock:
            if cache_key in self._template_cache:
                self.logger.debug(f"Template loaded from cache: {template_path}")
                return self._template_cache[cache_key]

        # Load template from file
        try:
            if not template_path.exists():
                raise TemplateLoadError(f"Template file not found: {template_path}")

            self.logger.info(f"Loading template from: {template_path}")

            with open(template_path, encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

            if not template_data:
                raise TemplateLoadError(f"Empty template file: {template_path}")

            # Validate template data using Pydantic
            template = Template(**template_data)

            # Validate template completeness
            validation_errors = template.validate_template_complete()
            if validation_errors:
                error_msg = (
                    f"Template validation failed: {'; '.join(validation_errors)}"
                )
                raise TemplateLoadError(error_msg)

            # Cache the template
            with self._cache_lock:
                self._template_cache[cache_key] = template

            self.logger.info(f"Template loaded successfully: {template.metadata.name}")
            return template

        except yaml.YAMLError as e:
            raise TemplateLoadError(f"YAML parsing error in {template_path}: {e}")
        except ValidationError as e:
            raise TemplateLoadError(
                f"Template validation error in {template_path}: {e}"
            )
        except Exception as e:
            raise TemplateLoadError(
                f"Unexpected error loading template {template_path}: {e}"
            )

    def resolve_variables(
        self, template: Template, user_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve template variables with user-provided values.

        Args:
            template: Template object with variable definitions
            user_values: User-provided variable values

        Returns:
            Resolved variable values

        Raises:
            VariableResolutionError: If variable resolution fails
        """
        resolved_values = {}
        errors = []

        self.logger.debug(f"Resolving variables for template: {template.metadata.name}")

        # Process variables in order
        for variable in template.variables:
            try:
                # Get user value or default
                if variable.name in user_values:
                    value = user_values[variable.name]
                elif variable.default is not None:
                    value = variable.default
                elif variable.required:
                    errors.append(f"Required variable '{variable.name}' not provided")
                    continue
                else:
                    value = None

                # Validate the value
                if value is not None:
                    validation_errors = variable.validate_value(value)
                    if validation_errors:
                        errors.extend(
                            [
                                f"Variable '{variable.name}': {err}"
                                for err in validation_errors
                            ]
                        )
                        continue

                # Check conditional logic
                if not self._evaluate_variable_condition(variable, resolved_values):
                    self.logger.debug(
                        f"Variable '{variable.name}' skipped due to condition"
                    )
                    continue

                resolved_values[variable.name] = value
                self.logger.debug(f"Variable '{variable.name}' resolved to: {value}")

            except Exception as e:
                errors.append(f"Error resolving variable '{variable.name}': {e}")

        if errors:
            raise VariableResolutionError(
                f"Variable resolution failed: {'; '.join(errors)}"
            )

        self.logger.info(f"Resolved {len(resolved_values)} variables")
        return resolved_values

    def _evaluate_variable_condition(
        self, variable: TemplateVariable, resolved_values: Dict[str, Any]
    ) -> bool:
        """Evaluate if a variable should be included based on conditions.

        Args:
            variable: Template variable to evaluate
            resolved_values: Already resolved variable values

        Returns:
            True if variable should be included, False otherwise
        """
        if not variable.show_if and not variable.hide_if:
            return True

        try:
            # Evaluate show_if condition
            if variable.show_if:
                condition = variable.show_if
                result = self._evaluate_condition(condition, resolved_values)
                if not result:
                    return False

            # Evaluate hide_if condition
            if variable.hide_if:
                condition = variable.hide_if
                result = self._evaluate_condition(condition, resolved_values)
                if result:
                    return False

            return True

        except Exception as e:
            self.logger.warning(
                f"Error evaluating condition for variable '{variable.name}': {e}"
            )
            return True  # Default to including the variable

    def _evaluate_condition(
        self, condition: Dict[str, Any], values: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition expression.

        Args:
            condition: Condition dictionary with variable, operator, value
            values: Variable values to evaluate against

        Returns:
            Result of condition evaluation
        """
        variable = condition.get("variable")
        operator = condition.get("operator", "equals")
        expected_value = condition.get("value")

        if variable not in values:
            return False

        actual_value = values[variable]

        if operator == "equals":
            return actual_value == expected_value
        elif operator == "not_equals":
            return actual_value != expected_value
        elif operator == "in":
            return (
                actual_value in expected_value
                if isinstance(expected_value, list)
                else False
            )
        elif operator == "not_in":
            return (
                actual_value not in expected_value
                if isinstance(expected_value, list)
                else True
            )
        elif operator == "contains":
            return expected_value in str(actual_value)
        elif operator == "not_contains":
            return expected_value not in str(actual_value)
        else:
            self.logger.warning(f"Unknown operator: {operator}")
            return True

    def render_template_string(
        self, template_string: str, variables: Dict[str, Any]
    ) -> str:
        """Render a template string with variables.

        Args:
            template_string: Jinja2 template string
            variables: Variables for template rendering

        Returns:
            Rendered string

        Raises:
            RenderingError: If rendering fails
        """
        try:
            template = self.jinja_env.from_string(template_string)
            return template.render(**variables)
        except jinja2.TemplateError as e:
            raise RenderingError(f"Template rendering failed: {e}")
        except Exception as e:
            raise RenderingError(f"Unexpected rendering error: {e}")

    def get_template_variables(self, template_string: str) -> Set[str]:
        """Extract variable names from a template string.

        Args:
            template_string: Jinja2 template string

        Returns:
            Set of variable names used in the template
        """
        try:
            ast = self.jinja_env.parse(template_string)
            return meta.find_undeclared_variables(ast)
        except Exception as e:
            self.logger.warning(f"Error extracting variables from template: {e}")
            return set()

    def clear_cache(self) -> None:
        """Clear the template cache."""
        with self._cache_lock:
            self._template_cache.clear()
        self.logger.info("Template cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get template cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._cache_lock:
            return {
                "cached_templates": len(self._template_cache),
                "template_paths": list(self._template_cache.keys()),
            }
