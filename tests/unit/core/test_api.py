# ABOUTME: Unit tests for core API module - main public interface for project generation
# ABOUTME: Tests synchronous and asynchronous project creation, template validation and listing

"""
Unit tests for create_project.core.api module.

Tests the main public API functions including:
- create_project (synchronous)
- create_project_async (asynchronous)
- template validation and listing
- async operation management
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import pytest

from create_project.core.api import (
    create_project,
    create_project_async,
    get_async_result,
    cancel_async_operation,
    validate_template,
    list_available_templates,
    get_template_info,
)
from create_project.core.project_generator import GenerationResult, ProjectOptions
from create_project.core.threading_model import OperationResult, ThreadingModel
from create_project.config.config_manager import ConfigManager


class TestCreateProject:
    """Test the create_project function."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock ConfigManager."""
        config = Mock(spec=ConfigManager)
        return config

    @pytest.fixture
    def mock_template_loader(self):
        """Create a mock TemplateLoader."""
        loader = Mock()
        loader.find_template_by_name.return_value = Path("test_template.yaml")
        return loader

    @pytest.fixture
    def mock_template_engine(self):
        """Create a mock TemplateEngine."""
        engine = Mock()
        mock_template = Mock()
        mock_template.metadata.name = "Test Template"
        engine.load_template.return_value = mock_template
        return engine

    @pytest.fixture
    def mock_project_generator(self):
        """Create a mock ProjectGenerator."""
        generator = Mock()
        generator.generate_project.return_value = GenerationResult(
            success=True,
            target_path=Path("/test/my-project"),
            template_name="test_template",
            files_created=["README.md", "main.py"],
            errors=[]
        )
        return generator

    def test_create_project_success(self, mock_config_manager, mock_template_loader, 
                                  mock_template_engine, mock_project_generator):
        """Test successful project creation."""
        with patch('create_project.core.api.TemplateLoader', return_value=mock_template_loader), \
             patch('create_project.core.api.TemplateEngine', return_value=mock_template_engine), \
             patch('create_project.core.api.ProjectGenerator', return_value=mock_project_generator):
            
            result = create_project(
                template_name="test_template",
                project_name="my-project",
                target_directory="/test",
                variables={"author": "Test Author"},
                config_manager=mock_config_manager
            )
            
            assert result.success is True
            assert result.template_name == "test_template"
            assert len(result.files_created) == 2
            assert result.errors == []
            
            # Verify template loader was called correctly
            mock_template_loader.find_template_by_name.assert_called_once_with("test_template")
            
            # Verify template engine was called
            mock_template_engine.load_template.assert_called_once()
            
            # Verify generator was called with correct variables
            mock_project_generator.generate_project.assert_called_once()
            call_args = mock_project_generator.generate_project.call_args
            variables = call_args[1]['variables']
            assert variables['project_name'] == 'my-project'
            assert variables['author'] == 'Test Author'

    def test_create_project_template_not_found(self, mock_config_manager):
        """Test project creation when template is not found."""
        mock_loader = Mock()
        mock_loader.find_template_by_name.return_value = None
        
        mock_engine = Mock()
        mock_generator = Mock()
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader), \
             patch('create_project.core.api.TemplateEngine', return_value=mock_engine), \
             patch('create_project.core.api.ProjectGenerator', return_value=mock_generator):
            
            result = create_project(
                template_name="nonexistent_template",
                project_name="my-project",
                target_directory="/test",
                config_manager=mock_config_manager
            )
            
            assert result.success is False
            assert "Template 'nonexistent_template' not found" in result.errors
            assert result.template_name == "nonexistent_template"

    def test_create_project_with_defaults(self):
        """Test project creation with default parameters."""
        mock_loader = Mock()
        mock_loader.find_template_by_name.return_value = Path("test.yaml")
        
        mock_engine = Mock()
        mock_template = Mock()
        mock_engine.load_template.return_value = mock_template
        
        mock_generator = Mock()
        mock_generator.generate_project.return_value = GenerationResult(
            success=True,
            target_path=Path("/test/my-project"),
            template_name="test_template",
            files_created=[],
            errors=[]
        )
        
        with patch('create_project.core.api.ConfigManager') as mock_cm_class, \
             patch('create_project.core.api.TemplateLoader', return_value=mock_loader), \
             patch('create_project.core.api.TemplateEngine', return_value=mock_engine), \
             patch('create_project.core.api.ProjectGenerator', return_value=mock_generator):
            
            result = create_project(
                template_name="test_template",
                project_name="my-project",
                target_directory="/test"
            )
            
            assert result.success is True
            # Verify ConfigManager was instantiated
            mock_cm_class.assert_called()
            
            # Verify generator was called with project name in variables
            call_args = mock_generator.generate_project.call_args
            variables = call_args[1]['variables']
            assert variables['project_name'] == 'my-project'

    def test_create_project_dry_run(self, mock_config_manager, mock_template_loader,
                                   mock_template_engine, mock_project_generator):
        """Test project creation in dry run mode."""
        with patch('create_project.core.api.TemplateLoader', return_value=mock_template_loader), \
             patch('create_project.core.api.TemplateEngine', return_value=mock_template_engine), \
             patch('create_project.core.api.ProjectGenerator', return_value=mock_project_generator):
            
            create_project(
                template_name="test_template",
                project_name="my-project",
                target_directory="/test",
                dry_run=True,
                config_manager=mock_config_manager
            )
            
            # Verify dry_run was passed to generator
            call_args = mock_project_generator.generate_project.call_args
            assert call_args[1]['dry_run'] is True

    def test_create_project_with_progress_callback(self, mock_config_manager, mock_template_loader,
                                                  mock_template_engine, mock_project_generator):
        """Test project creation with progress callback."""
        progress_callback = Mock()
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_template_loader), \
             patch('create_project.core.api.TemplateEngine', return_value=mock_template_engine), \
             patch('create_project.core.api.ProjectGenerator', return_value=mock_project_generator):
            
            create_project(
                template_name="test_template",
                project_name="my-project",
                target_directory="/test",
                progress_callback=progress_callback,
                config_manager=mock_config_manager
            )
            
            # Verify progress_callback was passed to generator
            call_args = mock_project_generator.generate_project.call_args
            assert call_args[1]['progress_callback'] is progress_callback


class TestCreateProjectAsync:
    """Test the create_project_async function."""

    @pytest.fixture
    def mock_threading_model(self):
        """Create a mock ThreadingModel."""
        threading_model = Mock(spec=ThreadingModel)
        threading_model.start_project_generation.return_value = "op_test_12345678"
        return threading_model

    def test_create_project_async_success(self, mock_threading_model):
        """Test successful async project creation."""
        mock_loader = Mock()
        mock_loader.find_template_by_name.return_value = Path("test.yaml")
        
        mock_engine = Mock()
        mock_template = Mock()
        mock_engine.load_template.return_value = mock_template
        
        mock_generator = Mock()
        
        with patch('create_project.core.api.ConfigManager'), \
             patch('create_project.core.api.TemplateLoader', return_value=mock_loader), \
             patch('create_project.core.api.TemplateEngine', return_value=mock_engine), \
             patch('create_project.core.api.ProjectGenerator', return_value=mock_generator):
            
            operation_id = create_project_async(
                template_name="test_template",
                project_name="my-project",
                target_directory="/test",
                threading_model=mock_threading_model
            )
            
            assert operation_id == "op_test_12345678"
            
            # Verify threading model was called
            mock_threading_model.start_project_generation.assert_called_once()
            call_args = mock_threading_model.start_project_generation.call_args[1]
            assert 'operation_id' in call_args
            assert 'project_generator' in call_args
            assert 'template' in call_args
            assert 'variables' in call_args
            assert call_args['variables']['project_name'] == 'my-project'

    def test_create_project_async_template_not_found(self):
        """Test async project creation when template is not found."""
        mock_loader = Mock()
        mock_loader.find_template_by_name.return_value = None
        
        with patch('create_project.core.api.ConfigManager'), \
             patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            
            with pytest.raises(ValueError) as exc_info:
                create_project_async(
                    template_name="nonexistent_template",
                    project_name="my-project",
                    target_directory="/test"
                )
            
            assert "Template 'nonexistent_template' not found" in str(exc_info.value)

    def test_create_project_async_with_defaults(self):
        """Test async project creation with default threading model."""
        mock_loader = Mock()
        mock_loader.find_template_by_name.return_value = Path("test.yaml")
        
        mock_engine = Mock()
        mock_template = Mock()
        mock_engine.load_template.return_value = mock_template
        
        mock_generator = Mock()
        
        mock_threading_model = Mock()
        mock_threading_model.start_project_generation.return_value = "op_default_12345678"
        
        with patch('create_project.core.api.ConfigManager'), \
             patch('create_project.core.api.TemplateLoader', return_value=mock_loader), \
             patch('create_project.core.api.TemplateEngine', return_value=mock_engine), \
             patch('create_project.core.api.ProjectGenerator', return_value=mock_generator), \
             patch('create_project.core.api.ThreadingModel', return_value=mock_threading_model):
            
            operation_id = create_project_async(
                template_name="test_template",
                project_name="my-project",
                target_directory="/test"
            )
            
            assert operation_id == "op_default_12345678"


class TestAsyncOperationManagement:
    """Test async operation management functions."""

    def test_get_async_result(self):
        """Test getting async operation result."""
        mock_threading_model = Mock(spec=ThreadingModel)
        mock_result = OperationResult(
            operation_id="test_op",
            status="completed",
            result=Mock(),
            error=None
        )
        mock_threading_model.get_operation_result.return_value = mock_result
        
        result = get_async_result(
            operation_id="test_op",
            threading_model=mock_threading_model,
            timeout=30.0,
            remove_completed=True
        )
        
        assert result is mock_result
        mock_threading_model.get_operation_result.assert_called_once_with(
            operation_id="test_op",
            timeout=30.0,
            remove_completed=True
        )

    def test_cancel_async_operation(self):
        """Test cancelling async operation."""
        mock_threading_model = Mock(spec=ThreadingModel)
        mock_threading_model.cancel_operation.return_value = True
        
        result = cancel_async_operation(
            operation_id="test_op",
            threading_model=mock_threading_model
        )
        
        assert result is True
        mock_threading_model.cancel_operation.assert_called_once_with("test_op")


class TestTemplateValidation:
    """Test template validation functions."""

    def test_validate_template_success(self):
        """Test successful template validation."""
        mock_loader = Mock()
        mock_template = Mock()
        mock_loader.load_template.return_value = mock_template
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            result = validate_template("test_template")
            
            assert result is True
            mock_loader.load_template.assert_called_once_with("test_template")

    def test_validate_template_failure(self):
        """Test template validation failure."""
        mock_loader = Mock()
        mock_loader.load_template.side_effect = Exception("Template error")
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            result = validate_template("invalid_template")
            
            assert result is False

    def test_validate_template_with_config_manager(self):
        """Test template validation with custom config manager."""
        mock_config = Mock(spec=ConfigManager)
        
        mock_loader = Mock()
        mock_template = Mock()
        mock_loader.load_template.return_value = mock_template
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            result = validate_template("test_template", config_manager=mock_config)
            
            assert result is True


class TestTemplateListingAndInfo:
    """Test template listing and information functions."""

    def test_list_available_templates(self):
        """Test listing available templates."""
        mock_loader = Mock()
        mock_loader.list_available_templates.return_value = ["template1", "template2", "template3"]
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            templates = list_available_templates()
            
            assert templates == ["template1", "template2", "template3"]
            mock_loader.list_available_templates.assert_called_once()

    def test_list_available_templates_with_config_manager(self):
        """Test listing templates with custom config manager."""
        mock_config = Mock(spec=ConfigManager)
        
        mock_loader = Mock()
        mock_loader.list_available_templates.return_value = ["template1"]
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            templates = list_available_templates(config_manager=mock_config)
            
            assert templates == ["template1"]

    def test_get_template_info_basic(self):
        """Test getting basic template information."""
        mock_loader = Mock()
        mock_template = Mock()
        mock_template.name = "Test Template"
        mock_template.display_name = "Test Template Display"
        mock_template.description = "A test template"
        mock_template.version = "1.0.0"
        mock_template.author = "Test Author"
        mock_template.tags = ["test", "sample"]
        mock_template.variables = []
        
        # Mock compatibility
        mock_compatibility = Mock()
        mock_compatibility.min_python_version = "3.9.6"
        mock_compatibility.max_python_version = None
        mock_compatibility.supported_os = ["Linux", "macOS", "Windows"]
        mock_compatibility.dependencies = []
        mock_template.compatibility = mock_compatibility
        
        mock_loader.load_template.return_value = mock_template
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            info = get_template_info("test_template")
            
            assert info["name"] == "Test Template"
            assert info["display_name"] == "Test Template Display"
            assert info["description"] == "A test template"
            assert info["version"] == "1.0.0"
            assert info["author"] == "Test Author"
            assert info["tags"] == ["test", "sample"]
            assert info["variables"] == []
            assert info["compatibility"]["min_python_version"] == "3.9.6"
            assert info["compatibility"]["supported_os"] == ["Linux", "macOS", "Windows"]

    def test_get_template_info_with_variables(self):
        """Test getting template info with variables."""
        mock_loader = Mock()
        mock_template = Mock()
        mock_template.name = "Test Template"
        mock_template.display_name = "Test Template"
        mock_template.description = "A test template"
        mock_template.version = "1.0.0"
        mock_template.author = "Test Author"
        mock_template.tags = []
        
        # Mock variables
        mock_var = Mock()
        mock_var.name = "project_name"
        mock_var.display_name = "Project Name"
        mock_var.description = "Name of the project"
        mock_var.type = "string"
        mock_var.required = True
        mock_var.default = None
        mock_template.variables = [mock_var]
        
        # Mock compatibility
        mock_compatibility = Mock()
        mock_compatibility.min_python_version = "3.9.6"
        mock_compatibility.max_python_version = None
        mock_compatibility.supported_os = ["Linux"]
        mock_compatibility.dependencies = []
        mock_template.compatibility = mock_compatibility
        
        mock_loader.load_template.return_value = mock_template
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            info = get_template_info("test_template")
            
            assert len(info["variables"]) == 1
            var_info = info["variables"][0]
            assert var_info["name"] == "project_name"
            assert var_info["display_name"] == "Project Name"
            assert var_info["description"] == "Name of the project"
            assert var_info["type"] == "string"
            assert var_info["required"] is True
            assert var_info["default"] is None

    def test_get_template_info_missing_attributes(self):
        """Test getting template info when some attributes are missing."""
        mock_loader = Mock()
        mock_template = Mock(spec=[])  # Empty spec means no attributes
        mock_template.name = "Test Template"
        mock_template.display_name = "Test Template"
        mock_template.description = "A test template"
        mock_template.version = "1.0.0"
        mock_template.author = "Test Author"
        mock_template.tags = []
        # No variables or compatibility attributes - hasattr will return False
        
        mock_loader.load_template.return_value = mock_template
        
        with patch('create_project.core.api.TemplateLoader', return_value=mock_loader):
            info = get_template_info("test_template")
            
            assert info["variables"] == []
            assert info["compatibility"] == {}


class TestAPIIntegration:
    """Integration tests for API functions."""

    def test_create_project_full_workflow(self):
        """Test complete project creation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            
            # Mock all components to return success
            mock_loader = Mock()
            mock_loader.find_template_by_name.return_value = Path("test.yaml")
            
            mock_engine = Mock()
            mock_template = Mock()
            mock_template.metadata.name = "Test Template"
            mock_engine.load_template.return_value = mock_template
            
            mock_generator = Mock()
            mock_generator.generate_project.return_value = GenerationResult(
                success=True,
                target_path=target_dir / "test-project",
                template_name="test_template",
                files_created=["README.md"],
                errors=[]
            )
            
            with patch('create_project.core.api.ConfigManager'), \
                 patch('create_project.core.api.TemplateLoader', return_value=mock_loader), \
                 patch('create_project.core.api.TemplateEngine', return_value=mock_engine), \
                 patch('create_project.core.api.ProjectGenerator', return_value=mock_generator):
                
                result = create_project(
                    template_name="test_template",
                    project_name="test-project",
                    target_directory=str(target_dir),
                    variables={"author": "Test Author", "license": "MIT"}
                )
                
                assert result.success is True
                assert result.template_name == "test_template"
                assert "README.md" in result.files_created
                
                # Verify all variables were passed correctly
                call_args = mock_generator.generate_project.call_args[1]
                variables = call_args['variables']
                assert variables['project_name'] == 'test-project'
                assert variables['author'] == 'Test Author'
                assert variables['license'] == 'MIT'