# ABOUTME: Configuration module initialization
# ABOUTME: Exposes configuration management functionality for the Python Project Creator

"""
Configuration Management Module

Provides centralized configuration handling including:
- JSON configuration files (settings.json, defaults.json)
- Environment variable integration
- Configuration validation and schemas
- User preference persistence
- Secure handling of sensitive data
"""

from .config_manager import ConfigManager, get_config_manager, get_config, get_setting, set_setting
from .models import Config, AppConfig, UIConfig, TemplateConfig, OllamaConfig, LoggingConfig

__all__ = [
    'ConfigManager',
    'get_config_manager',
    'get_config',
    'get_setting',
    'set_setting',
    'Config',
    'AppConfig', 
    'UIConfig',
    'TemplateConfig',
    'OllamaConfig',
    'LoggingConfig'
]
