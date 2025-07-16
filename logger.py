#!/usr/bin/env python3
"""
Enhanced logging utility with colored terminal output and performance optimizations.

This module provides a flexible logging system with:
- Colored console output based on log levels
- Performance optimizations through caching
- Support for different log levels via environment variables
- Terminal detection for color support

Author: FX
Email: mail@fxmartin.me
"""

import logging
import os
import sys
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Cache log level mappings for performance
_LOG_LEVEL_CACHE = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Cache environment variables
_ENV_LOG_LEVEL = None

def _get_env_log_level():
    """Get cached environment log level"""
    global _ENV_LOG_LEVEL
    if _ENV_LOG_LEVEL is None:
        _ENV_LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    return _ENV_LOG_LEVEL

def _is_terminal():
    """Check if output is a terminal for color support"""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


class ColoredFormatter(logging.Formatter):
    """Custom formatter with terminal colors for different log levels"""
    
    __slots__ = ('_colors_enabled', '_color_map')
    
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self._colors_enabled = _is_terminal()
        
        # Pre-formatted color strings for performance
        if self._colors_enabled:
            self._color_map = {
                'DEBUG': '\033[36mDEBUG\033[0m',      # Cyan
                'INFO': '\033[32mINFO\033[0m',        # Green
                'WARNING': '\033[33mWARNING\033[0m',  # Yellow
                'ERROR': '\033[31mERROR\033[0m',      # Red
                'CRITICAL': '\033[91mCRITICAL\033[0m' # Bright Red
            }
        else:
            self._color_map = {}
    
    def format(self, record):
        if self._colors_enabled and record.levelname in self._color_map:
            record.levelname = self._color_map[record.levelname]
        return super().format(record)


class Logger:
    """Enhanced logging utility with colored terminal output"""
    
    __slots__ = ('logger', '_initialized')
    
    def __init__(self, name: str = "TextRewriter", level: str | None = None):
        self.logger = logging.getLogger(name)
        self._initialized = False
        self._setup_logger(level)
    
    def _setup_logger(self, level: str | None):
        """Setup logger with optimized initialization"""
        if self._initialized:
            return
            
        # Only clear handlers if they exist to avoid unnecessary work
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Get log level efficiently
        if level:
            log_level = _LOG_LEVEL_CACHE.get(level.upper(), logging.INFO)
        else:
            env_level = _get_env_log_level()
            log_level = _LOG_LEVEL_CACHE.get(env_level, logging.INFO)
        
        self.logger.setLevel(log_level)
        
        # Create console handler with colored formatter
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        formatter = ColoredFormatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self._initialized = True
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warn(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def warning(self, message: str):
        """Log warning message (alias for warn)"""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Log error message with optional exception info"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = False):
        """Log critical message with optional exception info"""
        self.logger.critical(message, exc_info=exc_info)
    
    def exception(self, message: str):
        """Log error message with exception traceback"""
        self.logger.error(message, exc_info=True)
    
    def log(self, level, message: str):
        """Log with specified level"""
        if isinstance(level, LogLevel):
            level = level.value
        
        # Use cached mapping instead of getattr
        log_level = _LOG_LEVEL_CACHE.get(level.upper())
        if log_level is not None:
            self.logger.log(log_level, message)
        else:
            self.logger.info(message)  # Fallback


# Lazy initialization for default logger
_default_logger = None

def _get_default_logger():
    """Get or create default logger instance lazily"""
    global _default_logger
    if _default_logger is None:
        _default_logger = Logger()
    return _default_logger


# Convenience functions using lazy default logger
def log_debug(message: str):
    """Log debug message using default logger"""
    _get_default_logger().debug(message)

def log_info(message: str):
    """Log info message using default logger"""
    _get_default_logger().info(message)

def log_warn(message: str):
    """Log warning message using default logger"""
    _get_default_logger().warn(message)

def log_warning(message: str):
    """Log warning message using default logger"""
    _get_default_logger().warning(message)

def log_error(message: str):
    """Log error message using default logger"""
    _get_default_logger().error(message)

def log_critical(message: str):
    """Log critical message using default logger"""
    _get_default_logger().critical(message)

def log(level, message: str):
    """Log with specified level using default logger"""
    _get_default_logger().log(level, message)