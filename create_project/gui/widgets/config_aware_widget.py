# ABOUTME: Base widget class that automatically responds to configuration changes
# ABOUTME: Provides foundation for UI components that need real-time config updates

"""
Configuration-Aware Widget Base Class

Provides a base class for widgets that need to respond to configuration changes
in real-time, ensuring UI stays synchronized with settings.
"""

from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from ...config import ConfigManager, get_config_manager
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ConfigChangeNotifier(QObject):
    """Singleton notifier for configuration changes."""
    
    config_changed = pyqtSignal(str, object)  # path, value
    
    _instance: Optional["ConfigChangeNotifier"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "_initialized"):
            super().__init__()
            self._initialized = True
            self._config_manager: Optional[ConfigManager] = None
    
    def set_config_manager(self, config_manager: ConfigManager) -> None:
        """Set the configuration manager to monitor."""
        self._config_manager = config_manager
        
        # Monkey-patch the set_setting method to emit signals
        original_set_setting = config_manager.set_setting
        
        def patched_set_setting(key: str, value: Any) -> bool:
            result = original_set_setting(key, value)
            if result:
                self.config_changed.emit(key, value)
            return result
        
        config_manager.set_setting = patched_set_setting
    
    def notify_change(self, path: str, value: Any) -> None:
        """Manually notify of a configuration change."""
        self.config_changed.emit(path, value)


class ConfigAwareWidget(QWidget):
    """Base widget that responds to configuration changes."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, parent: Optional[QWidget] = None):
        """Initialize configuration-aware widget.
        
        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config_manager = config_manager or get_config_manager()
        self._config_paths = set()  # Paths this widget is interested in
        
        # Get or create the singleton notifier
        self._notifier = ConfigChangeNotifier()
        self._notifier.set_config_manager(self.config_manager)
        
        # Connect to configuration changes
        self._notifier.config_changed.connect(self._on_config_changed)
    
    def watch_config(self, path: str) -> None:
        """Register interest in a configuration path.
        
        Args:
            path: Configuration path to watch (e.g., "ui.theme", "ai.enabled")
        """
        self._config_paths.add(path)
        logger.debug(f"Widget {self.__class__.__name__} watching config path: {path}")
    
    def unwatch_config(self, path: str) -> None:
        """Remove interest in a configuration path.
        
        Args:
            path: Configuration path to stop watching
        """
        self._config_paths.discard(path)
    
    def _on_config_changed(self, path: str, value: Any) -> None:
        """Handle configuration change notification.
        
        Args:
            path: Configuration path that changed
            value: New value
        """
        # Check if this widget is interested in this path
        if path in self._config_paths:
            logger.debug(
                f"Widget {self.__class__.__name__} received config change",
                path=path,
                value=value
            )
            self.on_config_changed(path, value)
        
        # Also check for parent paths (e.g., "ai" when watching "ai.enabled")
        for watched_path in self._config_paths:
            if path.startswith(watched_path + ".") or watched_path.startswith(path + "."):
                logger.debug(
                    f"Widget {self.__class__.__name__} received related config change",
                    path=path,
                    watched=watched_path,
                    value=value
                )
                self.on_config_changed(path, value)
    
    def on_config_changed(self, path: str, value: Any) -> None:
        """Override this method to handle configuration changes.
        
        Args:
            path: Configuration path that changed
            value: New value
        """
        pass  # Override in subclasses
    
    def get_config_value(self, path: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            path: Configuration path
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        return self.config_manager.get_setting(path, default)
    
    def set_config_value(self, path: str, value: Any) -> bool:
        """Set a configuration value.
        
        Args:
            path: Configuration path
            value: New value
            
        Returns:
            True if successful
        """
        return self.config_manager.set_setting(path, value)