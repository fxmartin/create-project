# ABOUTME: Unit tests for configuration data models
# ABOUTME: Tests Pydantic model validation, defaults, and type conversion

"""
Tests for Configuration Data Models

Test suite for all Pydantic configuration models including:
- Validation of valid and invalid data
- Default value assignment
- Type conversion and validation errors
- Nested model relationships
"""

import pytest
from pydantic import ValidationError
from create_project.config.models import (
    AppConfig, UIConfig, TemplateConfig, OllamaConfig, LoggingConfig,
    Config, create_default_config, validate_config_dict
)


class TestAppConfig:
    """Test cases for AppConfig model."""
    
    def test_default_values(self):
        """Test that default values are properly assigned."""
        config = AppConfig()
        assert config.version == "1.0.0"
        assert config.debug is False
        assert config.data_dir == "./data"
    
    def test_valid_configuration(self):
        """Test creation with valid configuration data."""
        config = AppConfig(
            version="2.0.0",
            debug=True,
            data_dir="/custom/path"
        )
        assert config.version == "2.0.0"
        assert config.debug is True
        assert config.data_dir == "/custom/path"
    
    def test_data_dir_expansion(self):
        """Test that data directory paths are properly expanded."""
        config = AppConfig(data_dir="~/test")
        # Should expand tilde to home directory
        assert config.data_dir.startswith("/")
        assert "test" in config.data_dir
    
    def test_invalid_version_type(self):
        """Test validation error for invalid version type."""
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(version=123)
        assert "string_type" in str(exc_info.value)


class TestUIConfig:
    """Test cases for UIConfig model."""
    
    def test_default_values(self):
        """Test that default values are properly assigned."""
        config = UIConfig()
        assert config.theme == "system"
        assert config.window_size == [800, 600]
        assert config.remember_window_state is True
    
    def test_valid_theme_values(self):
        """Test that valid theme values are accepted."""
        for theme in ["system", "light", "dark"]:
            config = UIConfig(theme=theme)
            assert config.theme == theme
    
    def test_invalid_theme_value(self):
        """Test validation error for invalid theme value."""
        with pytest.raises(ValidationError) as exc_info:
            UIConfig(theme="invalid")
        assert "literal_error" in str(exc_info.value)
    
    def test_valid_window_sizes(self):
        """Test that valid window sizes are accepted."""
        valid_sizes = [
            [400, 400],  # Minimum size
            [800, 600],  # Standard size
            [1920, 1080],  # Large size
            [3840, 2160]   # 4K size
        ]
        
        for size in valid_sizes:
            config = UIConfig(window_size=size)
            assert config.window_size == size
    
    def test_invalid_window_size_dimensions(self):
        """Test validation errors for invalid window dimensions."""
        # Too small
        with pytest.raises(ValidationError) as exc_info:
            UIConfig(window_size=[300, 400])
        assert "Window dimensions must be at least 400 pixels" in str(exc_info.value)
        
        # Too large
        with pytest.raises(ValidationError) as exc_info:
            UIConfig(window_size=[5000, 600])
        assert "Window dimensions must not exceed 4000 pixels" in str(exc_info.value)
    
    def test_invalid_window_size_count(self):
        """Test validation error for wrong number of dimensions."""
        with pytest.raises(ValidationError) as exc_info:
            UIConfig(window_size=[800])
        assert "exactly 2 values" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            UIConfig(window_size=[800, 600, 100])
        assert "exactly 2 values" in str(exc_info.value)


class TestTemplateConfig:
    """Test cases for TemplateConfig model."""
    
    def test_default_values(self):
        """Test that default values are properly assigned."""
        config = TemplateConfig()
        assert config.builtin_path == "./templates"
        assert config.custom_path == "~/.project-creator/templates"
        assert config.auto_update is False
    
    def test_path_expansion(self):
        """Test that template paths are properly expanded."""
        config = TemplateConfig(
            builtin_path="~/builtin",
            custom_path="~/custom"
        )
        # Should expand tildes to home directory
        assert config.builtin_path.startswith("/")
        assert config.custom_path.startswith("/")
        assert "builtin" in config.builtin_path
        assert "custom" in config.custom_path


class TestOllamaConfig:
    """Test cases for OllamaConfig model."""
    
    def test_default_values(self):
        """Test that default values are properly assigned."""
        config = OllamaConfig()
        assert config.api_url == "http://localhost:11434"
        assert config.timeout == 30
        assert config.preferred_model is None
        assert config.enable_cache is True
    
    def test_valid_api_urls(self):
        """Test that valid API URLs are accepted."""
        valid_urls = [
            "http://localhost:11434",
            "https://api.example.com",
            "http://192.168.1.100:8080"
        ]
        
        for url in valid_urls:
            config = OllamaConfig(api_url=url)
            assert config.api_url == url
    
    def test_invalid_api_url_format(self):
        """Test validation error for invalid API URL format."""
        with pytest.raises(ValidationError) as exc_info:
            OllamaConfig(api_url="not-a-url")
        assert "http://" in str(exc_info.value) or "https://" in str(exc_info.value)
    
    def test_timeout_validation(self):
        """Test timeout value validation."""
        # Valid timeouts
        for timeout in [1, 30, 300]:
            config = OllamaConfig(timeout=timeout)
            assert config.timeout == timeout
        
        # Invalid timeouts
        with pytest.raises(ValidationError):
            OllamaConfig(timeout=0)
        
        with pytest.raises(ValidationError):
            OllamaConfig(timeout=301)
    
    def test_optional_preferred_model(self):
        """Test that preferred_model can be None or a string."""
        config = OllamaConfig(preferred_model=None)
        assert config.preferred_model is None
        
        config = OllamaConfig(preferred_model="llama3.2:latest")
        assert config.preferred_model == "llama3.2:latest"


class TestLoggingConfig:
    """Test cases for LoggingConfig model."""
    
    def test_default_values(self):
        """Test that default values are properly assigned."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file_enabled is True
        assert config.console_enabled is True
        assert config.max_files == 5
    
    def test_valid_log_levels(self):
        """Test that valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            config = LoggingConfig(level=level)
            assert config.level == level
    
    def test_invalid_log_level(self):
        """Test validation error for invalid log level."""
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(level="INVALID")
        assert "literal_error" in str(exc_info.value)
    
    def test_max_files_validation(self):
        """Test max_files value validation."""
        # Valid values
        for max_files in [1, 5, 100]:
            config = LoggingConfig(max_files=max_files)
            assert config.max_files == max_files
        
        # Invalid values
        with pytest.raises(ValidationError):
            LoggingConfig(max_files=0)
        
        with pytest.raises(ValidationError):
            LoggingConfig(max_files=101)


class TestConfig:
    """Test cases for the root Config model."""
    
    def test_default_configuration(self):
        """Test creation of configuration with all defaults."""
        config = Config()
        
        # Check that all sections are present with correct types
        assert isinstance(config.app, AppConfig)
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.templates, TemplateConfig)
        assert isinstance(config.ollama, OllamaConfig)
        assert isinstance(config.logging, LoggingConfig)
        
        # Check some default values
        assert config.app.version == "1.0.0"
        assert config.ui.theme == "system"
        assert config.ollama.timeout == 30
    
    def test_nested_value_access(self):
        """Test getting nested values using dot notation."""
        config = Config()
        
        # Test getting existing values
        assert config.get_nested_value("ui.theme") == "system"
        assert config.get_nested_value("ollama.timeout") == 30
        assert config.get_nested_value("app.debug") is False
        
        # Test getting non-existent values
        assert config.get_nested_value("nonexistent.key", "default") == "default"
        assert config.get_nested_value("ui.nonexistent") is None
    
    def test_nested_value_setting(self):
        """Test setting nested values using dot notation."""
        config = Config()
        
        # Test setting existing values
        config.set_nested_value("ui.theme", "dark")
        assert config.ui.theme == "dark"
        
        config.set_nested_value("ollama.timeout", 60)
        assert config.ollama.timeout == 60
        
        # Test invalid paths
        with pytest.raises(ValueError, match="Unknown configuration section"):
            config.set_nested_value("invalid.key", "value")
        
        with pytest.raises(ValueError, match="Invalid key path"):
            config.set_nested_value("ui.invalid_key", "value")
    
    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            Config(extra_field="not allowed")
        assert "extra_forbidden" in str(exc_info.value)
    
    def test_configuration_consistency_validation(self):
        """Test cross-section configuration consistency validation."""
        # This should pass without issues
        config = Config(
            app=AppConfig(data_dir="/app/data"),
            templates=TemplateConfig(builtin_path="/app/templates")
        )
        assert config.app.data_dir == "/app/data"
        assert config.templates.builtin_path == "/app/templates"


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_create_default_config(self):
        """Test creation of default configuration."""
        config = create_default_config()
        
        assert isinstance(config, Config)
        assert config.app.version == "1.0.0"
        assert config.ui.theme == "system"
        assert config.ollama.timeout == 30
    
    def test_validate_config_dict_valid(self):
        """Test validation of valid configuration dictionary."""
        config_dict = {
            "app": {"version": "2.0.0", "debug": True},
            "ui": {"theme": "dark", "window_size": [1024, 768]},
            "ollama": {"timeout": 45}
        }
        
        config = validate_config_dict(config_dict)
        assert isinstance(config, Config)
        assert config.app.version == "2.0.0"
        assert config.app.debug is True
        assert config.ui.theme == "dark"
        assert config.ollama.timeout == 45
    
    def test_validate_config_dict_invalid(self):
        """Test validation error for invalid configuration dictionary."""
        config_dict = {
            "app": {"version": 123},  # Invalid type
            "ui": {"theme": "invalid"}  # Invalid value
        }
        
        with pytest.raises(ValidationError):
            validate_config_dict(config_dict)
    
    def test_validate_config_dict_partial(self):
        """Test validation of partial configuration dictionary."""
        config_dict = {
            "ui": {"theme": "light"}
        }
        
        config = validate_config_dict(config_dict)
        assert isinstance(config, Config)
        # Should have defaults for missing sections
        assert config.app.version == "1.0.0"
        assert config.ui.theme == "light"
        assert config.ollama.timeout == 30


if __name__ == "__main__":
    pytest.main([__file__])