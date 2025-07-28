# ABOUTME: Additional tests for ConfigManager to achieve 100% coverage
# ABOUTME: Focuses on uncovered lines and edge cases not covered in main test file

"""
Additional ConfigManager Tests for Coverage Gaps

Targets specific uncovered lines and edge cases identified by coverage analysis:
- Line 58: Default config path handling
- Lines 75-76: Property access edge cases  
- Lines 113-114: Exception handling in load_config
- Lines 131-168: Advanced save_config scenarios
- Lines 198-208: Environment variable edge cases
- Lines 217-220: JSON loading error scenarios
- Lines 231-236: Config merging edge cases
- Lines 245-248: Nested value setting edge cases
- Lines 257-260: Deep dictionary access
- Lines 282-285: Temporary setting error handling
- Lines 337-340: Validation errors
- Lines 356-413: Environment variable parsing
- Lines 426-451: Complex nested operations
- Lines 495-500: Global function edge cases
- Line 510: Singleton manager edge cases
- Line 524: Setting access edge cases  
- Line 538: Complex configuration scenarios
"""

import json
import os
import tempfile
import threading
import time
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from pydantic import ValidationError

import pytest

from create_project.config.config_manager import (
    ConfigManager,
    ConfigurationError,
    get_config,
    get_config_manager,
    get_setting,
    set_setting,
)
from create_project.config.models import Config


class TestConfigManagerDefaultPath:
    """Test ConfigManager with default path initialization."""
    
    def test_initialization_with_none_path_uses_default(self):
        """Test that None path uses package config directory (line 58).""" 
        # Reset any existing manager instance
        import create_project.config.config_manager as cm
        cm._global_config_manager = None
        
        manager = ConfigManager(None)  # Explicitly pass None
        
        # Should use the default path from the package
        expected_path = Path(__file__).parent.parent.parent / "create_project" / "config"
        assert manager.config_directory.name == "config"
        # Ensure the path resolution worked correctly
        assert manager.config_directory.is_absolute()


class TestPropertyAccessEdgeCases:
    """Test property access under various conditions."""
    
    def test_is_loaded_property_thread_safety(self):
        """Test is_loaded property with thread synchronization (lines 75-76)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            results = []
            
            def check_loaded_status():
                # Check is_loaded multiple times rapidly
                for _ in range(10):
                    status = manager.is_loaded
                    results.append(status)
                    time.sleep(0.001)
            
            # Start multiple threads checking is_loaded
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=check_loaded_status)
                threads.append(thread)
                thread.start()
            
            # Load config in main thread
            time.sleep(0.005)
            manager.load_config()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Results should be consistent (no race conditions)
            assert len(results) == 30


class TestExceptionHandlingInLoadConfig:
    """Test exception handling scenarios in load_config method."""
    
    def test_load_config_pydantic_validation_error(self):
        """Test load_config with Pydantic validation errors (lines 113-114)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create settings file with invalid data that will cause Pydantic error
            settings_file = Path(temp_dir) / "settings.json" 
            invalid_settings = {
                "ui": {
                    "theme": "invalid_theme_value",  # This should cause validation error
                    "window_size": "not_a_list"      # This should also cause validation error
                }
            }
            with open(settings_file, "w") as f:
                json.dump(invalid_settings, f)
            
            manager = ConfigManager(temp_dir)
            
            with pytest.raises(ConfigurationError, match="Failed to load configuration"):
                manager.load_config()
    
    def test_load_config_unexpected_error(self):
        """Test load_config with unexpected system errors (lines 113-114)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # Mock _get_default_config_dict to raise unexpected error
            with patch.object(manager, '_get_default_config_dict', side_effect=RuntimeError("System error")):
                with pytest.raises(ConfigurationError, match="Failed to load configuration"):
                    manager.load_config()


class TestAdvancedSaveConfigScenarios:
    """Test advanced save_config scenarios for full coverage."""
    
    def test_save_config_directory_creation_error(self):
        """Test save_config when directory creation fails (lines 131-168)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            config = manager.load_config()
            
            # Mock mkdir to raise permission error
            with patch.object(Path, 'mkdir', side_effect=PermissionError("Cannot create directory")):
                success = manager.save_config(config)
                assert success is False
    
    def test_save_config_atomic_rename_failure(self):
        """Test save_config when atomic rename fails (lines 131-168)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            config = manager.load_config()
            
            # Mock Path.replace to raise an error
            with patch.object(Path, 'replace', side_effect=OSError("Rename failed")):
                success = manager.save_config(config)
                assert success is False
    
    def test_save_config_temporary_file_cleanup(self):
        """Test temporary file cleanup on errors (lines 131-168)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            config = manager.load_config()
            
            temp_file_path = Path(temp_dir) / "settings.tmp"
            
            # Mock json.dump to raise error after temp file is created
            def mock_json_dump(*args, **kwargs):
                # Create the temp file to test cleanup
                temp_file_path.touch()
                raise ValueError("JSON encoding error")
            
            with patch('json.dump', side_effect=mock_json_dump):
                success = manager.save_config(config)
                assert success is False
                # Temp file should be cleaned up
                assert not temp_file_path.exists()
    
    def test_save_config_internal_state_update(self):
        """Test internal config state update on successful save (lines 131-168)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            original_config = manager.load_config()
            
            # Modify current config directly
            manager._config.ui.theme = "dark"
            
            # Save without passing config parameter (should save current _config)
            success = manager.save_config()
            assert success is True
            
            # Internal config should still be the same object, but with updated values
            assert manager._config is original_config
            assert manager._config.ui.theme == "dark"


class TestEnvironmentVariableEdgeCases:
    """Test environment variable processing edge cases."""
    
    def test_complex_environment_variable_parsing(self):
        """Test complex environment variable parsing scenarios (lines 356-413)."""
        complex_env_vars = {
            "APP_DEBUG": "TRUE",  # Test uppercase boolean
            "UI_THEME": "dark",  # Test string conversion
            "OLLAMA_TIMEOUT": "  45  ",  # Test integer with whitespace
            "APP_AI_TEMPERATURE": "0.75",  # Test float parsing
            "UI_WINDOW_SIZE": "",  # Test empty string handling
            "LOG_FILE_ENABLED": "yes",  # Test alternative boolean format
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, complex_env_vars, clear=False):
                manager = ConfigManager(temp_dir)
                
                # Test the environment variable loading directly
                env_dict = manager._load_environment_variables()
                
                # Verify complex parsing worked
                assert env_dict.get("app", {}).get("debug") is True
                assert env_dict.get("ui", {}).get("theme") == "dark"
                assert env_dict.get("ollama", {}).get("timeout") == 45
                assert env_dict.get("ai", {}).get("temperature") == 0.75
    
    def test_environment_variable_type_conversion_edge_cases(self):
        """Test edge cases in environment variable type conversion (lines 356-413)."""
        edge_case_vars = {
            "APP_AI_PREFERRED_MODELS": "model1,model2,model3",  # Test list parsing
            "UI_WINDOW_WIDTH": "1920",   # Test width setting
            "UI_WINDOW_HEIGHT": "1080",  # Test height setting  
            "OLLAMA_ENABLE_CACHE": "false",  # Test boolean false
            "LOG_MAX_FILES": "1",  # Test minimum valid integer
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, edge_case_vars, clear=False):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()
                
                # Verify all conversions worked correctly
                assert config.ai.preferred_models == ["model1", "model2", "model3"]
                assert config.ui.window_size[0] == 1920
                assert config.ui.window_size[1] == 1080
                assert config.ollama.enable_cache is False
                assert config.logging.max_files == 1


class TestJSONLoadingErrorScenarios:
    """Test JSON file loading error scenarios."""
    
    def test_load_json_file_encoding_error(self):
        """Test JSON loading with encoding errors (lines 217-220)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create file with invalid encoding
            settings_file = Path(temp_dir) / "settings.json" 
            with open(settings_file, "wb") as f:
                f.write(b'\xff\xfe{"ui": {"theme": "dark"}}')  # Invalid UTF-8 BOM
            
            manager = ConfigManager(temp_dir)
            
            with pytest.raises(ConfigurationError, match="Cannot read"):
                manager.load_config()
    
    def test_load_json_file_permission_denied(self):
        """Test JSON loading with permission errors (lines 217-220)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text('{"ui": {"theme": "dark"}}')
            settings_file.chmod(0o000)  # No permissions
            
            manager = ConfigManager(temp_dir)
            
            try:
                with pytest.raises(ConfigurationError, match="Cannot read"):
                    manager.load_config()
            finally:
                settings_file.chmod(0o644)  # Restore for cleanup


class TestConfigMergingEdgeCases:
    """Test configuration merging edge cases."""
    
    def test_merge_config_dicts_none_values(self):
        """Test merging dictionaries with None values (lines 231-236)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            base_dict = {"ui": {"theme": "light", "window_size": [800, 600]}}
            override_dict = {"ui": {"theme": None, "new_field": "value"}}
            
            result = manager._merge_config_dicts(base_dict, override_dict)
            
            # None values should override existing values
            assert result["ui"]["theme"] is None
            assert result["ui"]["new_field"] == "value"
            assert result["ui"]["window_size"] == [800, 600]  # Should remain
    
    def test_merge_config_dicts_deep_nesting(self):
        """Test merging deeply nested dictionaries (lines 231-236)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            base_dict = {
                "level1": {
                    "level2": {
                        "level3": {
                            "value1": "base",
                            "value2": "base"
                        }
                    }
                }
            }
            
            override_dict = {
                "level1": {
                    "level2": { 
                        "level3": {
                            "value1": "override",
                            "value3": "new"
                        }
                    }
                }
            }
            
            result = manager._merge_config_dicts(base_dict, override_dict)
            
            assert result["level1"]["level2"]["level3"]["value1"] == "override"
            assert result["level1"]["level2"]["level3"]["value2"] == "base"
            assert result["level1"]["level2"]["level3"]["value3"] == "new"


class TestNestedValueSettingEdgeCases:
    """Test nested value setting edge cases."""
    
    def test_set_nested_dict_value_create_path(self):
        """Test creating nested paths in dictionaries (lines 245-248)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            config_dict = {}
            key_path = ("deep", "nested", "path", "value")
            
            manager._set_nested_dict_value(config_dict, key_path, "test_value")
            
            assert config_dict["deep"]["nested"]["path"]["value"] == "test_value"
    
    def test_set_nested_dict_value_override_existing(self):
        """Test overriding existing nested values (lines 245-248)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            config_dict = {"existing": {"path": {"value": "old"}}}
            key_path = ("existing", "path", "value")
            
            manager._set_nested_dict_value(config_dict, key_path, "new")
            
            assert config_dict["existing"]["path"]["value"] == "new"


class TestDeepDictionaryAccess:
    """Test deep dictionary access scenarios."""
    
    def test_get_setting_missing_intermediate(self):
        """Test getting settings with missing intermediate keys (lines 257-260)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()
            
            # Test missing intermediate key
            result = manager.get_setting("nonexistent.missing.value", "default")
            assert result == "default"
            
            # Test existing path
            result = manager.get_setting("ui.theme", "default")
            assert result == "system"  # Default theme value
    
    def test_get_setting_empty_path(self):
        """Test getting settings with empty path (lines 257-260)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()
            
            # Test empty string path
            result = manager.get_setting("", "default")
            assert result == "default"


class TestTemporarySettingErrorHandling:
    """Test temporary setting context manager error handling."""
    
    def test_temporary_setting_with_set_error(self):
        """Test temporary setting when setting fails (lines 282-285)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()
            
            # Mock set_setting to fail
            with patch.object(manager, 'set_setting', return_value=False):
                # Should not raise error, but should not change value
                original_value = manager.get_setting("ui.theme")
                
                try:
                    with manager.temporary_setting("ui.theme", "dark"):
                        # Inside context, value might not have changed due to set failure
                        pass
                except Exception:
                    # Context manager should handle errors gracefully
                    pass
                
                # Value should be restored (or remain unchanged)
                final_value = manager.get_setting("ui.theme")
                assert final_value == original_value
    
    def test_temporary_setting_restore_error(self):
        """Test temporary setting when restore fails (lines 282-285)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            manager.load_config()
            
            original_value = manager.get_setting("ui.theme")
            
            def failing_set_setting(key, value):
                if value == original_value:  # Fail only on restore
                    return False
                return True
            
            with patch.object(manager, 'set_setting', side_effect=failing_set_setting):
                try:
                    with manager.temporary_setting("ui.theme", "dark"):
                        pass  # Should handle restore failure gracefully
                except Exception as e:
                    # Should not propagate restoration errors
                    pytest.fail(f"Temporary setting context manager should handle errors: {e}")


class TestValidationErrors:
    """Test configuration validation error scenarios."""
    
    def test_config_validation_with_invalid_model_data(self):
        """Test Config creation with invalid model data (lines 337-340)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # Create invalid config data that will fail Pydantic validation
            invalid_data = {
                "ui": {
                    "theme": 123,  # Should be string
                    "window_size": "invalid"  # Should be list
                },
                "ollama": {
                    "timeout": "not_a_number"  # Should be integer
                }
            }
            
            with pytest.raises(ValidationError):
                Config(**invalid_data)


class TestGlobalFunctionEdgeCases:
    """Test global function edge cases."""
    
    def test_global_functions_with_manager_reset(self):
        """Test global functions when manager is reset (lines 495-500)."""
        # Reset global manager
        import create_project.config.config_manager as cm
        original_manager = cm._global_config_manager
        cm._global_config_manager = None
        
        try:
            # Should create new manager instance
            manager = get_config_manager()
            assert manager is not None
            
            # Should return same instance on subsequent calls
            manager2 = get_config_manager()
            assert manager is manager2
            
            # Global config function should work
            config = get_config()
            assert isinstance(config, Config)
            
        finally:
            # Restore original manager
            cm._global_config_manager = original_manager
    
    def test_get_setting_with_auto_loading(self):
        """Test get_setting with automatic config loading (line 524)."""
        # Reset global manager to test auto-loading
        import create_project.config.config_manager as cm
        original_manager = cm._global_config_manager
        cm._global_config_manager = None
        
        try:
            # Should auto-load configuration
            value = get_setting("ui.theme", "default")
            assert value in ["system", "light", "dark", "default"]
            
        finally:
            # Restore original manager
            cm._global_config_manager = original_manager
    
    def test_set_setting_with_auto_loading(self):
        """Test set_setting with automatic config loading (line 524)."""
        # Reset global manager to test auto-loading
        import create_project.config.config_manager as cm
        original_manager = cm._global_config_manager
        cm._global_config_manager = None
        
        try:
            # Should auto-load and set
            success = set_setting("ui.theme", "dark")
            assert success is True
            
            # Verify setting was applied
            value = get_setting("ui.theme")
            assert value == "dark"
            
        finally:
            # Restore original manager
            cm._global_config_manager = original_manager


class TestComplexConfigurationScenarios:
    """Test complex configuration scenarios."""
    
    def test_complex_nested_environment_override(self):
        """Test complex nested environment variable overrides (line 538)."""
        complex_env_vars = {
            "APP_DEBUG": "true",
            "UI_THEME": "dark",
            "UI_WINDOW_WIDTH": "1920",
            "UI_WINDOW_HEIGHT": "1080", 
            "OLLAMA_API_URL": "http://custom.ollama.com:11434",
            "OLLAMA_TIMEOUT": "60",
            "OLLAMA_ENABLE_CACHE": "false",
            "APP_AI_TEMPERATURE": "0.8",
            "APP_AI_TOP_P": "0.95",
            "APP_AI_PREFERRED_MODELS": "llama3,codellama,mistral,gemma",
            "LOG_LEVEL": "DEBUG",
            "LOG_FILE_ENABLED": "true",
            "LOG_MAX_FILES": "15",
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create complex defaults file
            defaults_file = Path(temp_dir) / "defaults.json"
            defaults_data = {
                "app": {"debug": False, "version": "1.0.0"},
                "ui": {"theme": "system", "window_size": [800, 600]},
                "ollama": {"api_url": "http://localhost:11434", "timeout": 30},
                "ai": {"temperature": 0.7, "top_p": 0.9, "preferred_models": []},
                "logging": {"level": "INFO", "file_enabled": False, "max_files": 5}
            }
            with open(defaults_file, "w") as f:
                json.dump(defaults_data, f)
            
            # Create complex settings file
            settings_file = Path(temp_dir) / "settings.json"
            settings_data = {
                "ui": {"theme": "light"},  # Should be overridden by env var
                "ollama": {"timeout": 45},  # Should be overridden by env var
                "logging": {"max_files": 10}  # Should be overridden by env var
            }
            with open(settings_file, "w") as f:
                json.dump(settings_data, f)
            
            with patch.dict(os.environ, complex_env_vars, clear=False):
                manager = ConfigManager(temp_dir)
                config = manager.load_config()
                
                # Verify all environment variables took precedence
                assert config.app.debug is True
                assert config.ui.theme == "dark"
                assert config.ui.window_size == [1920, 1080]
                assert config.ollama.api_url == "http://custom.ollama.com:11434"
                assert config.ollama.timeout == 60
                assert config.ollama.enable_cache is False
                assert config.ai.temperature == 0.8
                assert config.ai.top_p == 0.95
                assert config.ai.preferred_models == ["llama3", "codellama", "mistral", "gemma"]
                assert config.logging.level == "DEBUG"
                assert config.logging.file_enabled is True
                assert config.logging.max_files == 15
                
                # Verify defaults file values that weren't overridden
                assert config.app.version == "1.0.0"


class TestSingletonManagerEdgeCases:
    """Test singleton manager edge cases."""
    
    def test_singleton_manager_thread_safety(self):
        """Test singleton manager creation thread safety (line 510)."""
        import create_project.config.config_manager as cm
        original_manager = cm._global_config_manager
        
        try:
            # Reset manager
            cm._global_config_manager = None
            managers = []
            
            def get_manager():
                manager = get_config_manager()
                managers.append(manager)
            
            # Create multiple threads trying to get manager
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=get_manager)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # All should be the same instance
            assert len(managers) == 10
            first_manager = managers[0]
            for manager in managers[1:]:
                assert manager is first_manager
                
        finally:
            # Restore original manager
            cm._global_config_manager = original_manager


if __name__ == "__main__":
    pytest.main([__file__])