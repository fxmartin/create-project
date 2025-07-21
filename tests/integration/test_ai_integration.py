# ABOUTME: Integration tests for AI service with project generation
# ABOUTME: Tests error handling with AI assistance and graceful degradation

"""Integration tests for AI service with project generation."""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import shutil

from create_project.core.project_generator import ProjectGenerator, ProjectOptions, GenerationResult
from create_project.core.exceptions import ProjectGenerationError, TemplateError, VirtualEnvError
from create_project.ai.ai_service import AIService, AIServiceConfig
from create_project.ai.exceptions import OllamaNotFoundError


class TestAIIntegration:
    """Test AI service integration with project generation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_template(self):
        """Create a mock template."""
        template = MagicMock()
        template.name = "test-template"
        template.metadata.name = "Test Template"
        template.metadata.description = "Test template"
        template.structure = {"directories": ["src", "tests"], "files": []}
        return template
    
    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service."""
        service = Mock(spec=AIService)
        service.is_available = AsyncMock(return_value=True)
        service.generate_help_response = AsyncMock(
            return_value="AI Suggestion: Check your file permissions and ensure the directory is writable."
        )
        return service
    
    def test_ai_assistance_on_error(self, temp_dir, mock_template, mock_ai_service):
        """Test AI assistance is provided when generation fails."""
        # Create generator with AI service
        generator = ProjectGenerator(ai_service=mock_ai_service)
        
        # Create a directory that will cause an error
        target_path = temp_dir / "existing_project"
        target_path.mkdir()
        (target_path / "file.txt").touch()  # Make it non-empty
        
        # Try to generate project (should fail)
        options = ProjectOptions(enable_ai_assistance=True)
        result = generator.generate_project(
            template=mock_template,
            variables={"project_name": "test"},
            target_path=target_path,
            options=options
        )
        
        # Verify failure with AI assistance
        assert not result.success
        assert result.ai_suggestions is not None
        assert "Check your file permissions" in result.ai_suggestions
        assert mock_ai_service.generate_help_response.called
    
    def test_ai_assistance_disabled(self, temp_dir, mock_template, mock_ai_service):
        """Test AI assistance is not called when disabled."""
        # Create generator with AI service
        generator = ProjectGenerator(ai_service=mock_ai_service)
        
        # Create a directory that will cause an error
        target_path = temp_dir / "existing_project"
        target_path.mkdir()
        (target_path / "file.txt").touch()  # Make it non-empty
        
        # Try to generate project with AI disabled
        options = ProjectOptions(enable_ai_assistance=False)
        result = generator.generate_project(
            template=mock_template,
            variables={"project_name": "test"},
            target_path=target_path,
            options=options
        )
        
        # Verify failure without AI assistance
        assert not result.success
        assert result.ai_suggestions is None
        assert not mock_ai_service.generate_help_response.called
    
    def test_ai_service_unavailable(self, temp_dir, mock_template):
        """Test graceful degradation when AI service is unavailable."""
        # Create generator without AI service
        generator = ProjectGenerator(ai_service=None)
        
        # Create a directory that will cause an error
        target_path = temp_dir / "existing_project"
        target_path.mkdir()
        (target_path / "file.txt").touch()  # Make it non-empty
        
        # Try to generate project
        options = ProjectOptions(enable_ai_assistance=True)
        result = generator.generate_project(
            template=mock_template,
            variables={"project_name": "test"},
            target_path=target_path,
            options=options
        )
        
        # Verify failure with fallback assistance (graceful degradation)
        assert not result.success
        # AI suggestions should contain fallback help when service is unavailable
        assert result.ai_suggestions is not None
        assert "Project generation failed" in result.ai_suggestions
        assert len(result.errors) > 0
    
    def test_ai_service_error_handling(self, temp_dir, mock_template):
        """Test handling of AI service errors."""
        # Create a mock AI service that raises an error
        mock_ai_service = Mock(spec=AIService)
        mock_ai_service.is_available = AsyncMock(return_value=True)
        mock_ai_service.generate_help_response = AsyncMock(
            side_effect=Exception("AI service error")
        )
        
        generator = ProjectGenerator(ai_service=mock_ai_service)
        
        # Create a directory that will cause an error
        target_path = temp_dir / "existing_project"
        target_path.mkdir()
        (target_path / "file.txt").touch()  # Make it non-empty
        
        # Try to generate project
        options = ProjectOptions(enable_ai_assistance=True)
        result = generator.generate_project(
            template=mock_template,
            variables={"project_name": "test"},
            target_path=target_path,
            options=options
        )
        
        # Verify failure without crashing (AI error is caught)
        assert not result.success
        assert result.ai_suggestions is None
        assert len(result.errors) > 0
    
    
    def test_ai_context_collection(self, temp_dir, mock_template):
        """Test that proper context is collected for AI assistance."""
        # Create a mock AI service to capture context
        captured_context = {}
        
        async def capture_context(**kwargs):
            captured_context.update(kwargs)
            return "AI response"
        
        mock_ai_service = Mock(spec=AIService)
        mock_ai_service.is_available = AsyncMock(return_value=True)
        mock_ai_service.generate_help_response = AsyncMock(side_effect=capture_context)
        
        generator = ProjectGenerator(ai_service=mock_ai_service)
        
        # Create error condition
        target_path = temp_dir / "existing_project"
        target_path.mkdir()
        (target_path / "file.txt").touch()
        
        # Generate with specific options
        options = ProjectOptions(
            enable_ai_assistance=True,
            create_git_repo=True,
            create_venv=True,
            venv_name="myenv",
            python_version="3.9"
        )
        
        variables = {"project_name": "test", "author": "Test Author"}
        
        result = generator.generate_project(
            template=mock_template,
            variables=variables,
            target_path=target_path,
            options=options
        )
        
        # Verify context was captured
        assert not result.success
        assert "error" in captured_context
        assert "template" in captured_context
        assert captured_context["template"] == mock_template
        assert "project_variables" in captured_context
        assert captured_context["project_variables"] == variables
        assert "options" in captured_context
        assert captured_context["options"]["create_git_repo"] is True
        assert captured_context["options"]["venv_name"] == "myenv"