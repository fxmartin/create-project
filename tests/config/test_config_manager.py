# ABOUTME: Unit tests for configuration manager
# ABOUTME: Tests configuration loading, saving, thread safety, and error handling

"""
Tests for Configuration Manager

Test suite for the ConfigManager class including:
- Configuration loading and saving
- Default value handling
- Thread safety
- Error handling for corrupt files
- Environment variable integration
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from create_project.config.config_manager import (
    ConfigManager,
    ConfigurationError,
    get_config,
    get_config_manager,
    get_setting,
    set_setting,
)
from create_project.config.models import Config


class TestConfigManager:
    """Test cases for ConfigManager class."""

    def test_initialization_default_path(self):
        """Test ConfigManager initialization with default path."""
        manager = ConfigManager()

        # Should use the package config directory by default
        assert manager.config_directory.name == "config"
        assert not manager.is_loaded

    def test_initialization_custom_path(self):
        """Test ConfigManager initialization with custom path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)

            assert manager.config_directory == Path(temp_dir)
            assert not manager.is_loaded

    def test_load_config_defaults_only(self):
        """Test loading configuration with only built-in defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            config = manager.load_config()

            assert isinstance(config, Config)
            assert manager.is_loaded
            assert config.app.version == "1.0.0"
            assert config.ui.theme == "system"

    def test_load_config_with_defaults_file(self):
        """Test loading configuration with defaults.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create defaults.json file
            defaults_file = Path(temp_dir) / "defaults.json"
            defaults_data = {
                "app": {"version": "2.0.0", "debug": True},
                "ui": {"theme": "dark"},
            }
            with open(defaults_file, "w") as f:
                json.dump(defaults_data, f)

            manager = ConfigManager(temp_dir)
            config = manager.load_config()

            assert config.app.version == "2.0.0"
            assert config.app.debug is True
            assert config.ui.theme == "dark"
            # Should still have other defaults
            assert config.ollama.timeout == 30

    def test_load_config_with_settings_file(self):
        """Test loading configuration with settings.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create settings.json file
            settings_file = Path(temp_dir) / "settings.json"
            settings_data = {
                "ui": {"theme": "light", "window_size": [1024, 768]},
                "ollama": {"timeout": 60},
            }
            with open(settings_file, "w") as f:
                json.dump(settings_data, f)

            manager = ConfigManager(temp_dir)
            config = manager.load_config()

            assert config.ui.theme == "light"
            assert config.ui.window_size == [1024, 768]
            assert config.ollama.timeout == 60
            # Should still have other defaults
            assert config.app.version == "1.0.0"

    def test_load_config_with_environment_variables(self):
        """Test loading configuration with environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set environment variables
            env_vars = {"APP_DEBUG": "true", "UI_THEME": "dark", "OLLAMA_TIMEOUT": "45"}

            with patch.dict(os.environ, env_vars):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()

                assert config.app.debug is True
                assert config.ui.theme == "dark"
                assert config.ollama.timeout == 45

    def test_load_config_precedence(self):
        """Test configuration loading precedence: env vars > settings > defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create defaults.json
            defaults_file = Path(temp_dir) / "defaults.json"
            defaults_data = {"ui": {"theme": "system"}}
            with open(defaults_file, "w") as f:
                json.dump(defaults_data, f)

            # Create settings.json
            settings_file = Path(temp_dir) / "settings.json"
            settings_data = {"ui": {"theme": "light"}}
            with open(settings_file, "w") as f:
                json.dump(settings_data, f)

            # Set environment variable (highest priority)
            with patch.dict(os.environ, {"UI_THEME": "dark"}):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()

                # Environment variable should win
                assert config.ui.theme == "dark"

    def test_load_config_invalid_json(self):
        """Test error handling for invalid JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid JSON file
            settings_file = Path(temp_dir) / "settings.json"
            with open(settings_file, "w") as f:
                f.write("{ invalid json }")

            manager = ConfigManager(temp_dir)

            with pytest.raises(ConfigurationError, match="Invalid JSON"):
                manager.load_config()

    def test_save_config_success(self):
        """Test successful configuration saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            config = manager.load_config()

            # Modify configuration
            config.ui.theme = "dark"
            config.ollama.timeout = 60

            # Save configuration
            success = manager.save_config(config)
            assert success

            # Verify file was created and contains correct data
            settings_file = Path(temp_dir) / "settings.json"
            assert settings_file.exists()

            with open(settings_file) as f:
                saved_data = json.load(f)

            assert saved_data["ui"]["theme"] == "dark"
            assert saved_data["ollama"]["timeout"] == 60

    def test_save_config_no_config(self):
        """Test error handling when saving without configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)

            with pytest.raises(ConfigurationError, match="No configuration to save"):
                manager.save_config()

    def test_get_setting_dot_notation(self):
        """Test getting settings using dot notation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()

            # Test getting existing settings
            assert manager.get_setting("ui.theme") == "system"
            assert manager.get_setting("ollama.timeout") == 30
            assert manager.get_setting("app.debug") is False

            # Test getting non-existent settings with default
            assert manager.get_setting("nonexistent.key", "default") == "default"
            assert manager.get_setting("ui.nonexistent") is None

    def test_set_setting_dot_notation(self):
        """Test setting values using dot notation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()

            # Test setting existing values
            success = manager.set_setting("ui.theme", "dark")
            assert success
            assert manager.get_setting("ui.theme") == "dark"

            success = manager.set_setting("ollama.timeout", 45)
            assert success
            assert manager.get_setting("ollama.timeout") == 45

    def test_get_config(self):
        """Test getting the configuration instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)

            # Should auto-load on first access
            config = manager.get_config()
            assert isinstance(config, Config)
            assert manager.is_loaded

    def test_temporary_setting_context_manager(self):
        """Test temporary setting context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()

            original_theme = manager.get_setting("ui.theme")

            # Use temporary setting
            with manager.temporary_setting("ui.theme", "dark"):
                assert manager.get_setting("ui.theme") == "dark"

            # Should revert to original value
            assert manager.get_setting("ui.theme") == original_theme

    def test_reload_config(self):
        """Test configuration reloading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)

            # Load initial configuration
            config1 = manager.load_config()
            assert config1.ui.theme == "system"

            # Create settings file
            settings_file = Path(temp_dir) / "settings.json"
            settings_data = {"ui": {"theme": "dark"}}
            with open(settings_file, "w") as f:
                json.dump(settings_data, f)

            # Reload configuration
            config2 = manager.reload_config()
            assert config2.ui.theme == "dark"
            assert manager.is_loaded

    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()

            # Modify some settings
            manager.set_setting("ui.theme", "dark")
            manager.set_setting("ollama.timeout", 60)

            # Reset to defaults
            config = manager.reset_to_defaults()

            assert config.ui.theme == "system"
            assert config.ollama.timeout == 30
            assert manager.is_loaded


class TestThreadSafety:
    """Test cases for thread safety of ConfigManager."""

    def test_concurrent_access(self):
        """Test concurrent access to configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            results = []
            errors = []

            def worker(worker_id):
                try:
                    # Load configuration
                    config = manager.get_config()
                    results.append(f"worker_{worker_id}_loaded")

                    # Get and set values
                    theme = manager.get_setting("ui.theme")
                    success = manager.set_setting("ui.theme", f"theme_{worker_id}")

                    results.append(f"worker_{worker_id}_get_{theme}")
                    results.append(f"worker_{worker_id}_set_{success}")

                except Exception as e:
                    errors.append(f"worker_{worker_id}_error_{e}")

            # Create multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)

            # Start all threads
            for thread in threads:
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join()

            # Check results
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) >= 15, f"Not all operations completed: {results}"

    def test_concurrent_load_save(self):
        """Test concurrent loading and saving operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            results = []
            errors = []

            def loader():
                try:
                    for i in range(10):
                        config = manager.load_config()
                        results.append(f"loaded_{i}")
                        time.sleep(0.001)  # Small delay
                except Exception as e:
                    errors.append(f"loader_error_{e}")

            def saver():
                try:
                    themes = ["system", "light", "dark"]
                    for i in range(10):
                        config = manager.get_config()
                        config.ui.theme = themes[i % 3]  # Cycle through valid themes
                        success = manager.save_config(config)
                        results.append(f"saved_{i}_{success}")
                        time.sleep(0.001)  # Small delay
                except Exception as e:
                    errors.append(f"saver_error_{e}")

            # Start threads
            loader_thread = threading.Thread(target=loader)
            saver_thread = threading.Thread(target=saver)

            loader_thread.start()
            saver_thread.start()

            loader_thread.join()
            saver_thread.join()

            # Check results
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) >= 20, f"Not all operations completed: {results}"


class TestGlobalFunctions:
    """Test cases for global configuration functions."""

    def test_get_config_manager(self):
        """Test getting the global config manager."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        # Should return the same instance (singleton)
        assert manager1 is manager2

    def test_get_config(self):
        """Test getting global configuration."""
        config = get_config()
        assert isinstance(config, Config)

    def test_get_setting_global(self):
        """Test getting setting through global function."""
        value = get_setting("ui.theme", "default")
        assert value in ["system", "light", "dark", "default"]

    def test_set_setting_global(self):
        """Test setting value through global function."""
        original = get_setting("ui.theme")

        success = set_setting("ui.theme", "dark")
        assert success
        assert get_setting("ui.theme") == "dark"

        # Restore original value
        set_setting("ui.theme", original)


class TestEnvironmentVariableConversion:
    """Test cases for environment variable type conversion."""

    def test_boolean_conversion(self):
        """Test conversion of boolean environment variables."""
        boolean_vars = {
            "APP_DEBUG": "true",
            "UI_REMEMBER_WINDOW_STATE": "false",
            "OLLAMA_ENABLE_CACHE": "1",
            "LOG_FILE_ENABLED": "0",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, boolean_vars):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()

                assert config.app.debug is True
                assert config.ui.remember_window_state is False
                assert config.ollama.enable_cache is True
                assert config.logging.file_enabled is False

    def test_integer_conversion(self):
        """Test conversion of integer environment variables."""
        integer_vars = {
            "OLLAMA_TIMEOUT": "45",
            "LOG_MAX_FILES": "10",
            "UI_WINDOW_WIDTH": "1024",
            "UI_WINDOW_HEIGHT": "768",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, integer_vars):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()

                assert config.ollama.timeout == 45
                assert config.logging.max_files == 10
                assert config.ui.window_size == [1024, 768]

    def test_string_conversion(self):
        """Test conversion of string environment variables."""
        string_vars = {
            "UI_THEME": "dark",
            "OLLAMA_API_URL": "http://custom.api.com",
            "LOG_LEVEL": "DEBUG",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, string_vars):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()

                assert config.ui.theme == "dark"
                assert config.ollama.api_url == "http://custom.api.com"
                assert config.logging.level == "DEBUG"

    def test_optional_field_conversion(self):
        """Test conversion of optional fields (None values)."""
        optional_vars = {
            "OLLAMA_PREFERRED_MODEL": "",  # Empty string should become None
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, optional_vars):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()

                assert config.ollama.preferred_model is None


class TestSaveConfigAdvanced:
    """Advanced test cases for save_config method."""

    def test_save_current_config_without_parameter(self):
        """Test saving current loaded config without passing config parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            config = manager.load_config()
            
            # Modify config
            config.ui.theme = "dark"
            
            # Save without passing config parameter (should save current loaded config)
            success = manager.save_config()
            assert success
            
            # Verify file was created and contains correct data
            settings_file = Path(temp_dir) / "settings.json"
            assert settings_file.exists()
            
            with open(settings_file) as f:
                saved_data = json.load(f)
            
            assert saved_data["ui"]["theme"] == "dark"

    def test_save_config_write_error(self):
        """Test save_config error handling when write fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            config = manager.load_config()
            
            # Make directory read-only to cause write error
            config_dir = Path(temp_dir)
            config_dir.chmod(0o555)  # Read and execute only
            
            try:
                success = manager.save_config(config)
                # Should return False due to permission error
                assert success is False
            finally:
                # Restore permissions for cleanup
                config_dir.chmod(0o755)

    def test_save_config_json_encoding_error(self):
        """Test save_config with JSON encoding issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            config = manager.load_config()
            
            # Mock json.dump to raise an exception during save
            with patch('json.dump', side_effect=ValueError("Encoding error")):
                success = manager.save_config(config)
                assert success is False


class TestAutoLoadingBehavior:
    """Test automatic configuration loading behavior."""

    def test_get_setting_auto_loads_config(self):
        """Test that get_setting auto-loads config when not loaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # Config should not be loaded initially
            assert not manager.is_loaded
            
            # Calling get_setting should auto-load
            value = manager.get_setting("ui.theme")
            assert value == "system"
            assert manager.is_loaded

    def test_set_setting_auto_loads_config(self):
        """Test that set_setting auto-loads config when not loaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # Config should not be loaded initially
            assert not manager.is_loaded
            
            # Calling set_setting should auto-load
            success = manager.set_setting("ui.theme", "dark")
            assert success
            assert manager.is_loaded
            assert manager.get_setting("ui.theme") == "dark"

    def test_set_setting_error_handling(self):
        """Test set_setting error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()
            
            # Use an invalid key that will cause set_nested_value to fail
            success = manager.set_setting("nonexistent.deeply.nested.invalid.key", "value")
            assert success is False


class TestFileReadingErrors:
    """Test error handling for file reading operations."""

    def test_load_config_file_permission_error(self):
        """Test configuration loading with file permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create settings file
            settings_file = Path(temp_dir) / "settings.json"
            settings_data = {"ui": {"theme": "dark"}}
            with open(settings_file, "w") as f:
                json.dump(settings_data, f)
            
            # Make file unreadable
            settings_file.chmod(0o000)
            
            manager = ConfigManager(temp_dir)
            
            try:
                with pytest.raises(ConfigurationError, match="Cannot read"):
                    manager.load_config()
            finally:
                # Restore permissions for cleanup
                settings_file.chmod(0o644)

    def test_load_config_file_not_found_error(self):
        """Test configuration loading with file not found (should not raise error)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # Should load defaults without error even if files don't exist
            config = manager.load_config()
            assert isinstance(config, Config)
            assert config.ui.theme == "system"


class TestEnvironmentVariableEdgeCases:
    """Test edge cases in environment variable conversion."""

    def test_float_conversion_ai_variables(self):
        """Test conversion of float AI environment variables."""
        float_vars = {
            "APP_AI_TEMPERATURE": "0.7",
            "APP_AI_TOP_P": "0.9",
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, float_vars):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()
                
                assert config.ai.temperature == 0.7
                assert config.ai.top_p == 0.9

    def test_float_conversion_invalid_value(self):
        """Test float conversion with invalid values falls back to string."""
        invalid_float_vars = {
            "APP_AI_TEMPERATURE": "invalid_float",
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, invalid_float_vars):
                manager = ConfigManager(temp_dir)
                # This should raise ConfigurationError due to Pydantic validation
                with pytest.raises(ConfigurationError, match="Failed to load configuration"):
                    manager.load_config()

    def test_integer_conversion_invalid_value(self):
        """Test integer conversion with invalid values falls back to string."""
        invalid_int_vars = {
            "OLLAMA_TIMEOUT": "not_a_number",
        }
        
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, invalid_int_vars):
                manager = ConfigManager(temp_dir)
                # This should raise ConfigurationError due to Pydantic validation
                with pytest.raises(ConfigurationError, match="Failed to load configuration"):
                    manager.load_config()

    def test_list_conversion_ai_models(self):
        """Test conversion of comma-separated list variables."""
        list_vars = {
            "APP_AI_PREFERRED_MODELS": "llama2,codellama,mistral",
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, list_vars):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()
                
                assert config.ai.preferred_models == ["llama2", "codellama", "mistral"]

    def test_window_size_array_expansion(self):
        """Test window size array expansion for out-of-bounds indices."""
        # Test setting window height when window_size array needs expansion
        window_vars = {
            "UI_WINDOW_HEIGHT": "1080",
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, window_vars):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()
                
                # Should expand array and set height
                assert len(config.ui.window_size) >= 2
                assert config.ui.window_size[1] == 1080

    def test_window_size_array_expansion_large_index(self):
        """Test window size array expansion for very large index (covers line 438)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # Manually create environment with large window size index
            env_config = {}
            # Simulate setting a very large index that requires array expansion
            manager._set_nested_dict_value(env_config, ("ui", "window_size", 5), 1200)
            
            # Verify array was expanded properly
            assert len(env_config["ui"]["window_size"]) >= 6
            assert env_config["ui"]["window_size"][5] == 1200


class TestComplexConfigurationScenarios:
    """Test complex configuration scenarios and edge cases."""

    def test_nested_config_merging_deep(self):
        """Test deep nested configuration merging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested defaults that respect the schema
            defaults_file = Path(temp_dir) / "defaults.json"
            defaults_data = {
                "ui": {
                    "theme": "light",
                    "window_size": [1024, 768]
                },
                "ollama": {
                    "api_url": "http://localhost:11434",
                    "timeout": 30
                }
            }
            with open(defaults_file, "w") as f:
                json.dump(defaults_data, f)
            
            # Create settings that partially override
            settings_file = Path(temp_dir) / "settings.json"
            settings_data = {
                "ui": {
                    "theme": "dark"  # Override only theme, keep window_size from defaults
                },
                "ollama": {
                    "timeout": 60  # Override only timeout, keep api_url from defaults
                }
            }
            with open(settings_file, "w") as f:
                json.dump(settings_data, f)
            
            manager = ConfigManager(temp_dir)
            config = manager.load_config()
            
            # Should preserve base URL but override timeout
            assert config.ollama.api_url == "http://localhost:11434"
            assert config.ollama.timeout == 60
            # Should preserve window_size from defaults but override theme
            assert config.ui.theme == "dark"
            assert config.ui.window_size == [1024, 768]

    def test_config_with_all_sources_precedence(self):
        """Test configuration precedence with all sources active."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create defaults with valid theme
            defaults_file = Path(temp_dir) / "defaults.json"
            defaults_data = {"ui": {"theme": "system"}}
            with open(defaults_file, "w") as f:
                json.dump(defaults_data, f)
            
            # Create settings with different valid theme
            settings_file = Path(temp_dir) / "settings.json"
            settings_data = {"ui": {"theme": "light"}}
            with open(settings_file, "w") as f:
                json.dump(settings_data, f)
            
            # Set environment variable with valid theme (should win)
            with patch.dict(os.environ, {"UI_THEME": "dark"}):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()
                
                # Environment variable should take precedence
                assert config.ui.theme == "dark"


if __name__ == "__main__":
    pytest.main([__file__])
