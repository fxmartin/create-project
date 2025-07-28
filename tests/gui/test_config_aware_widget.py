# ABOUTME: Test suite for the configuration-aware widget base class
# ABOUTME: Validates real-time configuration change handling in UI components

"""Test the ConfigAwareWidget base class."""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from create_project.gui.widgets.config_aware_widget import (
    ConfigAwareWidget,
    ConfigChangeNotifier,
)


@pytest.fixture
def app(qtbot):
    """Create QApplication for testing."""
    return QApplication.instance()


class TestConfigChangeNotifier:
    """Test the ConfigChangeNotifier singleton."""
    
    def test_singleton_behavior(self):
        """Test that ConfigChangeNotifier is a singleton."""
        notifier1 = ConfigChangeNotifier()
        notifier2 = ConfigChangeNotifier()
        
        assert notifier1 is notifier2
    
    def test_set_config_manager(self):
        """Test setting the configuration manager."""
        notifier = ConfigChangeNotifier()
        mock_config_manager = MagicMock()
        
        # Store original method
        original_set_setting = mock_config_manager.set_setting
        original_set_setting.return_value = True
        
        notifier.set_config_manager(mock_config_manager)
        
        # Test that set_setting is patched
        mock_config_manager.set_setting("test.key", "test_value")
        original_set_setting.assert_called_with("test.key", "test_value")
    
    def test_manual_notify(self, qtbot):
        """Test manual notification of changes."""
        notifier = ConfigChangeNotifier()
        
        # Connect a test slot
        received_signals = []
        notifier.config_changed.connect(lambda path, value: received_signals.append((path, value)))
        
        # Manually notify
        notifier.notify_change("test.path", "test_value")
        
        assert len(received_signals) == 1
        assert received_signals[0] == ("test.path", "test_value")


class TestConfigAwareWidget:
    """Test the ConfigAwareWidget base class."""
    
    def test_initialization(self, qtbot):
        """Test widget initialization."""
        mock_config_manager = MagicMock()
        widget = ConfigAwareWidget(config_manager=mock_config_manager)
        qtbot.addWidget(widget)
        
        assert widget.config_manager == mock_config_manager
        assert len(widget._config_paths) == 0
    
    def test_watch_unwatch_config(self, qtbot):
        """Test watching and unwatching configuration paths."""
        widget = ConfigAwareWidget()
        qtbot.addWidget(widget)
        
        # Watch paths
        widget.watch_config("ui.theme")
        widget.watch_config("ai.enabled")
        
        assert "ui.theme" in widget._config_paths
        assert "ai.enabled" in widget._config_paths
        
        # Unwatch path
        widget.unwatch_config("ui.theme")
        
        assert "ui.theme" not in widget._config_paths
        assert "ai.enabled" in widget._config_paths
    
    def test_config_change_notification(self, qtbot):
        """Test receiving configuration change notifications."""
        # Create a test widget that tracks changes
        class TestWidget(ConfigAwareWidget):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.changes_received = []
            
            def on_config_changed(self, path: str, value):
                self.changes_received.append((path, value))
        
        widget = TestWidget()
        qtbot.addWidget(widget)
        
        # Watch some paths
        widget.watch_config("ui.theme")
        widget.watch_config("ai.enabled")
        
        # Simulate configuration changes
        widget._notifier.notify_change("ui.theme", "dark")
        widget._notifier.notify_change("ai.enabled", False)
        widget._notifier.notify_change("unrelated.path", "value")
        
        # Check that only watched paths triggered callbacks
        assert len(widget.changes_received) == 2
        assert ("ui.theme", "dark") in widget.changes_received
        assert ("ai.enabled", False) in widget.changes_received
        assert ("unrelated.path", "value") not in widget.changes_received
    
    def test_hierarchical_path_watching(self, qtbot):
        """Test watching parent/child paths."""
        class TestWidget(ConfigAwareWidget):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.changes_received = []
            
            def on_config_changed(self, path: str, value):
                self.changes_received.append((path, value))
        
        widget = TestWidget()
        qtbot.addWidget(widget)
        
        # Watch parent path
        widget.watch_config("ai")
        
        # Changes to child paths should be received
        widget._notifier.notify_change("ai.enabled", True)
        widget._notifier.notify_change("ai.timeout", 30)
        
        assert len(widget.changes_received) == 2
        assert any(path == "ai.enabled" for path, _ in widget.changes_received)
        assert any(path == "ai.timeout" for path, _ in widget.changes_received)
    
    def test_get_set_config_value(self, qtbot):
        """Test getting and setting configuration values."""
        mock_config_manager = MagicMock()
        mock_config_manager.get_setting.return_value = "test_value"
        mock_config_manager.set_setting.return_value = True
        
        widget = ConfigAwareWidget(config_manager=mock_config_manager)
        qtbot.addWidget(widget)
        
        # Test get
        value = widget.get_config_value("test.path", "default")
        assert value == "test_value"
        mock_config_manager.get_setting.assert_called_with("test.path", "default")
        
        # Test set
        result = widget.set_config_value("test.path", "new_value")
        assert result is True
        mock_config_manager.set_setting.assert_called_with("test.path", "new_value")
    
    def test_exception_handling_in_callback(self, qtbot):
        """Test that exceptions in callbacks don't break the notification system."""
        class BrokenWidget(ConfigAwareWidget):
            def on_config_changed(self, path: str, value):
                raise RuntimeError("Test error")
        
        widget = BrokenWidget()
        qtbot.addWidget(widget)
        
        widget.watch_config("test.path")
        
        # This should not raise an exception
        widget._notifier.notify_change("test.path", "value")
        
        # Widget should still be functional
        assert "test.path" in widget._config_paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])