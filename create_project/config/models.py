# ABOUTME: Configuration data models using Pydantic for validation
# ABOUTME: Defines the structure and validation rules for all configuration sections

"""
Configuration Data Models

Pydantic models for configuration validation and type safety.
All configuration sections are defined here with proper validation rules,
default values, and type hints.
"""

import os
from pathlib import Path
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class AppConfig(BaseModel):
    """Application-level configuration settings."""

    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    data_dir: str = Field(default="./data", description="Application data directory")

    @field_validator("data_dir")
    @classmethod
    def validate_data_dir(cls, v):
        """Ensure data directory path is valid and expandable."""
        return os.path.expanduser(v)


class UIConfig(BaseModel):
    """User interface configuration settings."""

    theme: Literal["system", "light", "dark"] = Field(
        default="system", description="UI theme preference"
    )
    window_size: List[int] = Field(
        default=[800, 600], description="Window size [width, height]"
    )
    remember_window_state: bool = Field(
        default=True, description="Remember window position and size"
    )

    @field_validator("window_size")
    @classmethod
    def validate_window_size(cls, v):
        """Validate window size dimensions."""
        if len(v) != 2:
            raise ValueError(
                "Window size must contain exactly 2 values [width, height]"
            )
        if any(dim < 400 for dim in v):
            raise ValueError("Window dimensions must be at least 400 pixels")
        if any(dim > 4000 for dim in v):
            raise ValueError("Window dimensions must not exceed 4000 pixels")
        return v


class TemplateConfig(BaseModel):
    """Template system configuration settings."""

    builtin_path: str = Field(
        default="./templates", description="Path to built-in templates"
    )
    custom_path: str = Field(
        default="~/.project-creator/templates",
        description="Path to custom user templates",
    )
    auto_update: bool = Field(
        default=False, description="Automatically update templates"
    )

    # Template Schema Settings
    validate_on_load: bool = Field(
        default=True, description="Validate templates when loading"
    )
    allow_custom_validators: bool = Field(
        default=False, description="Allow custom Python validators in templates"
    )
    max_template_size_mb: int = Field(
        default=10, ge=1, le=100, description="Maximum template size in MB"
    )
    enable_template_cache: bool = Field(
        default=True, description="Cache loaded and validated templates"
    )
    template_file_extensions: List[str] = Field(
        default_factory=lambda: [".yaml", ".yml"],
        description="Allowed template file extensions",
    )

    # Security Settings
    allow_external_commands: bool = Field(
        default=False, description="Allow templates to run external commands"
    )
    command_whitelist: List[str] = Field(
        default_factory=lambda: ["git", "npm", "pip", "python", "uv"],
        description="Whitelisted commands for template actions",
    )

    # Variable Settings
    variable_name_pattern: str = Field(
        default=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="Regex pattern for variable names",
    )
    max_variables_per_template: int = Field(
        default=50, ge=1, le=200, description="Maximum variables per template"
    )

    @field_validator("builtin_path", "custom_path")
    @classmethod
    def validate_template_paths(cls, v):
        """Expand user paths and validate template directories."""
        return os.path.expanduser(v)

    @field_validator("template_file_extensions")
    @classmethod
    def validate_extensions(cls, v):
        """Ensure extensions start with a dot."""
        return [ext if ext.startswith(".") else f".{ext}" for ext in v]

    @field_validator("variable_name_pattern")
    @classmethod
    def validate_regex_pattern(cls, v):
        """Validate the regex pattern is valid."""
        import re
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        return v


class OllamaConfig(BaseModel):
    """Ollama AI integration configuration settings."""

    api_url: Union[HttpUrl, str] = Field(
        default="http://localhost:11434", description="Ollama API endpoint URL"
    )
    timeout: int = Field(
        default=30, ge=1, le=300, description="Request timeout in seconds"
    )
    preferred_model: Optional[str] = Field(
        default=None, description="Preferred Ollama model name"
    )
    enable_cache: bool = Field(default=True, description="Enable response caching")

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v):
        """Ensure API URL is properly formatted."""
        if isinstance(v, str) and not v.startswith(("http://", "https://")):
            raise ValueError("API URL must start with http:// or https://")
        return str(v)


class LoggingConfig(BaseModel):
    """Logging system configuration settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    file_enabled: bool = Field(default=True, description="Enable file logging")
    console_enabled: bool = Field(default=True, description="Enable console logging")
    max_files: int = Field(
        default=5, ge=1, le=100, description="Maximum number of log files to retain"
    )


class Config(BaseModel):
    """Root configuration model containing all configuration sections."""

    app: AppConfig = Field(default_factory=AppConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = {
        "extra": "forbid",  # Forbid extra fields not defined in the model
        "validate_assignment": True,  # Validate on field assignment
        "use_enum_values": True,  # Use enum values instead of enum objects
    }

    @model_validator(mode="after")
    def validate_config_consistency(self):
        """Validate cross-section configuration consistency."""
        # Ensure data directory and template paths don't conflict
        data_dir = Path(self.app.data_dir).resolve()
        builtin_path = Path(self.templates.builtin_path).resolve()

        # Warn if builtin templates are inside data directory
        # (This is allowed but might indicate misconfiguration)
        if data_dir in builtin_path.parents:
            # This is just a validation note, not an error
            pass

        return self

    def get_nested_value(self, key_path: str, default=None):
        """
        Get a nested configuration value using dot notation.

        Args:
            key_path: Dot-separated path like 'ui.theme' or 'ollama.api_url'
            default: Default value if key is not found

        Returns:
            The configuration value or default
        """
        keys = key_path.split(".")
        current = self.model_dump()

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def set_nested_value(self, key_path: str, value):
        """
        Set a nested configuration value using dot notation.

        Args:
            key_path: Dot-separated path like 'ui.theme' or 'ollama.api_url'
            value: Value to set
        """
        keys = key_path.split(".")
        if len(keys) < 2:
            raise ValueError("Key path must contain at least one dot (section.key)")

        section_name = keys[0]
        if not hasattr(self, section_name):
            raise ValueError(f"Unknown configuration section: {section_name}")

        section = getattr(self, section_name)

        # Navigate to the parent of the target field
        current = section
        for key in keys[1:-1]:
            if hasattr(current, key):
                current = getattr(current, key)
            else:
                raise ValueError(f"Invalid key path: {key_path}")

        # Set the final value
        final_key = keys[-1]
        if hasattr(current, final_key):
            setattr(current, final_key, value)
        else:
            raise ValueError(f"Invalid key path: {key_path}")


# Utility function for creating default configurations
def create_default_config() -> Config:
    """Create a configuration instance with all default values."""
    return Config()


# Utility function for validating configuration dictionaries
def validate_config_dict(config_dict: dict) -> Config:
    """
    Validate a configuration dictionary and return a Config instance.

    Args:
        config_dict: Dictionary containing configuration data

    Returns:
        Validated Config instance

    Raises:
        ValidationError: If configuration is invalid
    """
    return Config(**config_dict)
