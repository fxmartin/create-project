# ABOUTME: Core configuration manager for loading, saving, and managing settings
# ABOUTME: Provides thread-safe configuration access with JSON and environment variable support

"""
Configuration Manager

Centralized configuration management system that handles:
- Loading configuration from JSON files and environment variables
- Thread-safe configuration access and modification
- Configuration validation and error handling
- Graceful handling of missing or corrupted configuration files
- Environment variable precedence over JSON settings
"""

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .models import Config, create_default_config


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


class ConfigManager:
    """
    Thread-safe configuration manager for the Python Project Creator.

    Handles loading configuration from multiple sources with the following precedence:
    1. Environment variables (highest priority)
    2. settings.json file
    3. defaults.json file
    4. Built-in defaults (lowest priority)
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Optional path to configuration directory.
                        If None, uses the default config directory.
        """
        self._lock = threading.RLock()
        self._config: Optional[Config] = None

        # Set up configuration paths
        if config_path is None:
            # Default to the config directory in the package
            self._config_dir = Path(__file__).parent
        else:
            self._config_dir = Path(config_path)

        self._settings_file = self._config_dir / "settings.json"
        self._defaults_file = self._config_dir / "defaults.json"
        self._schema_file = self._config_dir / "settings.schema.json"

        # Track if configuration has been loaded
        self._loaded = False

    @property
    def config_directory(self) -> Path:
        """Get the configuration directory path."""
        return self._config_dir

    @property
    def is_loaded(self) -> bool:
        """Check if configuration has been loaded."""
        with self._lock:
            return self._loaded

    def load_config(self) -> Config:
        """
        Load configuration from all sources with proper precedence.

        Returns:
            Validated Config instance

        Raises:
            ConfigurationError: If configuration loading fails
        """
        with self._lock:
            try:
                # Start with built-in defaults
                config_dict = self._get_default_config_dict()

                # Override with defaults.json if it exists
                if self._defaults_file.exists():
                    defaults_dict = self._load_json_file(self._defaults_file)
                    config_dict = self._merge_config_dicts(config_dict, defaults_dict)

                # Override with settings.json if it exists
                if self._settings_file.exists():
                    settings_dict = self._load_json_file(self._settings_file)
                    config_dict = self._merge_config_dicts(config_dict, settings_dict)

                # Override with environment variables (highest priority)
                env_dict = self._load_environment_variables()
                config_dict = self._merge_config_dicts(config_dict, env_dict)

                # Validate and create Config instance
                self._config = Config(**config_dict)
                self._loaded = True

                return self._config

            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load configuration: {str(e)}"
                ) from e

    def save_config(self, config: Optional[Config] = None) -> bool:
        """
        Save configuration to settings.json file.

        Args:
            config: Config instance to save. If None, saves current loaded config.

        Returns:
            True if save was successful, False otherwise

        Raises:
            ConfigurationError: If no configuration is available to save
        """
        with self._lock:
            try:
                config_to_save = config or self._config
                if config_to_save is None:
                    raise ConfigurationError("No configuration to save")

                # Ensure config directory exists
                self._config_dir.mkdir(parents=True, exist_ok=True)

                # Convert to dictionary and save as JSON
                config_dict = config_to_save.model_dump()

                # Write to temporary file first, then rename for atomic operation
                temp_file = self._settings_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)

                # Atomic rename
                temp_file.replace(self._settings_file)

                # Update internal config if we saved the current one
                if config is None:
                    self._config = config_to_save

                return True

            except ConfigurationError:
                # Re-raise ConfigurationError without catching it
                raise
            except Exception as e:
                # Clean up temporary file if it exists
                temp_file = self._settings_file.with_suffix(".tmp")
                if temp_file.exists():
                    temp_file.unlink()

                # Log error (would use logger from section 1.3 here)
                print(f"Error saving configuration: {e}")
                return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration setting using dot notation.

        Args:
            key: Setting key in dot notation (e.g., 'ui.theme', 'ollama.api_url')
            default: Default value if setting is not found

        Returns:
            Setting value or default
        """
        with self._lock:
            if self._config is None:
                self.load_config()

            return self._config.get_nested_value(key, default)

    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a configuration setting using dot notation.

        Args:
            key: Setting key in dot notation (e.g., 'ui.theme', 'ollama.api_url')
            value: Value to set

        Returns:
            True if setting was successful, False otherwise
        """
        with self._lock:
            try:
                if self._config is None:
                    self.load_config()

                self._config.set_nested_value(key, value)
                return True

            except Exception as e:
                print(f"Error setting configuration value '{key}': {e}")
                return False

    def get_config(self) -> Config:
        """
        Get the current configuration instance.

        Returns:
            Current Config instance
        """
        with self._lock:
            if self._config is None:
                self.load_config()
            return self._config

    @contextmanager
    def temporary_setting(self, key: str, value: Any):
        """
        Context manager for temporarily changing a setting.

        Args:
            key: Setting key in dot notation
            value: Temporary value
        """
        old_value = self.get_setting(key)
        self.set_setting(key, value)
        try:
            yield
        finally:
            self.set_setting(key, old_value)

    def reload_config(self) -> Config:
        """
        Reload configuration from all sources.

        Returns:
            Reloaded Config instance
        """
        with self._lock:
            self._config = None
            self._loaded = False
            return self.load_config()

    def reset_to_defaults(self) -> Config:
        """
        Reset configuration to built-in defaults.

        Returns:
            Default Config instance
        """
        with self._lock:
            self._config = create_default_config()
            self._loaded = True
            return self._config

    def _get_default_config_dict(self) -> Dict[str, Any]:
        """Get the built-in default configuration as a dictionary."""
        return create_default_config().model_dump()

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load and parse a JSON configuration file.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON as dictionary

        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in {file_path}: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Cannot read {file_path}: {e}") from e

    def _load_environment_variables(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Returns:
            Configuration dictionary from environment variables
        """
        env_config = {}

        # Mapping of environment variable names to config paths
        env_mappings = {
            "APP_DEBUG": ("app", "debug"),
            "APP_DATA_DIR": ("app", "data_dir"),
            "UI_THEME": ("ui", "theme"),
            "UI_WINDOW_WIDTH": ("ui", "window_size", 0),
            "UI_WINDOW_HEIGHT": ("ui", "window_size", 1),
            "UI_REMEMBER_WINDOW_STATE": ("ui", "remember_window_state"),
            "TEMPLATES_BUILTIN_PATH": ("templates", "builtin_path"),
            "TEMPLATES_CUSTOM_PATH": ("templates", "custom_path"),
            "TEMPLATES_AUTO_UPDATE": ("templates", "auto_update"),
            "OLLAMA_API_URL": ("ollama", "api_url"),
            "OLLAMA_TIMEOUT": ("ollama", "timeout"),
            "OLLAMA_PREFERRED_MODEL": ("ollama", "preferred_model"),
            "OLLAMA_ENABLE_CACHE": ("ollama", "enable_cache"),
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FILE_ENABLED": ("logging", "file_enabled"),
            "LOG_CONSOLE_ENABLED": ("logging", "console_enabled"),
            "LOG_MAX_FILES": ("logging", "max_files"),
            # AI configuration environment variables
            "APP_AI_ENABLED": ("ai", "enabled"),
            "APP_AI_OLLAMA_URL": ("ai", "ollama_url"),
            "APP_AI_OLLAMA_TIMEOUT": ("ai", "ollama_timeout"),
            "APP_AI_CACHE_ENABLED": ("ai", "cache_enabled"),
            "APP_AI_CACHE_TTL_HOURS": ("ai", "cache_ttl_hours"),
            "APP_AI_MAX_CACHE_ENTRIES": ("ai", "max_cache_entries"),
            "APP_AI_PREFERRED_MODELS": ("ai", "preferred_models"),
            "APP_AI_CONTEXT_COLLECTION_ENABLED": ("ai", "context_collection_enabled"),
            "APP_AI_MAX_CONTEXT_SIZE_KB": ("ai", "max_context_size_kb"),
            "APP_AI_ENABLE_AI_ASSISTANCE": ("ai", "enable_ai_assistance"),
            "APP_AI_RESPONSE_QUALITY_CHECK": ("ai", "response_quality_check"),
            "APP_AI_MAX_RESPONSE_TOKENS": ("ai", "max_response_tokens"),
            "APP_AI_TEMPERATURE": ("ai", "temperature"),
            "APP_AI_TOP_P": ("ai", "top_p"),
            "APP_AI_STREAM_RESPONSES": ("ai", "stream_responses"),
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Convert string values to appropriate types
                converted_value = self._convert_env_value(env_value, config_path)

                # Set the value in the nested dictionary
                self._set_nested_dict_value(env_config, config_path, converted_value)

        return env_config

    def _convert_env_value(self, value: str, config_path: tuple) -> Any:
        """
        Convert environment variable string value to appropriate type.

        Args:
            value: String value from environment variable
            config_path: Tuple representing the configuration path

        Returns:
            Converted value
        """
        # Boolean values
        if any(
            path_part
            in [
                "debug",
                "remember_window_state",
                "auto_update",
                "enable_cache",
                "file_enabled",
                "console_enabled",
                "enabled",  # AI enabled
                "cache_enabled",  # AI cache
                "context_collection_enabled",  # AI context
                "enable_ai_assistance",  # AI assistance
                "response_quality_check",  # AI quality check
                "stream_responses",  # AI streaming
            ]
            for path_part in config_path
        ):
            return value.lower() in ("true", "1", "yes", "on")

        # Integer values
        if any(
            path_part in [
                "timeout", 
                "max_files",
                "ollama_timeout",  # AI timeout
                "cache_ttl_hours",  # AI cache TTL
                "max_cache_entries",  # AI cache size
                "max_context_size_kb",  # AI context size
                "max_response_tokens",  # AI response tokens
            ] 
            for path_part in config_path
        ) or (len(config_path) > 2 and config_path[1] == "window_size"):
            try:
                return int(value)
            except ValueError:
                return value  # Return as string if conversion fails

        # Float values
        if any(
            path_part in ["temperature", "top_p"]
            for path_part in config_path
        ):
            try:
                return float(value)
            except ValueError:
                return value  # Return as string if conversion fails
        
        # List values (comma-separated)
        if any(
            path_part in ["preferred_models"]
            for path_part in config_path
        ):
            return [v.strip() for v in value.split(",") if v.strip()]
        
        # Handle empty string for optional fields
        if not value.strip() and any(
            path_part in ["preferred_model"] for path_part in config_path
        ):
            return None

        # Return as string for all other values
        return value

    def _set_nested_dict_value(
        self, dictionary: Dict[str, Any], path: tuple, value: Any
    ) -> None:
        """
        Set a value in a nested dictionary using a path tuple.

        Args:
            dictionary: Target dictionary
            path: Tuple representing the nested path
            value: Value to set
        """
        current = dictionary

        # Special handling for window_size array
        if len(path) == 3 and path[1] == "window_size" and isinstance(path[2], int):
            # Ensure ui section exists
            if "ui" not in current:
                current["ui"] = {}
            # Ensure window_size list exists
            if "window_size" not in current["ui"]:
                current["ui"]["window_size"] = [800, 600]  # Default size
            # Ensure list is large enough
            while len(current["ui"]["window_size"]) <= path[2]:
                current["ui"]["window_size"].append(600)
            # Set the value
            current["ui"]["window_size"][path[2]] = value
            return

        # Navigate to the parent of the target key
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        final_key = path[-1]
        current[final_key] = value

    def _merge_config_dicts(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_config_dicts(result[key], value)
            else:
                result[key] = value

        return result


# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None
_global_lock = threading.Lock()


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.

    Returns:
        Global ConfigManager instance
    """
    global _global_config_manager

    if _global_config_manager is None:
        with _global_lock:
            if _global_config_manager is None:
                _global_config_manager = ConfigManager()

    return _global_config_manager


def get_config() -> Config:
    """
    Get the current configuration.

    Returns:
        Current Config instance
    """
    return get_config_manager().get_config()


def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a configuration setting using dot notation.

    Args:
        key: Setting key in dot notation
        default: Default value if setting is not found

    Returns:
        Setting value or default
    """
    return get_config_manager().get_setting(key, default)


def set_setting(key: str, value: Any) -> bool:
    """
    Set a configuration setting using dot notation.

    Args:
        key: Setting key in dot notation
        value: Value to set

    Returns:
        True if setting was successful, False otherwise
    """
    return get_config_manager().set_setting(key, value)
