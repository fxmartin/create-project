# ABOUTME: Test suite for the enhanced API module
# ABOUTME: Validates improved UI-Backend integration with detailed progress reporting

"""Test the enhanced API for UI-Backend integration."""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from create_project.core.api_enhanced import (
    DetailedProgress,
    EnhancedProjectGenerator,
    create_project_enhanced,
)
from create_project.core.project_generator import GenerationResult, ProjectOptions


class TestDetailedProgress:
    """Test the DetailedProgress dataclass."""
    
    def test_detailed_progress_creation(self):
        """Test creating a DetailedProgress instance."""
        progress = DetailedProgress(
            percentage=50,
            message="Processing...",
            current_step=2,
            total_steps=5,
            phase="generation",
            time_elapsed=10.5,
            estimated_remaining=10.5
        )
        
        assert progress.percentage == 50
        assert progress.message == "Processing..."
        assert progress.current_step == 2
        assert progress.total_steps == 5
        assert progress.phase == "generation"
        assert progress.time_elapsed == 10.5
        assert progress.estimated_remaining == 10.5


class TestEnhancedProjectGenerator:
    """Test the EnhancedProjectGenerator class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        mock_config_manager = MagicMock()
        mock_config_manager.get_setting.return_value = True
        
        mock_template_loader = MagicMock()
        mock_template_engine = MagicMock()
        
        # Mock template
        mock_template = MagicMock()
        mock_template.name = "Test Template"
        mock_template_engine.load_template.return_value = mock_template
        
        return {
            "config_manager": mock_config_manager,
            "template_loader": mock_template_loader,
            "template_engine": mock_template_engine,
            "template": mock_template
        }
    
    def test_initialization(self, mock_dependencies):
        """Test generator initialization."""
        generator = EnhancedProjectGenerator(
            config_manager=mock_dependencies["config_manager"],
            template_loader=mock_dependencies["template_loader"],
            template_engine=mock_dependencies["template_engine"]
        )
        
        assert generator.config_manager == mock_dependencies["config_manager"]
        assert generator.template_loader == mock_dependencies["template_loader"]
        assert generator.template_engine == mock_dependencies["template_engine"]
        assert generator._progress_callbacks == []
        assert generator._error_callbacks == []
    
    def test_progress_callback_management(self, mock_dependencies):
        """Test adding and removing progress callbacks."""
        generator = EnhancedProjectGenerator(**mock_dependencies)
        
        callback1 = Mock()
        callback2 = Mock()
        
        # Add callbacks
        generator.add_progress_callback(callback1)
        generator.add_progress_callback(callback2)
        assert len(generator._progress_callbacks) == 2
        
        # Add duplicate (should not add)
        generator.add_progress_callback(callback1)
        assert len(generator._progress_callbacks) == 2
        
        # Remove callback
        generator.remove_progress_callback(callback1)
        assert len(generator._progress_callbacks) == 1
        assert callback2 in generator._progress_callbacks
    
    def test_error_callback_management(self, mock_dependencies):
        """Test adding and removing error callbacks."""
        generator = EnhancedProjectGenerator(**mock_dependencies)
        
        callback1 = Mock()
        callback2 = Mock()
        
        # Add callbacks
        generator.add_error_callback(callback1)
        generator.add_error_callback(callback2)
        assert len(generator._error_callbacks) == 2
        
        # Remove callback
        generator.remove_error_callback(callback1)
        assert len(generator._error_callbacks) == 1
        assert callback2 in generator._error_callbacks
    
    def test_generate_project_with_progress(self, mock_dependencies, tmp_path):
        """Test project generation with progress reporting."""
        generator = EnhancedProjectGenerator(**mock_dependencies)
        
        # Mock the internal generator
        mock_result = GenerationResult(
            success=True,
            target_path=tmp_path,
            template_name="Test Template",
            files_created=[],
            errors=[],
            duration=1.0
        )
        
        with patch.object(generator.generator, "generate_project", return_value=mock_result):
            progress_callback = Mock()
            generator.add_progress_callback(progress_callback)
            
            result = generator.generate_project(
                template_path=Path("test.yaml"),
                target_path=tmp_path,
                variables={"name": "test"},
                options=ProjectOptions()
            )
            
            assert result.success is True
            
            # Check that progress was reported
            assert progress_callback.called
            
            # Check first and last progress calls
            first_call = progress_callback.call_args_list[0][0][0]
            assert isinstance(first_call, DetailedProgress)
            assert first_call.percentage == 0
            assert first_call.phase == "setup"
            
            last_call = progress_callback.call_args_list[-1][0][0]
            assert isinstance(last_call, DetailedProgress)
            assert last_call.percentage == 100
            assert last_call.phase == "complete"
    
    def test_generate_project_with_error(self, mock_dependencies, tmp_path):
        """Test project generation with error handling."""
        generator = EnhancedProjectGenerator(**mock_dependencies)
        
        # Mock template loading to fail
        mock_dependencies["template_engine"].load_template.side_effect = RuntimeError("Template not found")
        
        error_callback = Mock()
        generator.add_error_callback(error_callback)
        
        with pytest.raises(RuntimeError):
            generator.generate_project(
                template_path=Path("test.yaml"),
                target_path=tmp_path,
                variables={"name": "test"},
                options=ProjectOptions()
            )
        
        # Check that error callback was called
        assert error_callback.called
        error, context = error_callback.call_args[0]
        assert isinstance(error, RuntimeError)
        assert "Template not found" in str(error)
        assert context["operation"] == "project_generation"
        assert "config_state" in context
    
    def test_phase_determination(self, mock_dependencies):
        """Test phase determination logic."""
        generator = EnhancedProjectGenerator(**mock_dependencies)
        
        assert generator._determine_phase(None) == "generation"
        assert generator._determine_phase(0) == "setup"
        assert generator._determine_phase(10) == "setup"
        assert generator._determine_phase(50) == "generation"
        assert generator._determine_phase(90) == "postprocess"
        assert generator._determine_phase(100) == "complete"
    
    def test_step_calculation(self, mock_dependencies):
        """Test step calculation from percentage."""
        generator = EnhancedProjectGenerator(**mock_dependencies)
        
        assert generator._calculate_step(None) == 3
        assert generator._calculate_step(0) == 1
        assert generator._calculate_step(20) == 2
        assert generator._calculate_step(40) == 3
        assert generator._calculate_step(60) == 4
        assert generator._calculate_step(80) == 5
        assert generator._calculate_step(100) == 5
    
    def test_remaining_time_estimation(self, mock_dependencies):
        """Test remaining time estimation."""
        generator = EnhancedProjectGenerator(**mock_dependencies)
        
        # No estimation for 0% or None
        assert generator._estimate_remaining(None, 10.0) is None
        assert generator._estimate_remaining(0, 10.0) is None
        
        # Linear estimation
        assert generator._estimate_remaining(50, 10.0) == 10.0  # 50% done in 10s = 10s remaining
        assert generator._estimate_remaining(75, 15.0) == 5.0   # 75% done in 15s = 5s remaining
        assert generator._estimate_remaining(100, 20.0) == 0.0  # 100% done = 0s remaining


class TestCreateProjectEnhanced:
    """Test the create_project_enhanced function."""
    
    def test_create_project_enhanced_basic(self, tmp_path):
        """Test basic project creation with enhanced API."""
        mock_result = GenerationResult(
            success=True,
            target_path=tmp_path,
            template_name="Test Template",
            files_created=[],
            errors=[],
            duration=1.0
        )
        
        with patch("create_project.core.api_enhanced.EnhancedProjectGenerator") as MockGenerator:
            mock_instance = MockGenerator.return_value
            mock_instance.generate_project.return_value = mock_result
            
            result = create_project_enhanced(
                template_path=Path("test.yaml"),
                target_path=tmp_path,
                variables={"name": "test"}
            )
            
            assert result.success is True
            assert mock_instance.generate_project.called
    
    def test_create_project_enhanced_with_callbacks(self, tmp_path):
        """Test project creation with callbacks."""
        mock_result = GenerationResult(
            success=True,
            target_path=tmp_path,
            template_name="Test Template",
            files_created=[],
            errors=[],
            duration=1.0
        )
        
        progress_callback = Mock()
        error_callback = Mock()
        
        with patch("create_project.core.api_enhanced.EnhancedProjectGenerator") as MockGenerator:
            mock_instance = MockGenerator.return_value
            mock_instance.generate_project.return_value = mock_result
            
            result = create_project_enhanced(
                template_path=Path("test.yaml"),
                target_path=tmp_path,
                variables={"name": "test"},
                progress_callback=progress_callback,
                error_callback=error_callback
            )
            
            assert result.success is True
            
            # Check callbacks were registered
            mock_instance.add_progress_callback.assert_called_with(progress_callback)
            mock_instance.add_error_callback.assert_called_with(error_callback)
            
            # Check callbacks were cleaned up
            mock_instance.remove_progress_callback.assert_called_with(progress_callback)
            mock_instance.remove_error_callback.assert_called_with(error_callback)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])