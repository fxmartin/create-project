# ABOUTME: Tests for AI configuration loading and validation
# ABOUTME: Ensures AI settings are properly handled by ConfigManager

"""Tests for AI configuration integration with ConfigManager."""

import json
import os
from unittest import mock

import pytest

from create_project.config.config_manager import ConfigManager


class TestAIConfiguration:
    """Test AI configuration loading and management."""

    def test_load_ai_config_from_settings(self, tmp_path):
        """Test loading AI configuration from settings.json."""
        # Create settings file with AI config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.json"

        ai_config = {
            "ai": {
                "enabled": True,
                "ollama_url": "http://localhost:11434",
                "ollama_timeout": 30,
                "cache_enabled": True,
                "cache_ttl_hours": 24,
                "max_cache_entries": 100,
                "preferred_models": ["codellama:13b", "llama2:13b"],
                "context_collection_enabled": True,
                "max_context_size_kb": 4,
                "enable_ai_assistance": True,
                "response_quality_check": True,
                "max_response_tokens": 1000,
                "temperature": 0.7,
                "top_p": 0.9,
                "stream_responses": False,
                "prompt_templates": {"custom_path": "~/.project-creator/ai-templates"},
            }
        }

        settings_file.write_text(json.dumps(ai_config))

        # Load configuration
        config_manager = ConfigManager(config_path=config_dir)

        # Verify AI configuration loaded
        assert config_manager.get_setting("ai.enabled") is True
        assert config_manager.get_setting("ai.ollama_url") == "http://localhost:11434"
        assert config_manager.get_setting("ai.ollama_timeout") == 30
        assert config_manager.get_setting("ai.cache_enabled") is True
        assert config_manager.get_setting("ai.cache_ttl_hours") == 24
        assert config_manager.get_setting("ai.max_cache_entries") == 100
        assert config_manager.get_setting("ai.preferred_models") == [
            "codellama:13b",
            "llama2:13b",
        ]
        assert config_manager.get_setting("ai.context_collection_enabled") is True
        assert config_manager.get_setting("ai.max_context_size_kb") == 4
        assert config_manager.get_setting("ai.enable_ai_assistance") is True
        assert config_manager.get_setting("ai.response_quality_check") is True
        assert config_manager.get_setting("ai.max_response_tokens") == 1000
        assert config_manager.get_setting("ai.temperature") == 0.7
        assert config_manager.get_setting("ai.top_p") == 0.9
        assert config_manager.get_setting("ai.stream_responses") is False
        # Path is expanded, so we need to check the expanded version
        custom_path = config_manager.get_setting("ai.prompt_templates.custom_path")
        assert custom_path.endswith("/.project-creator/ai-templates")

    def test_ai_config_environment_override(self, tmp_path):
        """Test environment variables override AI settings."""
        # Create minimal settings
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "ai": {
                        "enabled": False,
                        "ollama_url": "http://localhost:11434",
                        "temperature": 0.5,
                    }
                }
            )
        )

        # Set environment variables
        with mock.patch.dict(
            os.environ,
            {
                "APP_AI_ENABLED": "true",
                "APP_AI_OLLAMA_URL": "http://custom:8080",
                "APP_AI_TEMPERATURE": "0.9",
            },
        ):
            config_manager = ConfigManager(config_path=config_dir)

            # Environment variables should override settings
            assert config_manager.get_setting("ai.enabled") is True
            assert config_manager.get_setting("ai.ollama_url") == "http://custom:8080"
            assert config_manager.get_setting("ai.temperature") == 0.9

    def test_ai_config_defaults(self, tmp_path):
        """Test AI configuration defaults when not specified."""
        # Create empty settings
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.json"
        settings_file.write_text(json.dumps({}))

        config_manager = ConfigManager(config_path=config_dir)

        # Should have sensible defaults
        assert config_manager.get_setting("ai.enabled", True) is True
        assert (
            config_manager.get_setting("ai.ollama_url", "http://localhost:11434")
            == "http://localhost:11434"
        )
        assert config_manager.get_setting("ai.cache_enabled", True) is True

    def test_ai_service_config_creation(self, tmp_path):
        """Test creating AIServiceConfig from ConfigManager."""
        from create_project.ai.ai_service import AIServiceConfig

        # Create settings with AI config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.json"

        ai_settings = {
            "ai": {
                "enabled": True,
                "ollama_url": "http://localhost:11434",
                "ollama_timeout": 45,
                "cache_enabled": False,
                "cache_ttl_hours": 48,
                "max_cache_entries": 200,
                "preferred_models": ["mistral:7b"],
                "context_collection_enabled": False,
                "max_context_size_kb": 8,
            }
        }

        settings_file.write_text(json.dumps(ai_settings))
        config_manager = ConfigManager(config_path=config_dir)

        # Create AIServiceConfig from settings
        ai_config = AIServiceConfig(
            enabled=config_manager.get_setting("ai.enabled", True),
            ollama_url=config_manager.get_setting(
                "ai.ollama_url", "http://localhost:11434"
            ),
            ollama_timeout=config_manager.get_setting("ai.ollama_timeout", 30),
            cache_enabled=config_manager.get_setting("ai.cache_enabled", True),
            cache_ttl_hours=config_manager.get_setting("ai.cache_ttl_hours", 24),
            max_cache_entries=config_manager.get_setting("ai.max_cache_entries", 100),
            preferred_models=config_manager.get_setting("ai.preferred_models"),
            context_collection_enabled=config_manager.get_setting(
                "ai.context_collection_enabled", True
            ),
            max_context_size_kb=config_manager.get_setting("ai.max_context_size_kb", 4),
        )

        # Verify configuration
        assert ai_config.enabled is True
        assert ai_config.ollama_url == "http://localhost:11434"
        assert ai_config.ollama_timeout == 45
        assert ai_config.cache_enabled is False
        assert ai_config.cache_ttl_hours == 48
        assert ai_config.max_cache_entries == 200
        assert ai_config.preferred_models == ["mistral:7b"]
        assert ai_config.context_collection_enabled is False
        assert ai_config.max_context_size_kb == 8

    def test_nested_ai_config_access(self, tmp_path):
        """Test accessing nested AI configuration values."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.json"

        settings = {
            "ai": {
                "prompt_templates": {"custom_path": "/custom/templates"},
                "temperature": 0.8,
                "max_response_tokens": 2000,
            }
        }

        settings_file.write_text(json.dumps(settings))
        config_manager = ConfigManager(config_path=config_dir)

        # Test nested access
        assert (
            config_manager.get_setting("ai.prompt_templates.custom_path")
            == "/custom/templates"
        )
        assert config_manager.get_setting("ai.temperature") == 0.8
        assert config_manager.get_setting("ai.max_response_tokens") == 2000
        # Test access to non-existent nested values returns None
        assert config_manager.get_setting("ai.non_existent.value") is None

    def test_ai_config_type_conversion(self, tmp_path):
        """Test type conversion for AI configuration from environment."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.json"
        settings_file.write_text(json.dumps({}))

        with mock.patch.dict(
            os.environ,
            {
                "APP_AI_ENABLED": "false",
                "APP_AI_CACHE_ENABLED": "true",
                "APP_AI_MAX_CACHE_ENTRIES": "250",
                "APP_AI_TEMPERATURE": "0.85",
                "APP_AI_PREFERRED_MODELS": "model1,model2,model3",
            },
        ):
            config_manager = ConfigManager(config_path=config_dir)

            # Boolean conversion
            assert config_manager.get_setting("ai.enabled") is False
            assert config_manager.get_setting("ai.cache_enabled") is True

            # Integer conversion
            assert config_manager.get_setting("ai.max_cache_entries") == 250
            assert isinstance(config_manager.get_setting("ai.max_cache_entries"), int)

            # Float conversion
            assert config_manager.get_setting("ai.temperature") == 0.85
            assert isinstance(config_manager.get_setting("ai.temperature"), float)

            # List conversion (comma-separated)
            models = config_manager.get_setting("ai.preferred_models")
            assert models == ["model1", "model2", "model3"]

    def test_invalid_ai_config_handling(self, tmp_path):
        """Test handling of invalid AI configuration values."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.json"

        # Invalid JSON
        settings_file.write_text("invalid json {")

        # ConfigManager doesn't raise error on init, only when loading config
        config_manager = ConfigManager(config_path=config_dir)

        # Error occurs when trying to access a setting
        from create_project.config.config_manager import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            config_manager.get_setting("ai.enabled")

        assert "Invalid JSON" in str(exc_info.value)
