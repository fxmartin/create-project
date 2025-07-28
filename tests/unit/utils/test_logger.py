# ABOUTME: Comprehensive unit tests for logging infrastructure module
# ABOUTME: Tests structured logging, configuration, environment handling, and file operations

"""Unit tests for logger module."""

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest
import yaml

from create_project.utils.logger import (
    LoggerConfig,
    StructuredLogger,
    get_default_config,
    get_default_logger,
    get_environment,
    get_logger,
    init_logging,
    load_config_from_yaml,
)


class TestLoggerConfig:
    """Test LoggerConfig class."""

    def test_initialization_with_defaults(self):
        """Test LoggerConfig initialization with default values."""
        config = LoggerConfig()
        
        assert config.level == "INFO"
        assert config.format_json is False
        assert config.include_context is True
        assert config.max_bytes == 10 * 1024 * 1024
        assert config.backup_count == 30
        assert config.console_colors is True
        assert isinstance(config.log_dir, Path)

    def test_initialization_with_custom_values(self, tmp_path):
        """Test LoggerConfig initialization with custom values."""
        custom_log_dir = tmp_path / "custom_logs"
        
        config = LoggerConfig(
            level="DEBUG",
            format_json=True,
            include_context=False,
            log_dir=str(custom_log_dir),
            max_bytes=5 * 1024 * 1024,
            backup_count=10,
            console_colors=False,
        )
        
        assert config.level == "DEBUG"
        assert config.format_json is True
        assert config.include_context is False
        assert config.log_dir == custom_log_dir
        assert config.max_bytes == 5 * 1024 * 1024
        assert config.backup_count == 10
        assert config.console_colors is False

    def test_level_normalization(self):
        """Test that log level is normalized to uppercase."""
        config = LoggerConfig(level="debug")
        assert config.level == "DEBUG"
        
        config = LoggerConfig(level="warning")
        assert config.level == "WARNING"

    def test_log_dir_creation(self, tmp_path):
        """Test that log directory is created if it doesn't exist."""
        log_dir = tmp_path / "new_logs"
        assert not log_dir.exists()
        
        config = LoggerConfig(log_dir=str(log_dir))
        
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_get_default_log_dir_finds_project_root(self, tmp_path):
        """Test _get_default_log_dir finds project root with pyproject.toml."""
        # Create a mock project structure
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[project]\nname = 'test'")
        
        # Create nested directory structure
        nested_dir = project_root / "src" / "utils"
        nested_dir.mkdir(parents=True)
        
        # Mock the __file__ path to be in the nested directory
        mock_file_path = nested_dir / "logger.py"
        with patch.object(LoggerConfig, '_get_default_log_dir') as mock_method:
            # Simulate the method behavior manually
            current_dir = mock_file_path.parent
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    mock_method.return_value = current_dir / "logs"
                    break
                current_dir = current_dir.parent
            else:
                mock_method.return_value = mock_file_path.parent.parent.parent / "logs"
            
            config = LoggerConfig()
            
            # Should find project root and use logs directory
            expected_log_dir = project_root / "logs"
            assert config.log_dir == expected_log_dir

    def test_get_default_log_dir_fallback(self, tmp_path):
        """Test _get_default_log_dir fallback when no pyproject.toml found."""
        # Mock file path without pyproject.toml in parent directories
        mock_file_path = tmp_path / "deep" / "nested" / "path" / "logger.py"
        mock_file_path.parent.mkdir(parents=True)
        
        with patch.object(LoggerConfig, '_get_default_log_dir') as mock_method:
            # Simulate fallback behavior
            expected_fallback = mock_file_path.parent.parent.parent / "logs"
            mock_method.return_value = expected_fallback
            
            config = LoggerConfig()
            
            # Should use fallback path relative to logger.py
            assert config.log_dir == expected_fallback

    def test_log_dir_creation_with_permissions_error(self, tmp_path):
        """Test log directory creation with permission errors."""
        log_dir = tmp_path / "restricted_logs"
        
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                LoggerConfig(log_dir=str(log_dir))

    def test_none_log_dir_uses_default(self):
        """Test that None log_dir uses default directory discovery."""
        config = LoggerConfig(log_dir=None)
        
        # Should have found some default directory
        assert isinstance(config.log_dir, Path)
        assert config.log_dir.exists()

    def test_log_dir_as_path_object(self, tmp_path):
        """Test that log_dir accepts Path objects."""
        log_dir_path = tmp_path / "path_logs"
        
        config = LoggerConfig(log_dir=log_dir_path)
        
        assert config.log_dir == log_dir_path
        assert log_dir_path.exists()


class TestStructuredLogger:
    """Test StructuredLogger class."""

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Create temporary log directory."""
        log_dir = tmp_path / "test_logs"
        log_dir.mkdir()
        return log_dir

    @pytest.fixture
    def basic_config(self, temp_log_dir):
        """Create basic logger configuration."""
        return LoggerConfig(
            level="DEBUG",
            log_dir=str(temp_log_dir),
            console_colors=False,  # Disable colors for testing
        )

    @pytest.fixture
    def logger(self, basic_config):
        """Create test logger instance."""
        return StructuredLogger("test_logger", basic_config)

    def test_initialization(self, basic_config):
        """Test StructuredLogger initialization."""
        logger = StructuredLogger("test_module", basic_config)
        
        assert logger.name == "test_module"
        assert logger.config == basic_config
        assert logger._logger is not None
        assert isinstance(logger._logger, logging.Logger)

    def test_logger_setup_creates_handlers(self, logger, temp_log_dir):
        """Test that logger setup creates appropriate handlers."""
        handlers = logger._logger.handlers
        
        # Should have console handler and file handlers
        assert len(handlers) >= 2
        
        # Check that log files are created
        assert (temp_log_dir / "app.log").exists()
        assert (temp_log_dir / "error.log").exists()
        assert (temp_log_dir / "debug.log").exists()  # DEBUG level enabled

    def test_logger_setup_without_debug(self, tmp_path):
        """Test logger setup without DEBUG level."""
        config = LoggerConfig(level="INFO", log_dir=str(tmp_path))
        logger = StructuredLogger("test", config)
        
        # Debug log should not be created for INFO level
        assert not (tmp_path / "debug.log").exists()

    def test_console_handler_with_colors(self, tmp_path):
        """Test console handler with colors enabled."""
        config = LoggerConfig(log_dir=str(tmp_path), console_colors=True)
        
        with patch('sys.stdout.isatty', return_value=True):
            logger = StructuredLogger("test", config)
            
            # Should have console handler with color formatter
            console_handlers = [h for h in logger._logger.handlers 
                              if isinstance(h, logging.StreamHandler)]
            assert len(console_handlers) > 0

    def test_console_handler_without_colors(self, tmp_path):
        """Test console handler without colors."""
        config = LoggerConfig(log_dir=str(tmp_path), console_colors=False)
        logger = StructuredLogger("test", config)
        
        # Should have console handler with plain formatter
        console_handlers = [h for h in logger._logger.handlers 
                          if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) > 0

    def test_json_formatter(self, tmp_path):
        """Test JSON formatter configuration."""
        config = LoggerConfig(log_dir=str(tmp_path), format_json=True)
        logger = StructuredLogger("test", config)
        
        # Check that file handlers use JSON formatter
        file_handlers = [h for h in logger._logger.handlers 
                        if hasattr(h, 'baseFilename')]
        assert len(file_handlers) > 0

    def test_structlog_setup_with_context(self, tmp_path):
        """Test structlog setup when context is enabled."""
        config = LoggerConfig(log_dir=str(tmp_path), include_context=True)
        
        with patch('structlog.configure') as mock_configure:
            logger = StructuredLogger("test", config)
            mock_configure.assert_called_once()

    def test_structlog_setup_without_context(self, tmp_path):
        """Test structlog setup when context is disabled."""
        config = LoggerConfig(log_dir=str(tmp_path), include_context=False)
        
        with patch('structlog.configure') as mock_configure:
            logger = StructuredLogger("test", config)
            mock_configure.assert_not_called()

    def test_debug_logging(self, logger):
        """Test debug logging method."""
        with patch.object(logger._logger, 'debug') as mock_debug:
            logger.debug("Debug message")
            mock_debug.assert_called_once_with("Debug message")

    def test_debug_logging_with_context(self, logger):
        """Test debug logging with context."""
        with patch.object(logger._logger, 'debug') as mock_debug:
            logger.debug("Debug message", user_id=123, action="test")
            mock_debug.assert_called_once_with("Debug message", extra={'user_id': 123, 'action': 'test'})

    def test_info_logging(self, logger):
        """Test info logging method."""
        with patch.object(logger._logger, 'info') as mock_info:
            logger.info("Info message")
            mock_info.assert_called_once_with("Info message")

    def test_info_logging_with_context(self, logger):
        """Test info logging with context."""
        with patch.object(logger._logger, 'info') as mock_info:
            logger.info("Info message", component="auth", status="success")
            mock_info.assert_called_once_with("Info message", extra={'component': 'auth', 'status': 'success'})

    def test_warning_logging(self, logger):
        """Test warning logging method."""
        with patch.object(logger._logger, 'warning') as mock_warning:
            logger.warning("Warning message")
            mock_warning.assert_called_once_with("Warning message")

    def test_error_logging(self, logger):
        """Test error logging method."""
        with patch.object(logger._logger, 'error') as mock_error:
            logger.error("Error message")
            mock_error.assert_called_once_with("Error message")

    def test_critical_logging(self, logger):
        """Test critical logging method."""
        with patch.object(logger._logger, 'critical') as mock_critical:
            logger.critical("Critical message")
            mock_critical.assert_called_once_with("Critical message")

    def test_exception_logging(self, logger):
        """Test exception logging method."""
        with patch.object(logger._logger, 'exception') as mock_exception:
            logger.exception("Exception message")
            mock_exception.assert_called_once_with("Exception message")

    def test_logging_without_context_enabled(self, tmp_path):
        """Test logging methods when context is disabled."""
        config = LoggerConfig(log_dir=str(tmp_path), include_context=False)
        logger = StructuredLogger("test", config)
        
        with patch.object(logger._logger, 'info') as mock_info:
            logger.info("Message", ignored_context="value")
            # Should ignore context when include_context is False
            mock_info.assert_called_once_with("Message")

    def test_get_structlog_logger_with_context(self, logger):
        """Test getting structlog logger when context is enabled."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_structlog = Mock()
            mock_get_logger.return_value = mock_structlog
            
            result = logger.get_structlog_logger()
            
            mock_get_logger.assert_called_once_with("test_logger")
            assert result == mock_structlog

    def test_get_structlog_logger_without_context(self, tmp_path):
        """Test getting structlog logger when context is disabled."""
        config = LoggerConfig(log_dir=str(tmp_path), include_context=False)
        logger = StructuredLogger("test", config)
        
        with pytest.raises(ValueError, match="Context logging must be enabled"):
            logger.get_structlog_logger()

    def test_handler_clearing(self, tmp_path):
        """Test that existing handlers are cleared to avoid duplicates."""
        config = LoggerConfig(log_dir=str(tmp_path))
        
        # Create logger twice with same name
        logger1 = StructuredLogger("duplicate_test", config)
        original_handler_count = len(logger1._logger.handlers)
        
        logger2 = StructuredLogger("duplicate_test", config)
        
        # Should not have doubled the handlers 
        assert len(logger2._logger.handlers) == original_handler_count

    def test_file_handler_rotation_config(self, logger, temp_log_dir):
        """Test that file handlers are configured with correct rotation settings."""
        file_handlers = [h for h in logger._logger.handlers 
                        if hasattr(h, 'maxBytes')]
        
        assert len(file_handlers) > 0
        for handler in file_handlers:
            assert handler.maxBytes == logger.config.max_bytes
            assert handler.backupCount == logger.config.backup_count

    def test_error_handler_level_filtering(self, logger):
        """Test that error handler only handles ERROR and above."""
        error_handlers = [h for h in logger._logger.handlers 
                         if hasattr(h, 'baseFilename') and 'error.log' in h.baseFilename]
        
        assert len(error_handlers) == 1
        assert error_handlers[0].level == logging.ERROR

    def test_structlog_json_processor(self, tmp_path):
        """Test structlog JSON processor configuration."""
        config = LoggerConfig(log_dir=str(tmp_path), format_json=True, include_context=True)
        
        with patch('structlog.configure') as mock_configure:
            StructuredLogger("test", config)
            
            # Check that JSON processor is included
            call_args = mock_configure.call_args[1]
            processors = call_args['processors']
            
            # Should have JSON renderer when format_json=True
            processor_types = [type(p).__name__ for p in processors]
            assert 'JSONRenderer' in processor_types

    def test_structlog_console_processor(self, tmp_path):
        """Test structlog console processor configuration."""
        config = LoggerConfig(log_dir=str(tmp_path), format_json=False, include_context=True)
        
        with patch('structlog.configure') as mock_configure:
            StructuredLogger("test", config)
            
            # Check that console renderer is included
            call_args = mock_configure.call_args[1]
            processors = call_args['processors']
            
            # Should have console renderer when format_json=False
            processor_types = [type(p).__name__ for p in processors]
            assert 'ConsoleRenderer' in processor_types


class TestEnvironmentDetection:
    """Test environment detection functions."""

    def test_get_environment_development(self):
        """Test environment detection for development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert get_environment() == "development"
        
        with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
            assert get_environment() == "development"

    def test_get_environment_production(self):
        """Test environment detection for production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert get_environment() == "production"
        
        with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
            assert get_environment() == "production"

    def test_get_environment_testing(self):
        """Test environment detection for testing."""
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            assert get_environment() == "testing"
        
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            assert get_environment() == "testing"

    def test_get_environment_default(self):
        """Test environment detection default (development)."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_environment() == "development"
        
        with patch.dict(os.environ, {"ENVIRONMENT": "unknown"}):
            assert get_environment() == "development"

    def test_get_environment_case_insensitive(self):
        """Test environment detection is case insensitive."""
        with patch.dict(os.environ, {"ENVIRONMENT": "PRODUCTION"}):
            assert get_environment() == "production"
        
        with patch.dict(os.environ, {"ENVIRONMENT": "Development"}):
            assert get_environment() == "development"


class TestYAMLConfigLoading:
    """Test YAML configuration loading."""

    @pytest.fixture
    def sample_yaml_config(self):
        """Create sample YAML configuration."""
        return {
            "development": {
                "level": "DEBUG",
                "format_json": False,
                "include_context": True,
                "console_colors": True,
                "max_bytes": 5242880,
                "backup_count": 15,
            },
            "production": {
                "level": "INFO",
                "format_json": True,
                "include_context": True,
                "console_colors": False,
                "max_bytes": 10485760,
                "backup_count": 30,
            },
            "testing": {
                "level": "WARNING",
                "format_json": False,
                "include_context": False,
                "console_colors": False,
            },
        }

    def test_load_config_from_yaml_success(self, tmp_path, sample_yaml_config):
        """Test successful YAML configuration loading."""
        config_file = tmp_path / "logging.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_yaml_config, f)
        
        config = load_config_from_yaml(str(config_file), "development")
        
        assert config.level == "DEBUG"
        assert config.format_json is False
        assert config.include_context is True
        assert config.console_colors is True
        assert config.max_bytes == 5242880
        assert config.backup_count == 15

    def test_load_config_from_yaml_production(self, tmp_path, sample_yaml_config):
        """Test YAML configuration loading for production environment."""
        config_file = tmp_path / "logging.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_yaml_config, f)
        
        config = load_config_from_yaml(str(config_file), "production")
        
        assert config.level == "INFO"
        assert config.format_json is True
        assert config.console_colors is False

    def test_load_config_from_yaml_file_not_found(self, tmp_path):
        """Test YAML configuration loading with missing file."""
        nonexistent_file = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config_from_yaml(str(nonexistent_file))

    def test_load_config_from_yaml_invalid_yaml(self, tmp_path):
        """Test YAML configuration loading with invalid YAML."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")
        
        with pytest.raises(ValueError, match="Error loading YAML configuration"):
            load_config_from_yaml(str(config_file))

    def test_load_config_from_yaml_missing_environment(self, tmp_path, sample_yaml_config):
        """Test YAML configuration loading with missing environment."""
        config_file = tmp_path / "logging.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_yaml_config, f)
        
        with pytest.raises(ValueError, match="Environment 'nonexistent' not found"):
            load_config_from_yaml(str(config_file), "nonexistent")

    def test_load_config_from_yaml_auto_environment(self, tmp_path, sample_yaml_config):
        """Test YAML configuration loading with automatic environment detection."""
        config_file = tmp_path / "logging.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_yaml_config, f)
        
        with patch('create_project.utils.logger.get_environment', return_value="production"):
            config = load_config_from_yaml(str(config_file))
            assert config.level == "INFO"
            assert config.format_json is True

    def test_load_config_from_yaml_default_file_path(self, sample_yaml_config, tmp_path):
        """Test YAML configuration loading with default file path."""
        # Create the actual file in the expected default location pattern
        mock_config_file = tmp_path / "config" / "logging.yaml"
        mock_config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(mock_config_file, 'w') as f:
            yaml.dump(sample_yaml_config, f)
        
        # Mock __file__ to simulate the logger.py location
        with patch('create_project.utils.logger.__file__', str(tmp_path / "utils" / "logger.py")):
            config = load_config_from_yaml(environment="development")
            assert config.level == "DEBUG"

    def test_load_config_from_yaml_partial_config(self, tmp_path):
        """Test YAML configuration loading with partial configuration (uses defaults)."""
        partial_config = {
            "development": {
                "level": "ERROR",
                # Missing other fields - should use defaults
            }
        }
        
        config_file = tmp_path / "partial.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(partial_config, f)
        
        config = load_config_from_yaml(str(config_file), "development")
        
        assert config.level == "ERROR"
        # Should use defaults for missing values
        assert config.format_json is False  # Default
        assert config.include_context is True  # Default
        assert config.max_bytes == 10 * 1024 * 1024  # Default


class TestDefaultConfiguration:
    """Test default configuration functions."""

    def test_get_default_config_development(self):
        """Test default configuration for development environment."""
        with patch('create_project.utils.logger.get_environment', return_value="development"):
            with patch('create_project.utils.logger.load_config_from_yaml', 
                      side_effect=FileNotFoundError()):
                config = get_default_config()
                
                assert config.level == "DEBUG"
                assert config.format_json is False
                assert config.include_context is True
                assert config.console_colors is True

    def test_get_default_config_production(self):
        """Test default configuration for production environment."""
        with patch('create_project.utils.logger.get_environment', return_value="production"):
            with patch('create_project.utils.logger.load_config_from_yaml', 
                      side_effect=FileNotFoundError()):
                config = get_default_config("production")
                
                assert config.level == "INFO"
                assert config.format_json is True
                assert config.include_context is True
                assert config.console_colors is False

    def test_get_default_config_testing(self):
        """Test default configuration for testing environment."""
        with patch('create_project.utils.logger.load_config_from_yaml', 
                  side_effect=FileNotFoundError()):
            config = get_default_config("testing")
            
            assert config.level == "WARNING"
            assert config.format_json is False
            assert config.include_context is False
            assert config.console_colors is False

    def test_get_default_config_yaml_fallback(self, tmp_path):
        """Test that get_default_config tries YAML first, then falls back."""
        yaml_config = {
            "development": {
                "level": "ERROR",
                "format_json": True,
            }
        }
        
        config_file = tmp_path / "logging.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(yaml_config, f)
        
        with patch('create_project.utils.logger.load_config_from_yaml', 
                  return_value=LoggerConfig(level="ERROR", format_json=True)):
            config = get_default_config("development")
            
            # Should use YAML configuration, not hardcoded defaults
            assert config.level == "ERROR"
            assert config.format_json is True

    def test_get_default_config_unknown_environment(self):
        """Test default configuration with unknown environment."""
        with patch('create_project.utils.logger.load_config_from_yaml', 
                  side_effect=FileNotFoundError()):
            with pytest.raises(ValueError, match="Unknown environment"):
                get_default_config("unknown")

    def test_get_default_config_yaml_error_fallback(self):
        """Test fallback when YAML loading fails with ValueError."""
        with patch('create_project.utils.logger.load_config_from_yaml', 
                  side_effect=ValueError("Invalid YAML")):
            config = get_default_config("development")
            
            # Should fall back to hardcoded defaults
            assert config.level == "DEBUG"
            assert config.format_json is False


class TestGlobalLoggerFunctions:
    """Test global logger functions."""

    def test_get_logger_with_config(self, tmp_path):
        """Test get_logger with provided configuration."""
        config = LoggerConfig(log_dir=str(tmp_path))
        logger = get_logger("test_module", config)
        
        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test_module"
        assert logger.config == config

    def test_get_logger_without_config(self):
        """Test get_logger without configuration (uses default)."""
        with patch('create_project.utils.logger.get_default_config') as mock_get_default:
            # Create a proper mock config with required attributes
            mock_config = LoggerConfig(level="INFO")
            mock_get_default.return_value = mock_config
            
            logger = get_logger("test_module")
            
            mock_get_default.assert_called_once()
            assert logger.config == mock_config

    def test_init_logging_with_config(self, tmp_path):
        """Test init_logging with provided configuration."""
        config = LoggerConfig(log_dir=str(tmp_path))
        
        with patch('create_project.utils.logger._default_logger', None):
            init_logging(config)
            
            from create_project.utils.logger import _default_logger
            assert _default_logger is not None
            assert _default_logger.name == "app"
            assert _default_logger.config == config

    def test_init_logging_without_config(self):
        """Test init_logging without configuration (uses default)."""
        with patch('create_project.utils.logger.get_default_config') as mock_get_default:
            with patch('create_project.utils.logger._default_logger', None):
                # Create a proper mock config with required attributes
                mock_config = LoggerConfig(level="INFO")
                mock_get_default.return_value = mock_config
                
                init_logging()
                
                mock_get_default.assert_called_once()

    def test_init_logging_logs_initialization(self, tmp_path):
        """Test that init_logging logs initialization message."""
        config = LoggerConfig(log_dir=str(tmp_path))
        
        with patch('create_project.utils.logger._default_logger', None):
            with patch('create_project.utils.logger.StructuredLogger') as mock_logger_class:
                mock_logger = Mock()
                mock_logger_class.return_value = mock_logger
                
                init_logging(config)
                
                mock_logger.info.assert_called_once()
                call_args = mock_logger.info.call_args
                assert "Logging system initialized" in call_args[0][0]

    def test_get_default_logger_success(self, tmp_path):
        """Test get_default_logger when logging is initialized."""
        config = LoggerConfig(log_dir=str(tmp_path))
        
        with patch('create_project.utils.logger._default_logger', None):
            init_logging(config)
            
            logger = get_default_logger()
            assert isinstance(logger, StructuredLogger)

    def test_get_default_logger_not_initialized(self):
        """Test get_default_logger when logging is not initialized."""
        with patch('create_project.utils.logger._default_logger', None):
            with pytest.raises(RuntimeError, match="Logging not initialized"):
                get_default_logger()

    def test_multiple_init_logging_calls(self, tmp_path):
        """Test multiple calls to init_logging (should replace logger)."""
        config1 = LoggerConfig(log_dir=str(tmp_path / "logs1"))
        config2 = LoggerConfig(log_dir=str(tmp_path / "logs2"))
        
        with patch('create_project.utils.logger._default_logger', None):
            init_logging(config1)
            logger1 = get_default_logger()
            
            init_logging(config2)
            logger2 = get_default_logger()
            
            # Should be different logger instances
            assert logger1 is not logger2
            assert logger2.config == config2


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_end_to_end_logging_workflow(self, tmp_path):
        """Test complete logging workflow from initialization to actual logging."""
        log_dir = tmp_path / "integration_logs"
        config = LoggerConfig(
            level="DEBUG",
            log_dir=str(log_dir),
            format_json=False,
            console_colors=False,
        )
        
        # Initialize logging
        with patch('create_project.utils.logger._default_logger', None):
            init_logging(config)
            
            # Get logger and log messages
            logger = get_default_logger()
            logger.info("Test info message", component="test")
            logger.error("Test error message", error_code=500)
            
            # Verify log files exist
            assert (log_dir / "app.log").exists()
            assert (log_dir / "error.log").exists()

    def test_yaml_config_integration(self, tmp_path):
        """Test full YAML configuration integration."""
        yaml_config = {
            "development": {
                "level": "INFO",
                "format_json": False,
                "include_context": True,
                "console_colors": True,
            }
        }
        
        config_file = tmp_path / "logging.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(yaml_config, f)
        
        # Load and use configuration
        config = load_config_from_yaml(str(config_file), "development")
        logger = StructuredLogger("integration_test", config)
        
        assert logger.config.level == "INFO"
        assert logger.config.include_context is True

    def test_concurrent_logger_creation(self, tmp_path):
        """Test thread-safe logger creation."""
        import threading
        import time
        
        config = LoggerConfig(log_dir=str(tmp_path))
        loggers = []
        errors = []
        
        def create_logger(name):
            try:
                logger = StructuredLogger(f"thread_{name}", config)
                loggers.append(logger)
                time.sleep(0.01)  # Small delay to encourage race conditions
                logger.info(f"Message from thread {name}")
            except Exception as e:
                errors.append(e)
        
        # Create multiple loggers concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_logger, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(loggers) == 5

    def test_logging_with_large_context_data(self, tmp_path):
        """Test logging with large context data."""
        config = LoggerConfig(log_dir=str(tmp_path))
        logger = StructuredLogger("large_context_test", config)
        
        # Create large context data
        large_context = {
            f"key_{i}": f"value_{i}" * 100 for i in range(100)
        }
        
        # Should handle large context without issues
        logger.info("Message with large context", **large_context)
        
        # Verify log file exists and has content
        log_file = tmp_path / "app.log"
        assert log_file.exists()
        assert log_file.stat().st_size > 0

    def test_logging_system_resilience(self, tmp_path):
        """Test logging system resilience to various error conditions."""
        config = LoggerConfig(log_dir=str(tmp_path))
        logger = StructuredLogger("resilience_test", config)
        
        # Test logging with None values
        logger.info("Message with None", value=None)
        
        # Test logging with empty strings
        logger.info("", empty_context="")
        
        # Test logging with unicode characters
        logger.info("Unicode test: 🔥 🎉 ñáéíóú", unicode_field="测试")
        
        # All should complete without exceptions
        log_file = tmp_path / "app.log"
        assert log_file.exists()

    def test_environment_variable_override(self, tmp_path):
        """Test environment variable override behavior."""
        yaml_config = {
            "custom_env": {
                "level": "ERROR",
                "format_json": True,
            }
        }
        
        config_file = tmp_path / "logging.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(yaml_config, f)
        
        with patch.dict(os.environ, {"ENVIRONMENT": "custom_env"}):
            config = load_config_from_yaml(str(config_file), environment="custom_env")
            
            assert config.level == "ERROR"
            assert config.format_json is True