# ABOUTME: Template variable schema definition using Pydantic models
# ABOUTME: Provides variable types, validation, and conditional logic for templates

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, ValidationInfo


class VariableType(str, Enum):
    """Supported variable types for templates."""

    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    CHOICE = "choice"
    MULTICHOICE = "multichoice"
    LIST = "list"
    EMAIL = "email"
    URL = "url"
    PATH = "path"


class ChoiceItem(BaseModel):
    """Choice item for choice and multichoice variables."""

    value: str = Field(..., description="Choice value")

    label: Optional[str] = Field(
        None, description="Human-readable label for the choice"
    )

    description: Optional[str] = Field(
        None, description="Detailed description of the choice"
    )

    def get_display_label(self) -> str:
        """Get display label or fallback to value."""
        return self.label or self.value


class ValidationRule(BaseModel):
    """Validation rule for template variables."""

    rule_type: str = Field(
        ...,
        description="Type of validation rule (pattern, min_length, max_length, etc.)",
    )

    value: Any = Field(..., description="Value for the validation rule")

    message: Optional[str] = Field(
        None, description="Custom error message for validation failure"
    )

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        """Validate rule type is supported."""
        valid_types = {
            "pattern",
            "min_length",
            "max_length",
            "min_value",
            "max_value",
            "min_items",
            "max_items",
            "required",
            "format",
            "custom",
        }
        if v not in valid_types:
            raise ValueError(f"Invalid rule type '{v}'. Must be one of: {valid_types}")
        return v


class ConditionalLogic(BaseModel):
    """Conditional logic for showing/hiding variables."""

    variable: str = Field(..., description="Variable name to check")

    operator: str = Field(
        ..., description="Comparison operator (==, !=, in, not_in, contains, etc.)"
    )

    value: Any = Field(..., description="Value to compare against")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """Validate operator is supported."""
        valid_operators = {
            "==",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
            "in",
            "not_in",
            "contains",
            "not_contains",
            "startswith",
            "endswith",
            "is_empty",
            "is_not_empty",
            "matches",
            "not_matches",
        }
        if v not in valid_operators:
            raise ValueError(
                f"Invalid operator '{v}'. Must be one of: {valid_operators}"
            )
        return v


class TemplateVariable(BaseModel):
    """Template variable definition with type, validation, and conditional logic."""

    name: str = Field(
        ...,
        description="Variable name (must be valid identifier)",
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$",
    )

    type: VariableType = Field(..., description="Variable type")

    description: str = Field(
        ...,
        description="Human-readable description of the variable",
        min_length=1,
        max_length=200,
    )

    default: Optional[Any] = Field(None, description="Default value for the variable")

    required: bool = Field(default=True, description="Whether the variable is required")

    prompt: Optional[str] = Field(None, description="Custom prompt text for user input")

    help_text: Optional[str] = Field(
        None, description="Additional help text for the variable"
    )

    choices: Optional[List[ChoiceItem]] = Field(
        None, description="Available choices for choice/multichoice variables"
    )

    validation_rules: List[ValidationRule] = Field(
        default_factory=list, description="Validation rules for the variable"
    )

    show_if: Optional[List[ConditionalLogic]] = Field(
        None, description="Conditions for showing this variable"
    )

    hide_if: Optional[List[ConditionalLogic]] = Field(
        None, description="Conditions for hiding this variable"
    )

    filters: List[str] = Field(
        default_factory=list,
        description="Template filters to apply (snake_case, kebab_case, etc.)",
    )

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, v: Optional[List[str]], info: ValidationInfo) -> Optional[List[str]]:
        """Validate choices are provided for choice/multichoice variables."""
        if info.data and "type" in info.data:
            var_type = info.data["type"]
            if var_type in [VariableType.CHOICE, VariableType.MULTICHOICE]:
                if not v or len(v) == 0:
                    raise ValueError(
                        f"Choices must be provided for {var_type} variables"
                    )
                if len(v) < 2:
                    raise ValueError(
                        f"At least 2 choices required for {var_type} variables"
                    )
        return v

    @field_validator("default")
    @classmethod
    def validate_default_value(cls, v: Any, info: ValidationInfo) -> Any:
        """Validate default value matches variable type."""
        if v is None:
            return v

        if not info.data or "type" not in info.data:
            return v

        var_type = info.data["type"]

        # Type-specific validation
        if var_type == VariableType.BOOLEAN:
            if not isinstance(v, bool):
                raise ValueError("Default value for boolean variable must be boolean")
        elif var_type == VariableType.INTEGER:
            if not isinstance(v, int):
                raise ValueError("Default value for integer variable must be integer")
        elif var_type == VariableType.FLOAT:
            if not isinstance(v, (int, float)):
                raise ValueError("Default value for float variable must be number")
        elif var_type == VariableType.LIST:
            if not isinstance(v, list):
                raise ValueError("Default value for list variable must be list")
        elif var_type == VariableType.EMAIL:
            if not isinstance(v, str):
                raise ValueError("Default value for email variable must be string")
            # Basic email validation
            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
                raise ValueError("Default value must be valid email address")
        elif var_type == VariableType.URL:
            if not isinstance(v, str):
                raise ValueError("Default value for URL variable must be string")
            # Basic URL validation
            if not re.match(r"^https?://", v):
                raise ValueError("Default value must be valid URL")
        elif var_type == VariableType.PATH:
            if not isinstance(v, str):
                raise ValueError("Default value for path variable must be string")
        elif var_type in [VariableType.CHOICE, VariableType.MULTICHOICE]:
            # Will be validated against choices in a separate validator
            pass
        else:  # STRING and others
            if not isinstance(v, str):
                raise ValueError(
                    f"Default value for {var_type} variable must be string"
                )

        return v

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: List[str]) -> List[str]:
        """Validate template filters are supported."""
        supported_filters = {
            "snake_case",
            "kebab_case",
            "camel_case",
            "pascal_case",
            "upper",
            "lower",
            "title",
            "capitalize",
            "strip",
            "slugify",
            "sanitize",
            "replace_spaces",
            "normalize_path",
        }

        for filter_name in v:
            if filter_name not in supported_filters:
                raise ValueError(
                    f"Unsupported filter '{filter_name}'. Supported: {supported_filters}"
                )

        return v

    def get_prompt_text(self) -> str:
        """Get prompt text for user input."""
        if self.prompt:
            return self.prompt

        # Generate default prompt based on variable type
        base_prompt = f"Enter {self.description.lower()}"

        if self.type == VariableType.BOOLEAN:
            return f"{base_prompt} (y/n)"
        elif self.type == VariableType.CHOICE:
            if self.choices:
                choices_str = ", ".join([c.get_display_label() for c in self.choices])
                return f"{base_prompt} ({choices_str})"
        elif self.type == VariableType.MULTICHOICE:
            if self.choices:
                choices_str = ", ".join([c.get_display_label() for c in self.choices])
                return f"{base_prompt} (multiple allowed: {choices_str})"

        return f"{base_prompt}:"

    def validate_value(self, value: Any) -> List[str]:
        """Validate a value against this variable's constraints."""
        errors = []

        # Check required
        if self.required and (value is None or value == ""):
            errors.append(f"Variable '{self.name}' is required")
            return errors

        # Skip validation if value is None and not required
        if value is None and not self.required:
            return errors

        # Type-specific validation
        if self.type == VariableType.STRING:
            if not isinstance(value, str):
                errors.append(f"Variable '{self.name}' must be string")
        elif self.type == VariableType.BOOLEAN:
            if not isinstance(value, bool):
                errors.append(f"Variable '{self.name}' must be boolean")
        elif self.type == VariableType.INTEGER:
            if not isinstance(value, int):
                errors.append(f"Variable '{self.name}' must be integer")
        elif self.type == VariableType.FLOAT:
            if not isinstance(value, (int, float)):
                errors.append(f"Variable '{self.name}' must be number")
        elif self.type == VariableType.LIST:
            if not isinstance(value, list):
                errors.append(f"Variable '{self.name}' must be list")
        elif self.type == VariableType.EMAIL:
            if not isinstance(value, str):
                errors.append(f"Variable '{self.name}' must be string")
            elif not re.match(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value
            ):
                errors.append(f"Variable '{self.name}' must be valid email address")
        elif self.type == VariableType.URL:
            if not isinstance(value, str):
                errors.append(f"Variable '{self.name}' must be string")
            elif not re.match(r"^https?://", value):
                errors.append(f"Variable '{self.name}' must be valid URL")
        elif self.type == VariableType.PATH:
            if not isinstance(value, str):
                errors.append(f"Variable '{self.name}' must be string")
        elif self.type == VariableType.CHOICE:
            if self.choices:
                valid_values = [c.value for c in self.choices]
                if value not in valid_values:
                    errors.append(
                        f"Variable '{self.name}' must be one of: {valid_values}"
                    )
        elif self.type == VariableType.MULTICHOICE:
            if not isinstance(value, list):
                errors.append(f"Variable '{self.name}' must be list")
            elif self.choices:
                valid_values = [c.value for c in self.choices]
                for item in value:
                    if item not in valid_values:
                        errors.append(
                            f"Invalid choice '{item}' for variable '{self.name}'. Must be one of: {valid_values}"
                        )

        # Apply validation rules
        for rule in self.validation_rules:
            rule_errors = self._apply_validation_rule(value, rule)
            errors.extend(rule_errors)

        return errors

    def _apply_validation_rule(self, value: Any, rule: ValidationRule) -> List[str]:
        """Apply a single validation rule to a value."""
        errors = []

        try:
            if rule.rule_type == "pattern":
                if isinstance(value, str) and not re.match(rule.value, value):
                    msg = (
                        rule.message
                        or f"Variable '{self.name}' must match pattern: {rule.value}"
                    )
                    errors.append(msg)
            elif rule.rule_type == "min_length":
                if hasattr(value, "__len__") and len(value) < rule.value:
                    msg = (
                        rule.message
                        or f"Variable '{self.name}' must be at least {rule.value} characters"
                    )
                    errors.append(msg)
            elif rule.rule_type == "max_length":
                if hasattr(value, "__len__") and len(value) > rule.value:
                    msg = (
                        rule.message
                        or f"Variable '{self.name}' must be at most {rule.value} characters"
                    )
                    errors.append(msg)
            elif rule.rule_type == "min_value":
                if isinstance(value, (int, float)) and value < rule.value:
                    msg = (
                        rule.message
                        or f"Variable '{self.name}' must be at least {rule.value}"
                    )
                    errors.append(msg)
            elif rule.rule_type == "max_value":
                if isinstance(value, (int, float)) and value > rule.value:
                    msg = (
                        rule.message
                        or f"Variable '{self.name}' must be at most {rule.value}"
                    )
                    errors.append(msg)
            elif rule.rule_type == "min_items":
                if isinstance(value, list) and len(value) < rule.value:
                    msg = (
                        rule.message
                        or f"Variable '{self.name}' must have at least {rule.value} items"
                    )
                    errors.append(msg)
            elif rule.rule_type == "max_items":
                if isinstance(value, list) and len(value) > rule.value:
                    msg = (
                        rule.message
                        or f"Variable '{self.name}' must have at most {rule.value} items"
                    )
                    errors.append(msg)
        except Exception as e:
            errors.append(
                f"Error applying validation rule '{rule.rule_type}': {str(e)}"
            )

        return errors

    def should_show(self, variable_values: Dict[str, Any]) -> bool:
        """Determine if this variable should be shown based on conditions."""
        # If no conditions, always show
        if not self.show_if and not self.hide_if:
            return True

        # Check show_if conditions (all must be true)
        if self.show_if:
            for condition in self.show_if:
                if not self._evaluate_condition(condition, variable_values):
                    return False

        # Check hide_if conditions (any true means hide)
        if self.hide_if:
            for condition in self.hide_if:
                if self._evaluate_condition(condition, variable_values):
                    return False

        return True

    def _evaluate_condition(
        self, condition: ConditionalLogic, variable_values: Dict[str, Any]
    ) -> bool:
        """Evaluate a single conditional logic statement."""
        if condition.variable not in variable_values:
            return False

        var_value = variable_values[condition.variable]
        condition_value = condition.value

        try:
            if condition.operator == "==":
                return var_value == condition_value
            elif condition.operator == "!=":
                return var_value != condition_value
            elif condition.operator == "<":
                return var_value < condition_value
            elif condition.operator == "<=":
                return var_value <= condition_value
            elif condition.operator == ">":
                return var_value > condition_value
            elif condition.operator == ">=":
                return var_value >= condition_value
            elif condition.operator == "in":
                return var_value in condition_value
            elif condition.operator == "not_in":
                return var_value not in condition_value
            elif condition.operator == "contains":
                return condition_value in var_value
            elif condition.operator == "not_contains":
                return condition_value not in var_value
            elif condition.operator == "startswith":
                return str(var_value).startswith(str(condition_value))
            elif condition.operator == "endswith":
                return str(var_value).endswith(str(condition_value))
            elif condition.operator == "is_empty":
                return not var_value or var_value == ""
            elif condition.operator == "is_not_empty":
                return var_value and var_value != ""
            elif condition.operator == "matches":
                return bool(re.match(str(condition_value), str(var_value)))
            elif condition.operator == "not_matches":
                return not bool(re.match(str(condition_value), str(var_value)))
        except Exception:
            return False

        return False

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
