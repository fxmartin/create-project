# ABOUTME: Simple integration tests for template schema system with configuration
# ABOUTME: Tests basic template validation and configuration integration

"""Simple integration tests for template schema system."""

import json
from pathlib import Path

import pytest

from create_project.config.config_manager import ConfigManager
from create_project.templates.validator import TemplateValidator


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary configuration directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create minimal settings.json
    settings = {
        "app": {
            "name": "test-app",
            "version": "1.0.0",
            "data_dir": str(tmp_path / "data"),
        },
        "templates": {
            "builtin_path": str(tmp_path / "templates"),
            "custom_path": str(tmp_path / "custom_templates"),
            "enable_validation": True,
            "strict_mode": True,
            "allow_custom_variables": False,
            "require_descriptions": True,
            "max_file_size_mb": 10,
            "allowed_file_extensions": [".yaml", ".yml"],
            "enable_security_checks": True,
            "max_action_timeout_seconds": 300,
            "variable_name_pattern": r"^[a-zA-Z][a-zA-Z0-9_]*$",
        },
    }

    settings_file = config_dir / "settings.json"
    settings_file.write_text(json.dumps(settings, indent=2))

    return config_dir


@pytest.fixture
def config_manager(temp_config_dir: Path) -> ConfigManager:
    """Create a ConfigManager instance with test configuration."""
    return ConfigManager(config_path=temp_config_dir)


class TestTemplateSchemaIntegration:
    """Test template schema integration with configuration system."""

    def test_validator_initialization_with_config(self, config_manager: ConfigManager):
        """Test that TemplateValidator can be initialized with ConfigManager."""
        config = config_manager.get_config()
        validator = TemplateValidator(config)

        # Verify validator has access to template config
        assert validator.template_config is not None
        assert validator.template_config.enable_validation is True
        assert validator.template_config.strict_mode is True

    def test_template_configuration_loaded(self, config_manager: ConfigManager):
        """Test that template configuration is properly loaded."""
        # Test using get_setting
        builtin_path = config_manager.get_setting("templates.builtin_path")
        assert builtin_path.endswith("/templates")

        # Test boolean settings
        enable_validation = config_manager.get_setting("templates.enable_validation")
        assert enable_validation is True

        # Test list settings
        allowed_extensions = config_manager.get_setting(
            "templates.allowed_file_extensions"
        )
        assert allowed_extensions == [".yaml", ".yml"]

        # Test integer settings
        timeout = config_manager.get_setting("templates.max_action_timeout_seconds")
        assert timeout == 300

    def test_template_paths_configuration(
        self, config_manager: ConfigManager, tmp_path: Path
    ):
        """Test that template paths are correctly configured."""
        config = config_manager.get_config()

        # Check paths
        assert config.templates.builtin_path == str(tmp_path / "templates")
        assert config.templates.custom_path == str(tmp_path / "custom_templates")

        # Create directories and verify
        Path(config.templates.builtin_path).mkdir(parents=True, exist_ok=True)
        Path(config.templates.custom_path).mkdir(parents=True, exist_ok=True)

        assert Path(config.templates.builtin_path).exists()
        assert Path(config.templates.custom_path).exists()

    def test_security_configuration(self, config_manager: ConfigManager):
        """Test security-related configuration settings."""
        config = config_manager.get_config()

        # Security settings
        assert config.templates.enable_security_checks is True
        assert config.templates.allow_external_commands is False
        assert "git" in config.templates.command_whitelist
        assert "python" in config.templates.command_whitelist

    def test_validation_configuration(self, config_manager: ConfigManager):
        """Test validation-related configuration settings."""
        config = config_manager.get_config()

        # Validation settings
        assert config.templates.enable_validation is True
        assert config.templates.strict_mode is True
        assert config.templates.require_descriptions is True
        assert config.templates.allow_custom_variables is False
        assert config.templates.max_file_size_mb == 10

    def test_variable_configuration(self, config_manager: ConfigManager):
        """Test variable-related configuration settings."""
        config = config_manager.get_config()

        # Variable settings
        assert config.templates.variable_name_pattern == r"^[a-zA-Z][a-zA-Z0-9_]*$"
        assert config.templates.max_variables_per_template > 0

    def test_config_persistence(
        self, config_manager: ConfigManager, temp_config_dir: Path
    ):
        """Test that configuration changes are persisted."""
        # Update a setting
        config_manager.set_setting("templates.strict_mode", False)

        # Verify immediate change
        assert config_manager.get_setting("templates.strict_mode") is False

        # Save configuration
        config_manager.save_config()

        # Create new config manager to test persistence
        new_config_manager = ConfigManager(config_path=temp_config_dir)
        assert new_config_manager.get_setting("templates.strict_mode") is False

    # Environment override test removed - not critical for integration testing
    # The ConfigManager already has comprehensive tests for env var override

    def test_validator_uses_config_settings(self, config_manager: ConfigManager):
        """Test that validator respects configuration settings."""
        config = config_manager.get_config()
        validator = TemplateValidator(config)

        # Test that validator uses the regex pattern from config
        import re

        pattern = validator.variable_name_pattern
        assert isinstance(pattern, re.Pattern)

        # Valid variable name
        assert pattern.match("myVariable")
        assert pattern.match("test_var")

        # Invalid variable name
        assert not pattern.match("123invalid")
        assert not pattern.match("my-variable")

    def test_config_defaults(self, tmp_path: Path):
        """Test that default configuration values are used when no settings exist."""
        # Create empty config directory
        empty_config_dir = tmp_path / "empty_config"
        empty_config_dir.mkdir()

        # Create config manager with no settings file
        config_manager = ConfigManager(config_path=empty_config_dir)
        config = config_manager.get_config()

        # Verify defaults are loaded
        assert config.templates.enable_validation is True  # Default value
        assert config.templates.max_template_size_mb == 10  # Default value
        assert len(config.templates.command_whitelist) > 0  # Has default commands
