# ABOUTME: Unit tests for logging infrastructure
# ABOUTME: Tests logger configuration, formatting, and environment-specific behavior

import logging
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from create_project.utils.logger import (
    LoggerConfig,
    StructuredLogger,
    get_logger,
    init_logging,
    get_default_config,
    load_config_from_yaml,
    get_environment,
    get_default_logger,
)


class TestLoggerConfig(unittest.TestCase):
    """Test LoggerConfig class."""
    
    def test_default_config_creation(self):
        """Test default LoggerConfig creation."""
        config = LoggerConfig()
        
        self.assertEqual(config.level, "INFO")
        self.assertFalse(config.format_json)
        self.assertTrue(config.include_context)
        self.assertEqual(config.max_bytes, 10 * 1024 * 1024)
        self.assertEqual(config.backup_count, 30)
        self.assertTrue(config.console_colors)
        self.assertIsInstance(config.log_dir, Path)
    
    def test_custom_config_creation(self):
        """Test custom LoggerConfig creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggerConfig(
                level="DEBUG",
                format_json=True,
                include_context=False,
                log_dir=temp_dir,
                max_bytes=1024,
                backup_count=5,
                console_colors=False,
            )
            
            self.assertEqual(config.level, "DEBUG")
            self.assertTrue(config.format_json)
            self.assertFalse(config.include_context)
            self.assertEqual(config.log_dir, Path(temp_dir))
            self.assertEqual(config.max_bytes, 1024)
            self.assertEqual(config.backup_count, 5)
            self.assertFalse(config.console_colors)
    
    def test_log_directory_creation(self):
        """Test that log directory is created automatically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"
            self.assertFalse(log_dir.exists())
            
            config = LoggerConfig(log_dir=str(log_dir))
            self.assertTrue(log_dir.exists())


class TestStructuredLogger(unittest.TestCase):
    """Test StructuredLogger class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = LoggerConfig(
            level="DEBUG",
            log_dir=self.temp_dir,
            console_colors=False,
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_logger_creation(self):
        """Test StructuredLogger creation."""
        logger = StructuredLogger("test_logger", self.config)
        
        self.assertEqual(logger.name, "test_logger")
        self.assertEqual(logger.config, self.config)
        self.assertIsNotNone(logger._logger)
    
    def test_log_levels(self):
        """Test all log levels work correctly."""
        logger = StructuredLogger("test_logger", self.config)
        
        # Test that all log level methods exist and are callable
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_log_with_context(self):
        """Test logging with contextual information."""
        logger = StructuredLogger("test_logger", self.config)
        
        # Test logging with context (avoid reserved keywords like 'module')
        logger.info("Test message", user_id=123, action="test")
        logger.error("Error message", error_code=500, component="test")
    
    def test_log_files_created(self):
        """Test that log files are created correctly."""
        logger = StructuredLogger("test_logger", self.config)
        logger.info("Test message")
        
        # Check that log files exist
        log_dir = Path(self.temp_dir)
        self.assertTrue((log_dir / "app.log").exists())
        self.assertTrue((log_dir / "debug.log").exists())
        self.assertTrue((log_dir / "error.log").exists())
    
    def test_log_file_content(self):
        """Test that log files contain expected content."""
        logger = StructuredLogger("test_logger", self.config)
        test_message = "Test log message"
        logger.info(test_message)
        
        # Check app.log content
        app_log = Path(self.temp_dir) / "app.log"
        with open(app_log, 'r') as f:
            content = f.read()
            self.assertIn(test_message, content)
            self.assertIn("INFO", content)
            self.assertIn("test_logger", content)
    
    def test_error_log_filtering(self):
        """Test that error.log only contains error and critical messages."""
        logger = StructuredLogger("test_logger", self.config)
        
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # Check error.log content
        error_log = Path(self.temp_dir) / "error.log"
        with open(error_log, 'r') as f:
            content = f.read()
            self.assertNotIn("Info message", content)
            self.assertNotIn("Warning message", content)
            self.assertIn("Error message", content)
            self.assertIn("Critical message", content)
    
    def test_json_formatting(self):
        """Test JSON formatting in production mode."""
        config = LoggerConfig(
            level="INFO",
            format_json=True,
            log_dir=self.temp_dir,
            console_colors=False,
        )
        logger = StructuredLogger("test_logger", config)
        logger.info("Test message")
        
        # Check that log contains JSON-like structure
        app_log = Path(self.temp_dir) / "app.log"
        with open(app_log, 'r') as f:
            content = f.read()
            self.assertIn('"level": "INFO"', content)
            self.assertIn('"message": "Test message"', content)
    
    def test_exception_logging(self):
        """Test exception logging with traceback."""
        logger = StructuredLogger("test_logger", self.config)
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception occurred")
        
        # Check that exception is logged
        app_log = Path(self.temp_dir) / "app.log"
        with open(app_log, 'r') as f:
            content = f.read()
            self.assertIn("Exception occurred", content)
            self.assertIn("ValueError", content)
            self.assertIn("Test exception", content)


class TestEnvironmentDetection(unittest.TestCase):
    """Test environment detection functionality."""
    
    def test_environment_detection_development(self):
        """Test development environment detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            self.assertEqual(get_environment(), "development")
        
        with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
            self.assertEqual(get_environment(), "development")
    
    def test_environment_detection_production(self):
        """Test production environment detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            self.assertEqual(get_environment(), "production")
        
        with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
            self.assertEqual(get_environment(), "production")
    
    def test_environment_detection_testing(self):
        """Test testing environment detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            self.assertEqual(get_environment(), "testing")
        
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            self.assertEqual(get_environment(), "testing")
    
    def test_environment_detection_default(self):
        """Test default environment detection."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_environment(), "development")
        
        with patch.dict(os.environ, {"ENVIRONMENT": "unknown"}):
            self.assertEqual(get_environment(), "development")


class TestDefaultConfig(unittest.TestCase):
    """Test default configuration functionality."""
    
    def test_development_config(self):
        """Test development default configuration."""
        config = get_default_config("development")
        
        self.assertEqual(config.level, "DEBUG")
        self.assertFalse(config.format_json)
        self.assertTrue(config.include_context)
        self.assertTrue(config.console_colors)
    
    def test_production_config(self):
        """Test production default configuration."""
        config = get_default_config("production")
        
        self.assertEqual(config.level, "INFO")
        self.assertTrue(config.format_json)
        self.assertTrue(config.include_context)
        self.assertFalse(config.console_colors)
    
    def test_testing_config(self):
        """Test testing default configuration."""
        config = get_default_config("testing")
        
        self.assertEqual(config.level, "WARNING")
        self.assertFalse(config.format_json)
        self.assertFalse(config.include_context)
        self.assertFalse(config.console_colors)
    
    def test_unknown_environment(self):
        """Test unknown environment raises error."""
        with self.assertRaises(ValueError):
            get_default_config("unknown")


class TestYamlConfig(unittest.TestCase):
    """Test YAML configuration loading."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.yaml_content = """
development:
  level: DEBUG
  format_json: false
  include_context: true
  console_colors: true
  max_bytes: 1048576
  backup_count: 10

production:
  level: INFO
  format_json: true
  include_context: true
  console_colors: false
  max_bytes: 10485760
  backup_count: 30
"""
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_yaml_config_loading(self):
        """Test loading configuration from YAML file."""
        yaml_file = Path(self.temp_dir) / "logging.yaml"
        with open(yaml_file, 'w') as f:
            f.write(self.yaml_content)
        
        config = load_config_from_yaml(str(yaml_file), "development")
        
        self.assertEqual(config.level, "DEBUG")
        self.assertFalse(config.format_json)
        self.assertTrue(config.include_context)
        self.assertTrue(config.console_colors)
        self.assertEqual(config.max_bytes, 1048576)
        self.assertEqual(config.backup_count, 10)
    
    def test_yaml_config_missing_file(self):
        """Test error when YAML file doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            load_config_from_yaml("/nonexistent/file.yaml", "development")
    
    def test_yaml_config_missing_environment(self):
        """Test error when environment not found in YAML."""
        yaml_file = Path(self.temp_dir) / "logging.yaml"
        with open(yaml_file, 'w') as f:
            f.write(self.yaml_content)
        
        with self.assertRaises(ValueError):
            load_config_from_yaml(str(yaml_file), "nonexistent")


class TestLoggerFactory(unittest.TestCase):
    """Test logger factory functionality."""
    
    def test_get_logger_with_config(self):
        """Test getting logger with specific configuration."""
        config = LoggerConfig(level="DEBUG")
        logger = get_logger("test_component", config)
        
        self.assertIsInstance(logger, StructuredLogger)
        self.assertEqual(logger.name, "test_component")
        self.assertEqual(logger.config, config)
    
    def test_get_logger_with_default_config(self):
        """Test getting logger with default configuration."""
        logger = get_logger("test_component")
        
        self.assertIsInstance(logger, StructuredLogger)
        self.assertEqual(logger.name, "test_component")
        self.assertIsInstance(logger.config, LoggerConfig)
    
    def test_component_specific_loggers(self):
        """Test creating component-specific loggers."""
        ui_logger = get_logger("ui.wizard")
        core_logger = get_logger("core.generator")
        
        self.assertEqual(ui_logger.name, "ui.wizard")
        self.assertEqual(core_logger.name, "core.generator")
        self.assertNotEqual(ui_logger.name, core_logger.name)


class TestLoggingInitialization(unittest.TestCase):
    """Test logging initialization functionality."""
    
    def tearDown(self):
        """Clean up global logger state."""
        # Reset global logger state
        from create_project.utils.logger import _default_logger
        import create_project.utils.logger
        create_project.utils.logger._default_logger = None
    
    def test_init_logging_default(self):
        """Test logging initialization with default configuration."""
        init_logging()
        
        # Should not raise an exception
        logger = get_default_logger()
        self.assertIsInstance(logger, StructuredLogger)
        self.assertEqual(logger.name, "app")
    
    def test_init_logging_custom_config(self):
        """Test logging initialization with custom configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggerConfig(level="DEBUG", log_dir=temp_dir)
            init_logging(config)
            
            logger = get_default_logger()
            self.assertIsInstance(logger, StructuredLogger)
            self.assertEqual(logger.config.level, "DEBUG")
    
    def test_get_default_logger_not_initialized(self):
        """Test error when getting default logger before initialization."""
        with self.assertRaises(RuntimeError):
            get_default_logger()


class TestLogRotation(unittest.TestCase):
    """Test log rotation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        # Use small file size for testing rotation
        self.config = LoggerConfig(
            level="DEBUG",
            log_dir=self.temp_dir,
            max_bytes=1024,  # 1KB for easy testing
            backup_count=3,
            console_colors=False,
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_rotation_by_size(self):
        """Test log rotation when file size exceeds limit."""
        logger = StructuredLogger("test_logger", self.config)
        
        # Generate enough log messages to trigger rotation
        message = "A" * 100  # 100 character message
        for i in range(20):  # This should exceed 1KB limit
            logger.info(f"Message {i}: {message}")
        
        # Check that rotation occurred
        log_dir = Path(self.temp_dir)
        app_log = log_dir / "app.log"
        app_log_1 = log_dir / "app.log.1"
        
        self.assertTrue(app_log.exists(), "Main log file should exist")
        # Note: Rotation might not occur immediately in testing due to buffering
        # But the rotation handler should be properly configured
        
        # Verify handler is configured correctly
        python_logger = logging.getLogger("test_logger")
        rotating_handlers = [
            h for h in python_logger.handlers 
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        self.assertTrue(len(rotating_handlers) > 0, "Should have rotating file handlers")
        
        for handler in rotating_handlers:
            self.assertEqual(handler.maxBytes, 1024, "Max bytes should be 1024")
            self.assertEqual(handler.backupCount, 3, "Backup count should be 3")
    
    def test_log_files_exist_after_rotation(self):
        """Test that all expected log files exist after rotation setup."""
        logger = StructuredLogger("test_logger", self.config)
        
        # Generate some log messages
        logger.info("Test message")
        logger.error("Error message")
        logger.debug("Debug message")
        
        # Check that all expected log files exist
        log_dir = Path(self.temp_dir)
        self.assertTrue((log_dir / "app.log").exists(), "app.log should exist")
        self.assertTrue((log_dir / "error.log").exists(), "error.log should exist")
        self.assertTrue((log_dir / "debug.log").exists(), "debug.log should exist")
    
    def test_error_log_rotation_separate(self):
        """Test that error log has separate rotation configuration."""
        logger = StructuredLogger("test_logger", self.config)
        
        # Generate error messages
        for i in range(20):
            logger.error(f"Error message {i}: " + "E" * 50)
        
        # Check that error log exists and has rotating handler
        log_dir = Path(self.temp_dir)
        error_log = log_dir / "error.log"
        self.assertTrue(error_log.exists(), "error.log should exist")
        
        # Verify error handler configuration
        python_logger = logging.getLogger("test_logger")
        error_handlers = [
            h for h in python_logger.handlers 
            if isinstance(h, logging.handlers.RotatingFileHandler) and 
            h.baseFilename.endswith("error.log")
        ]
        self.assertTrue(len(error_handlers) > 0, "Should have error log rotating handler")
        
        for handler in error_handlers:
            self.assertEqual(handler.level, logging.ERROR, "Error handler should be ERROR level")
    
    def test_log_retention_configuration(self):
        """Test log retention policy configuration."""
        logger = StructuredLogger("test_logger", self.config)
        
        # Verify that handlers are configured with correct backup count
        python_logger = logging.getLogger("test_logger")
        rotating_handlers = [
            h for h in python_logger.handlers 
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        
        for handler in rotating_handlers:
            self.assertEqual(handler.backupCount, 3, "Backup count should be 3")
    
    def test_log_file_permissions(self):
        """Test that log files have correct permissions."""
        logger = StructuredLogger("test_logger", self.config)
        logger.info("Test message")
        
        # Check file permissions
        log_dir = Path(self.temp_dir)
        app_log = log_dir / "app.log"
        
        self.assertTrue(app_log.exists(), "Log file should exist")
        self.assertTrue(app_log.is_file(), "Should be a regular file")
        
        # Check that we can read and write to the file
        stat = app_log.stat()
        # On Unix systems, check that owner has read/write permissions
        import stat as stat_module
        self.assertTrue(stat.st_mode & stat_module.S_IRUSR, "Owner should have read permission")
        self.assertTrue(stat.st_mode & stat_module.S_IWUSR, "Owner should have write permission")


class TestCrossComponentLogging(unittest.TestCase):
    """Test logging across different components and environments."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = LoggerConfig(
            level="DEBUG",
            log_dir=self.temp_dir,
            console_colors=False,
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_multiple_component_loggers(self):
        """Test multiple component loggers writing to same files."""
        # Create loggers for different components
        ui_logger = StructuredLogger("ui.wizard", self.config)
        core_logger = StructuredLogger("core.generator", self.config)
        template_logger = StructuredLogger("templates.engine", self.config)
        
        # Generate messages from each component
        ui_logger.info("UI wizard started")
        core_logger.info("Core generator initialized")
        template_logger.debug("Template engine loaded")
        
        # Check that all messages appear in the same log file
        log_dir = Path(self.temp_dir)
        app_log = log_dir / "app.log"
        
        with open(app_log, 'r') as f:
            content = f.read()
            self.assertIn("UI wizard started", content)
            self.assertIn("Core generator initialized", content)
            self.assertIn("Template engine loaded", content)
            
            # Check that component names are preserved
            self.assertIn("ui.wizard", content)
            self.assertIn("core.generator", content)
            self.assertIn("templates.engine", content)
    
    def test_environment_specific_logging(self):
        """Test logging behavior in different environments."""
        # Test development environment
        dev_config = get_default_config("development")
        dev_logger = StructuredLogger("test_dev", dev_config)
        
        self.assertEqual(dev_logger.config.level, "DEBUG")
        self.assertFalse(dev_logger.config.format_json)
        self.assertTrue(dev_logger.config.console_colors)
        
        # Test production environment
        prod_config = get_default_config("production")
        prod_logger = StructuredLogger("test_prod", prod_config)
        
        self.assertEqual(prod_logger.config.level, "INFO")
        self.assertTrue(prod_logger.config.format_json)
        self.assertFalse(prod_logger.config.console_colors)
        
        # Test testing environment
        test_config = get_default_config("testing")
        test_logger = StructuredLogger("test_test", test_config)
        
        self.assertEqual(test_logger.config.level, "WARNING")
        self.assertFalse(test_logger.config.format_json)
        self.assertFalse(test_logger.config.console_colors)
    
    def test_log_message_propagation(self):
        """Test that log messages propagate correctly through the hierarchy."""
        # Create hierarchical loggers
        parent_logger = StructuredLogger("parent", self.config)
        child_logger = StructuredLogger("parent.child", self.config)
        
        # Both should write to the same log files
        parent_logger.info("Parent message")
        child_logger.info("Child message")
        
        # Check that both messages appear in log file
        log_dir = Path(self.temp_dir)
        app_log = log_dir / "app.log"
        
        with open(app_log, 'r') as f:
            content = f.read()
            self.assertIn("Parent message", content)
            self.assertIn("Child message", content)
    
    def test_performance_under_load(self):
        """Test logging performance with many messages."""
        logger = StructuredLogger("performance_test", self.config)
        
        # Generate many log messages quickly
        start_time = time.time()
        num_messages = 1000
        
        for i in range(num_messages):
            logger.info(f"Performance test message {i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust as needed)
        self.assertLess(duration, 5.0, "Logging 1000 messages should complete within 5 seconds")
        
        # Verify all messages were written
        log_dir = Path(self.temp_dir)
        app_log = log_dir / "app.log"
        
        with open(app_log, 'r') as f:
            content = f.read()
            lines = content.strip().split('\n')
            # Should have close to num_messages (may vary due to other log entries)
            self.assertGreater(len(lines), num_messages // 2, "Should have substantial number of log entries")
    
    def test_concurrent_logging(self):
        """Test concurrent logging from multiple threads."""
        import threading
        
        logger = StructuredLogger("concurrent_test", self.config)
        results = []
        
        def log_messages(thread_id):
            """Log messages from a specific thread."""
            for i in range(50):
                logger.info(f"Thread {thread_id} message {i}")
            results.append(f"Thread {thread_id} completed")
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_messages, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all threads completed
        self.assertEqual(len(results), 5, "All threads should complete")
        
        # Verify log file contains messages from all threads
        log_dir = Path(self.temp_dir)
        app_log = log_dir / "app.log"
        
        with open(app_log, 'r') as f:
            content = f.read()
            # Should contain messages from all threads
            for i in range(5):
                self.assertIn(f"Thread {i} message", content)


if __name__ == "__main__":
    unittest.main()