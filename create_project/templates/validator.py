# ABOUTME: Template schema validator for validating templates against the schema
# ABOUTME: Provides comprehensive validation with detailed error reporting and security checks

"""
Template Schema Validator

Provides comprehensive validation of template schemas with detailed error reporting,
security checks, and integration with the configuration system.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from pydantic import ValidationError

from ..config import get_config
from ..utils.logger import get_logger
from .schema import Template

logger = get_logger(__name__)


class TemplateValidationError(Exception):
    """Raised when template validation fails."""

    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.errors = errors or []


class TemplateValidator:
    """Validates templates against the schema with configuration integration."""

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the validator with configuration.

        Args:
            config: Optional configuration override (Config object or dict)
        """
        if config is None:
            config = get_config()
        self.config = config

        # Handle both Config objects and dicts
        if hasattr(config, "templates"):
            self.template_config = config.templates
        else:
            # For dict-based config
            self.template_config = config.get("templates", {})

        # Compile regex patterns
        self.variable_name_pattern = re.compile(
            self.template_config.variable_name_pattern
        )

        logger.debug("Initialized TemplateValidator", config=self.template_config)

    def validate_template_file(self, file_path: Union[str, Path]) -> Template:
        """
        Validate a template file and return the validated Template object.

        Args:
            file_path: Path to the template file

        Returns:
            Validated Template object

        Raises:
            TemplateValidationError: If validation fails
            FileNotFoundError: If template file doesn't exist
        """
        file_path = Path(file_path)

        # Check file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Template file not found: {file_path}")

        # Check file extension
        if file_path.suffix not in self.template_config.template_file_extensions:
            raise TemplateValidationError(
                f"Invalid template file extension: {file_path.suffix}. "
                f"Allowed extensions: {', '.join(self.template_config.template_file_extensions)}"
            )

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.template_config.max_template_size_mb:
            raise TemplateValidationError(
                f"Template file too large: {file_size_mb:.2f}MB. "
                f"Maximum allowed: {self.template_config.max_template_size_mb}MB"
            )

        logger.info(f"Validating template file: {file_path}")

        try:
            # Load YAML content
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise TemplateValidationError("Template must be a YAML dictionary")

            # Validate against schema
            return self.validate_template_data(data, source_path=str(file_path))

        except yaml.YAMLError as e:
            raise TemplateValidationError(f"Invalid YAML syntax: {e}")
        except Exception as e:
            logger.error(f"Error validating template file: {e}", exc_info=True)
            raise

    def validate_template_data(
        self, data: Dict[str, Any], source_path: Optional[str] = None
    ) -> Template:
        """
        Validate template data and return the validated Template object.

        Args:
            data: Template data dictionary
            source_path: Optional source file path for error reporting

        Returns:
            Validated Template object

        Raises:
            TemplateValidationError: If validation fails
        """
        try:
            # Create Template instance (Pydantic validation)
            template = Template(**data)

            # Additional custom validations
            self._validate_variables(template)
            self._validate_security(template)
            self._validate_references(template)

            logger.info(
                f"Successfully validated template: {template.metadata.name}",
                version=template.metadata.version,
                variables=len(template.variables),
                source=source_path,
            )

            return template

        except ValidationError as e:
            errors = []
            for error in e.errors():
                errors.append(
                    {
                        "field": ".".join(str(x) for x in error["loc"]),
                        "message": error["msg"],
                        "type": error["type"],
                    }
                )

            logger.error(
                "Template validation failed", errors=errors, source=source_path
            )

            raise TemplateValidationError(
                f"Template validation failed with {len(errors)} errors", errors=errors
            )

    def _validate_variables(self, template: Template) -> None:
        """
        Validate template variables against configuration rules.

        Args:
            template: Template to validate

        Raises:
            TemplateValidationError: If validation fails
        """
        # Check variable count
        if len(template.variables) > self.template_config.max_variables_per_template:
            raise TemplateValidationError(
                f"Too many variables: {len(template.variables)}. "
                f"Maximum allowed: {self.template_config.max_variables_per_template}"
            )

        # Validate variable names
        for var in template.variables:
            if not self.variable_name_pattern.match(var.name):
                raise TemplateValidationError(
                    f"Invalid variable name '{var.name}'. "
                    f"Must match pattern: {self.template_config.variable_name_pattern}"
                )

        # Check for duplicate variable names
        var_names = [var.name for var in template.variables]
        duplicates = [name for name in var_names if var_names.count(name) > 1]
        if duplicates:
            raise TemplateValidationError(
                f"Duplicate variable names found: {', '.join(set(duplicates))}"
            )

    def _validate_security(self, template: Template) -> None:
        """
        Validate security aspects of the template.

        Args:
            template: Template to validate

        Raises:
            TemplateValidationError: If security validation fails
        """
        # Check for custom validators if not allowed
        if not self.template_config.allow_custom_validators:
            for var in template.variables:
                if hasattr(var, "custom_validator") and var.custom_validator:
                    raise TemplateValidationError(
                        f"Custom validators not allowed. Variable '{var.name}' "
                        "has a custom validator."
                    )

        # Validate command actions
        if not self.template_config.allow_external_commands:
            # Check all action groups
            for hook_name in ["before_create", "after_create", "on_error"]:
                action_groups = getattr(template.hooks, hook_name, [])
                for group in action_groups:
                    for action in group.actions:
                        if action.type == "command":
                            # Check if command is whitelisted
                            cmd_parts = action.command.split()
                            if (
                                cmd_parts
                                and cmd_parts[0]
                                not in self.template_config.command_whitelist
                            ):
                                raise TemplateValidationError(
                                    f"Command '{cmd_parts[0]}' not in whitelist. "
                                    f"Allowed commands: {', '.join(self.template_config.command_whitelist)}"
                                )

    def _validate_references(self, template: Template) -> None:
        """
        Validate that all variable references in the template are valid.

        Args:
            template: Template to validate

        Raises:
            TemplateValidationError: If reference validation fails
        """
        # Get all variable names
        var_names = {var.name for var in template.variables}

        # Check conditional references
        for var in template.variables:
            if var.show_if:
                for condition in var.show_if:
                    ref_var = condition.variable
                    if ref_var not in var_names:
                        raise TemplateValidationError(
                            f"Variable '{var.name}' references unknown variable '{ref_var}' in show_if"
                        )

            if var.hide_if:
                for condition in var.hide_if:
                    ref_var = condition.variable
                    if ref_var not in var_names:
                        raise TemplateValidationError(
                            f"Variable '{var.name}' references unknown variable '{ref_var}' in hide_if"
                        )

    def validate_directory(
        self, directory: Union[str, Path], recursive: bool = True
    ) -> Tuple[List[Template], List[Dict[str, Any]]]:
        """
        Validate all templates in a directory.

        Args:
            directory: Directory to scan for templates
            recursive: Whether to scan subdirectories

        Returns:
            Tuple of (valid_templates, errors)
        """
        directory = Path(directory)
        valid_templates = []
        errors = []

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        # Find all template files
        pattern = "**/*" if recursive else "*"
        for ext in self.template_config.template_file_extensions:
            for file_path in directory.glob(f"{pattern}{ext}"):
                if file_path.is_file():
                    try:
                        template = self.validate_template_file(file_path)
                        valid_templates.append(template)
                    except Exception as e:
                        errors.append(
                            {
                                "file": str(file_path),
                                "error": str(e),
                                "type": type(e).__name__,
                            }
                        )

        logger.info(
            f"Validated directory: {directory}",
            valid_count=len(valid_templates),
            error_count=len(errors),
            recursive=recursive,
        )

        return valid_templates, errors


def validate_template(
    template_path: Union[str, Path], config: Optional[Dict[str, Any]] = None
) -> Template:
    """
    Convenience function to validate a single template file.

    Args:
        template_path: Path to template file
        config: Optional configuration override

    Returns:
        Validated Template object

    Raises:
        TemplateValidationError: If validation fails
    """
    validator = TemplateValidator(config)
    return validator.validate_template_file(template_path)
