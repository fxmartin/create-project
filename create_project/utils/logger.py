# ABOUTME: Logging infrastructure module providing structured logging capabilities
# ABOUTME: Supports environment-specific configuration, log rotation, and colored console output

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any, Optional

import colorlog
import structlog
import yaml


class LoggerConfig:
    """Configuration class for logging setup."""

    def __init__(
        self,
        level: str = "INFO",
        format_json: bool = False,
        include_context: bool = True,
        log_dir: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 30,
        console_colors: bool = True,
    ):
        """Initialize logger configuration.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_json: Whether to use JSON formatting
            include_context: Whether to include contextual information
            log_dir: Directory for log files (default: project_root/logs)
            max_bytes: Maximum size per log file in bytes
            backup_count: Number of backup log files to keep
            console_colors: Whether to use colored console output
        """
        self.level = level.upper()
        self.format_json = format_json
        self.include_context = include_context
        self.log_dir = Path(log_dir) if log_dir else self._get_default_log_dir()
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console_colors = console_colors

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_log_dir(self) -> Path:
        """Get the default log directory path."""
        # Find project root by looking for pyproject.toml
        current_dir = Path(__file__).parent
        while current_dir != current_dir.parent:
            if (current_dir / "pyproject.toml").exists():
                return current_dir / "logs"
            current_dir = current_dir.parent

        # Fallback to logs directory relative to this file
        return Path(__file__).parent.parent.parent / "logs"


class StructuredLogger:
    """Structured logger with support for contextual information."""

    def __init__(self, name: str, config: LoggerConfig):
        """Initialize structured logger.

        Args:
            name: Logger name (typically module or component name)
            config: Logger configuration
        """
        self.name = name
        self.config = config
        self._logger = self._setup_logger()

        # Set up structlog if context is enabled
        if config.include_context:
            self._setup_structlog()

    def _setup_logger(self) -> logging.Logger:
        """Set up the underlying Python logger."""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.config.level))

        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()

        # Add console handler
        console_handler = self._create_console_handler()
        logger.addHandler(console_handler)

        # Add file handlers
        file_handlers = self._create_file_handlers()
        for handler in file_handlers:
            logger.addHandler(handler)

        return logger

    def _create_console_handler(self) -> logging.Handler:
        """Create console handler with optional coloring."""
        handler = logging.StreamHandler(sys.stdout)

        if self.config.console_colors and sys.stdout.isatty():
            # Use colorlog for colored console output
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white",
                },
            )
        else:
            # Use plain formatter
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        handler.setFormatter(formatter)
        return handler

    def _create_file_handlers(self) -> list[logging.Handler]:
        """Create file handlers for different log levels."""
        handlers = []

        # Main application log (all levels)
        app_handler = logging.handlers.RotatingFileHandler(
            self.config.log_dir / "app.log",
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
        )
        app_formatter = self._get_file_formatter()
        app_handler.setFormatter(app_formatter)
        handlers.append(app_handler)

        # Error log (ERROR and CRITICAL only)
        error_handler = logging.handlers.RotatingFileHandler(
            self.config.log_dir / "error.log",
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(app_formatter)
        handlers.append(error_handler)

        # Debug log (DEBUG and above, only if debug level is enabled)
        if self.config.level == "DEBUG":
            debug_handler = logging.handlers.RotatingFileHandler(
                self.config.log_dir / "debug.log",
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count,
            )
            debug_handler.setFormatter(app_formatter)
            handlers.append(debug_handler)

        return handlers

    def _get_file_formatter(self) -> logging.Formatter:
        """Get formatter for file output."""
        if self.config.format_json:
            # JSON formatter for structured logging
            return logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s", '
                '"module": "%(module)s", "function": "%(funcName)s", '
                '"line": %(lineno)d}'
            )
        else:
            # Human-readable formatter
            return logging.Formatter(
                "%(asctime)s [%(levelname)8s] %(name)s [%(module)s:%(funcName)s:%(lineno)d]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    def _setup_structlog(self) -> None:
        """Set up structlog for structured logging."""
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
        ]

        if self.config.format_json:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(
                structlog.dev.ConsoleRenderer(colors=self.config.console_colors)
            )

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, self.config.level)
            ),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with optional context."""
        if self.config.include_context and kwargs:
            self._logger.debug(message, extra=kwargs)
        else:
            self._logger.debug(message)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with optional context."""
        if self.config.include_context and kwargs:
            self._logger.info(message, extra=kwargs)
        else:
            self._logger.info(message)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with optional context."""
        if self.config.include_context and kwargs:
            self._logger.warning(message, extra=kwargs)
        else:
            self._logger.warning(message)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with optional context."""
        if self.config.include_context and kwargs:
            self._logger.error(message, extra=kwargs)
        else:
            self._logger.error(message)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with optional context."""
        if self.config.include_context and kwargs:
            self._logger.critical(message, extra=kwargs)
        else:
            self._logger.critical(message)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        if self.config.include_context and kwargs:
            self._logger.exception(message, extra=kwargs)
        else:
            self._logger.exception(message)

    def get_structlog_logger(self) -> Any:
        """Get structlog logger for advanced structured logging."""
        if not self.config.include_context:
            raise ValueError("Context logging must be enabled to use structlog")
        return structlog.get_logger(self.name)


# Environment detection
def get_environment() -> str:
    """Detect current environment (development, production, testing)."""
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env in ["development", "dev"]:
        return "development"
    elif env in ["production", "prod"]:
        return "production"
    elif env in ["testing", "test"]:
        return "testing"
    else:
        # Default to development if not specified
        return "development"


# Configuration loading from YAML
def load_config_from_yaml(
    config_file: Optional[str] = None, environment: Optional[str] = None
) -> LoggerConfig:
    """Load logger configuration from YAML file.

    Args:
        config_file: Path to YAML configuration file
        environment: Environment name (development, production, testing)

    Returns:
        LoggerConfig instance loaded from YAML
    """
    if environment is None:
        environment = get_environment()

    if config_file is None:
        # Default to config/logging.yaml in project root
        config_file = Path(__file__).parent.parent / "config" / "logging.yaml"

    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Error loading YAML configuration: {e}")

    if environment not in config_data:
        raise ValueError(f"Environment '{environment}' not found in configuration")

    env_config = config_data[environment]

    # Extract configuration values with defaults
    return LoggerConfig(
        level=env_config.get("level", "INFO"),
        format_json=env_config.get("format_json", False),
        include_context=env_config.get("include_context", True),
        max_bytes=env_config.get("max_bytes", 10 * 1024 * 1024),
        backup_count=env_config.get("backup_count", 30),
        console_colors=env_config.get("console_colors", True),
    )


# Default configuration factory
def get_default_config(environment: Optional[str] = None) -> LoggerConfig:
    """Get default logger configuration for the specified environment.

    Attempts to load from YAML configuration first, falls back to hardcoded defaults.

    Args:
        environment: Environment name (development, production, testing)

    Returns:
        LoggerConfig instance with environment-appropriate settings
    """
    if environment is None:
        environment = get_environment()

    # Try to load from YAML configuration first
    try:
        return load_config_from_yaml(environment=environment)
    except (FileNotFoundError, ValueError):
        # Fall back to hardcoded defaults
        pass

    # Hardcoded defaults as fallback
    if environment == "development":
        return LoggerConfig(
            level="DEBUG",
            format_json=False,
            include_context=True,
            console_colors=True,
        )
    elif environment == "production":
        return LoggerConfig(
            level="INFO",
            format_json=True,
            include_context=True,
            console_colors=False,
        )
    elif environment == "testing":
        return LoggerConfig(
            level="WARNING",
            format_json=False,
            include_context=False,
            console_colors=False,
        )
    else:
        raise ValueError(f"Unknown environment: {environment}")


# Global logger instance for quick access
_default_logger: Optional[StructuredLogger] = None


def get_logger(name: str, config: Optional[LoggerConfig] = None) -> StructuredLogger:
    """Get or create a logger instance.

    Args:
        name: Logger name (typically module or component name)
        config: Optional logger configuration (uses default if not provided)

    Returns:
        StructuredLogger instance
    """
    if config is None:
        config = get_default_config()

    return StructuredLogger(name, config)


def init_logging(config: Optional[LoggerConfig] = None) -> None:
    """Initialize logging system with the specified configuration.

    This should be called once at application startup.

    Args:
        config: Optional logger configuration (uses default if not provided)
    """
    global _default_logger

    if config is None:
        config = get_default_config()

    # Create default logger
    _default_logger = StructuredLogger("app", config)

    # Log initialization
    _default_logger.info(
        "Logging system initialized",
        level=config.level,
        environment=get_environment(),
        log_dir=str(config.log_dir),
        format_json=config.format_json,
    )


def get_default_logger() -> StructuredLogger:
    """Get the default application logger.

    Returns:
        Default StructuredLogger instance

    Raises:
        RuntimeError: If logging hasn't been initialized
    """
    if _default_logger is None:
        raise RuntimeError("Logging not initialized. Call init_logging() first.")
    return _default_logger
