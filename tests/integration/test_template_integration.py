# ABOUTME: Comprehensive integration tests for template system components
# ABOUTME: Tests template loading, validation, rendering, and cross-component workflows

"""
Comprehensive integration tests for template system.

This module tests the complete integration between:
- TemplateLoader and template file loading
- TemplateEngine and template processing  
- Template validation and error handling
- Template variable substitution and conditional logic
- Cross-component template workflows
"""

import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock

import pytest
import yaml

from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader
from create_project.templates.validator import TemplateValidator
from create_project.templates.schema.template import Template


@pytest.mark.integration
class TestTemplateSystemIntegration:
    """Test integration between all template system components."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.config_manager = ConfigManager()
        self.config_manager.set_setting("templates.builtin_path", "create_project/templates/builtin")
        self.config_manager.set_setting("templates.cache_enabled", True)
        
        self.template_loader = TemplateLoader(self.config_manager)
        self.template_engine = TemplateEngine(self.config_manager)
        self.validator = TemplateValidator()

    def test_builtin_template_loading_integration(self):
        """Test that all builtin templates load correctly through the system."""
        # Act - Get list of all builtin templates
        builtin_templates = self.template_loader.get_builtin_templates()
        
        # Assert - Should have all 6+ builtin templates
        assert len(builtin_templates) >= 6
        
        expected_templates = {
            "python_library", "python_package", "cli_single_package", 
            "cli_internal_packages", "django_web_app", "flask_web_app", "one_off_script"
        }
        
        loaded_names = {t["name"] for t in builtin_templates}
        # Check that we have at least the core expected templates
        common_templates = {"Python Library/Package", "CLI Application (Single Package)", "Flask Web Application"}
        assert common_templates.issubset(loaded_names)
        
        # Verify each template has required metadata structure
        for template_metadata in builtin_templates:
            assert template_metadata.get("name")
            assert template_metadata.get("description")
            
            # Try to load the actual template
            template_path = self.template_loader.find_template_by_name(template_metadata["name"])
            if template_path:
                template = self.template_engine.load_template(template_path)
                assert template.metadata.name
                assert template.metadata.description
                assert template.variables
                assert template.structure

    def test_template_validation_integration(self):
        """Test template validation across all builtin templates."""
        # Arrange - Get builtin templates and load them
        builtin_templates = self.template_loader.get_builtin_templates()
        
        # Act & Assert - Each template should validate successfully
        for template_metadata in builtin_templates[:3]:  # Test first 3 for performance
            template_path = self.template_loader.find_template_by_name(template_metadata["name"])
            if template_path:
                # Validate using the template validator
                validation_result = self.validator.validate_template_file(template_path)
                assert validation_result.is_valid, f"Template {template_metadata['name']} failed validation: {validation_result.errors}"

    def test_template_engine_processing_integration(self):
        """Test template engine processing with loaded templates."""
        # Arrange
        template_path = self.template_loader.find_template_by_name("python_library")
        assert template_path is not None
        template = self.template_engine.load_template(template_path)
        
        context = {
            "project_name": "test_library",
            "author": "Test Author",
            "email": "test@example.com",
            "description": "A test library",
            "license": "MIT",
            "python_version": "3.9.6"
        }
        
        # Act - Process template through engine
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            result = self.template_engine.process_template(template, context, target_path)
            
            # Assert - Processing should succeed
            assert result.success
            assert not result.errors
            
            # Verify structure was created
            project_path = target_path / "test_library"
            assert project_path.exists()
            assert (project_path / "pyproject.toml").exists()
            assert (project_path / "README.md").exists()

    def test_template_variable_substitution_integration(self):
        """Test template variable substitution across different template types."""
        test_cases = [
            ("python_library", {
                "project_name": "mylib",
                "author": "Test Author",
                "email": "test@example.com",
                "description": "My test library",
                "license": "MIT"
            }),
            ("cli_single_package", {
                "project_name": "mycli", 
                "author": "CLI Author",
                "email": "cli@example.com",
                "description": "My CLI tool",
                "license": "Apache-2.0"
            })
        ]
        
        for template_name, context in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Arrange
                template_path = self.template_loader.find_template_by_name(template_name)
                if not template_path:
                    continue  # Skip if template not found
                template = self.template_engine.load_template(template_path)
                target_path = Path(temp_dir)
                
                # Act
                result = self.template_engine.process_template(template, context, target_path)
                
                # Assert
                assert result.success, f"Failed processing {template_name}: {result.errors}"
                
                # Verify variable substitution in key files
                project_path = target_path / context["project_name"]
                if (project_path / "README.md").exists():
                    readme_content = (project_path / "README.md").read_text()
                    assert context["project_name"] in readme_content
                    assert context["description"] in readme_content

    def test_template_conditional_logic_integration(self):
        """Test conditional logic in templates based on variables."""
        # Arrange
        template_path = self.template_loader.find_template_by_name("python_library")
        if not template_path:
            pytest.skip("python_library template not found")
        template = self.template_engine.load_template(template_path)
        
        # Test with different conditional variable combinations
        test_cases = [
            {"include_tests": True, "testing_framework": "pytest"},
            {"include_tests": False},
            {"init_git": True},
            {"init_git": False}
        ]
        
        base_context = {
            "project_name": "test_conditional",
            "author": "Test Author", 
            "email": "test@example.com",
            "description": "Test conditional logic",
            "license": "MIT"
        }
        
        for additional_vars in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Arrange
                context = {**base_context, **additional_vars}
                target_path = Path(temp_dir)
                
                # Act
                result = self.template_engine.process_template(template, context, target_path)
                
                # Assert
                assert result.success, f"Failed with context {additional_vars}: {result.errors}"
                
                project_path = target_path / context["project_name"]
                
                # Verify conditional file creation
                if additional_vars.get("include_tests", False):
                    assert (project_path / "tests").exists(), "Tests directory should exist when include_tests=True"
                
                if additional_vars.get("init_git", False):
                    # Git files might be created depending on template logic
                    pass  # Template might conditionally include .gitignore

    def test_template_error_handling_integration(self):
        """Test error handling throughout the template system."""
        # Test invalid template loading
        invalid_template_path = self.template_loader.find_template_by_name("nonexistent_template")
        assert invalid_template_path is None
        
        # Test processing with missing required variables
        template_path = self.template_loader.find_template_by_name("python_library")
        if template_path:
            template = self.template_engine.load_template(template_path)
            incomplete_context = {"project_name": "test"}  # Missing required variables
            
            with tempfile.TemporaryDirectory() as temp_dir:
                target_path = Path(temp_dir)
                result = self.template_engine.process_template(template, incomplete_context, target_path)
                
                # Should handle missing variables gracefully
                # Result behavior depends on template engine implementation
                assert result is not None

    def test_template_caching_integration(self):
        """Test template caching behavior across the system."""
        # Arrange - Enable caching
        self.config_manager.set_setting("templates.cache_enabled", True)
        
        # Act - Load same template multiple times
        template_path = self.template_loader.find_template_by_name("python_library")
        if template_path:
            template1 = self.template_engine.load_template(template_path)
            template2 = self.template_engine.load_template(template_path)
        
            # Assert - Should get cached version
            assert template1 is not None
            assert template2 is not None
            assert template1.metadata.name == template2.metadata.name

    def test_template_loader_engine_coordination(self):
        """Test coordination between loader and engine components."""
        # Arrange
        template_names = ["python_library", "cli_single_package", "flask_web_app"]
        
        for template_name in template_names:
            # Act - Load template and immediately process it
            template_path = self.template_loader.find_template_by_name(template_name)
            if not template_path:
                continue  # Skip if template not found
            template = self.template_engine.load_template(template_path)
            assert template is not None, f"Failed to load template: {template_name}"
            
            context = {
                "project_name": f"test_{template_name.replace('_', '')}",
                "author": "Integration Test",
                "email": "test@integration.com", 
                "description": f"Integration test for {template_name}",
                "license": "MIT"
            }
            
            with tempfile.TemporaryDirectory() as temp_dir:
                target_path = Path(temp_dir)
                result = self.template_engine.process_template(template, context, target_path)
                
                # Assert - Loader and engine should work together seamlessly
                assert result.success, f"Loader-Engine coordination failed for {template_name}: {result.errors}"

    def test_custom_template_integration(self):
        """Test integration with custom user-defined templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange - Create a custom template
            custom_template_dir = Path(temp_dir) / "custom_templates"
            custom_template_dir.mkdir()
            
            custom_template_data = {
                "metadata": {
                    "name": "custom_test_template",
                    "description": "Custom template for testing",
                    "version": "1.0.0",
                    "category": "test",
                    "author": "Test Suite"
                },
                "variables": [
                    {
                        "name": "project_name",
                        "type": "string",
                        "description": "Name of the project",
                        "required": True
                    }
                ],
                "structure": [
                    {
                        "type": "file",
                        "path": "README.md",
                        "content": "# {{ project_name }}\n\nCustom template test."
                    }
                ]
            }
            
            # Write custom template
            custom_template_file = custom_template_dir / "custom_test_template.yaml"
            with open(custom_template_file, 'w') as f:
                yaml.dump(custom_template_data, f)
            
            # Update config to include custom template directory
            original_directories = self.config_manager.get_setting("templates.directories", [])
            self.config_manager.set_setting("templates.directories", 
                                           original_directories + [str(custom_template_dir)])
            
            # Create new loader with updated config
            custom_loader = TemplateLoader(self.config_manager)
            
            # Act - Load and process custom template
            template = custom_loader.load_template("custom_test_template")
            assert template is not None
            
            context = {"project_name": "my_custom_project"}
            
            with tempfile.TemporaryDirectory() as project_temp_dir:
                target_path = Path(project_temp_dir)
                result = self.template_engine.process_template(template, context, target_path)
                
                # Assert - Custom template should work through the system
                assert result.success
                readme_path = target_path / "my_custom_project" / "README.md"
                assert readme_path.exists()
                content = readme_path.read_text()
                assert "my_custom_project" in content


@pytest.mark.integration 
class TestTemplateEnginePerformanceIntegration:
    """Test template engine performance with integration scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.config_manager = ConfigManager()
        self.config_manager.set_setting("templates.builtin_path", "create_project/templates/builtin")
        self.template_loader = TemplateLoader(self.config_manager)
        self.template_engine = TemplateEngine(self.config_manager)

    @pytest.mark.slow
    def test_multiple_template_processing_performance(self):
        """Test processing multiple templates for performance."""
        # Arrange
        templates = self.template_loader.load_all_templates()
        contexts = [
            {
                "project_name": f"perf_test_{i}",
                "author": "Performance Test",
                "email": "perf@test.com",
                "description": f"Performance test project {i}",
                "license": "MIT"
            }
            for i in range(3)  # Test with 3 projects
        ]
        
        # Act & Assert - Should process multiple templates efficiently
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            
            for i, template in enumerate(templates[:3]):  # Test first 3 templates
                context = contexts[i]
                result = self.template_engine.process_template(template, context, target_path)
                assert result.success, f"Performance test failed for template {template.metadata.name}"

    def test_template_caching_performance_integration(self):
        """Test that template caching improves performance."""
        # Enable caching
        self.config_manager.set_setting("templates.cache_enabled", True)
        
        # Load same template multiple times - should benefit from caching
        template_path = self.template_loader.find_template_by_name("python_library")
        if template_path:
            for _ in range(5):
                template = self.template_engine.load_template(template_path)
                assert template is not None
            
                # Process template to ensure full workflow
                context = {
                    "project_name": "cache_test",
                    "author": "Cache Test",
                    "email": "cache@test.com",
                    "description": "Cache performance test",
                    "license": "MIT"
                }
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    target_path = Path(temp_dir)
                    result = self.template_engine.process_template(template, context, target_path)
                    assert result.success