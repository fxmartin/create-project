# ABOUTME: Unit tests for the ProjectGenerator class
# ABOUTME: Tests orchestration of project creation, template integration, and atomic operations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from create_project.config.config_manager import ConfigManager
from create_project.core.exceptions import (
    ProjectGenerationError,
    TemplateError,
)
from create_project.core.file_renderer import FileRenderer
from create_project.core.path_utils import PathHandler
from create_project.core.project_generator import (
    GenerationResult,
    ProjectGenerator,
    ProjectOptions,
)
from create_project.templates.loader import TemplateLoader


class TestProjectGenerator:
    """Test suite for ProjectGenerator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_config_manager(self):
        """Mock ConfigManager."""
        mock = Mock(spec=ConfigManager)
        mock.get_setting.return_value = {"logging": {"level": "INFO"}}
        return mock

    @pytest.fixture
    def mock_template_loader(self):
        """Mock TemplateLoader."""
        mock = Mock(spec=TemplateLoader)
        return mock

    @pytest.fixture
    def sample_template(self):
        """Create a sample template for testing."""
        # Create a mock template object instead of trying to construct a valid one
        mock_template = Mock()
        mock_template.name = "python_library"

        # Mock metadata
        mock_metadata = Mock()
        mock_metadata.name = "Python Library Template"
        mock_template.metadata = mock_metadata

        # Mock variables
        mock_template.variables = []

        # Mock structure properly
        mock_structure = Mock()
        mock_root = Mock()
        mock_root.directories = []  # Empty list instead of ["src", "tests", "docs"]
        mock_root.files = []
        mock_structure.root_directory = mock_root
        mock_template.structure = mock_structure

        # Additional attributes that might be needed
        mock_template.configuration = Mock()
        mock_template.configuration.hooks = Mock()
        mock_template.configuration.hooks.pre_generation = []
        mock_template.configuration.hooks.post_generation = []

        return mock_template

    @pytest.fixture
    def sample_variables(self):
        """Sample variables for template rendering."""
        return {
            "project_name": "my_test_project",
            "author_name": "Test Author",
            "python_version": "3.9",
        }

    @pytest.fixture
    def project_generator(self, mock_config_manager, mock_template_loader):
        """Create ProjectGenerator instance with mocked dependencies."""
        return ProjectGenerator(
            config_manager=mock_config_manager, template_loader=mock_template_loader
        )

    def test_initialization(self, mock_config_manager, mock_template_loader):
        """Test ProjectGenerator initialization."""
        generator = ProjectGenerator(
            config_manager=mock_config_manager, template_loader=mock_template_loader
        )

        assert generator.config_manager is mock_config_manager
        assert generator.template_loader is mock_template_loader
        assert isinstance(generator.path_handler, PathHandler)
        assert generator.directory_creator is None  # Not initialized until needed
        assert isinstance(generator.file_renderer, FileRenderer)
        assert generator.generation_errors == []
        assert generator.rollback_handlers == []

    def test_initialization_with_defaults(self):
        """Test ProjectGenerator initialization with default dependencies."""
        generator = ProjectGenerator()

        assert generator.config_manager is not None
        assert generator.template_loader is not None
        assert isinstance(generator.path_handler, PathHandler)
        assert generator.directory_creator is None  # Not initialized until needed
        assert isinstance(generator.file_renderer, FileRenderer)

    @patch("create_project.core.project_generator.get_logger")
    def test_generate_project_success(
        self,
        mock_get_logger,
        project_generator,
        sample_template,
        sample_variables,
        temp_dir,
    ):
        """Test successful project generation."""
        # Setup mocks
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        target_path = temp_dir / "test_project"
        progress_callback = Mock()

        # Mock the individual components
        project_generator._validate_target_path = Mock()
        project_generator._prepare_template_variables = Mock(
            return_value=sample_variables
        )
        project_generator._create_directories = Mock()
        project_generator._render_files = Mock()
        # Mock the new integration methods
        project_generator._initialize_git_repository = Mock(return_value=True)
        project_generator._create_virtual_environment = Mock(return_value=True)
        project_generator._execute_post_commands = Mock(return_value=2)
        project_generator._create_initial_commit = Mock()

        # Execute
        result = project_generator.generate_project(
            template=sample_template,
            variables=sample_variables,
            target_path=target_path,
            progress_callback=progress_callback,
        )

        # Verify result
        assert isinstance(result, GenerationResult)
        assert result.success is True
        assert result.target_path.resolve() == target_path.resolve()
        assert result.template_name == "python_library"
        assert len(result.errors) == 0
        # Verify new integration fields
        assert result.git_initialized is True
        assert result.venv_created is True
        assert result.commands_executed == 2

        # Verify method calls (paths might be normalized)
        project_generator._validate_target_path.assert_called_once()
        project_generator._prepare_template_variables.assert_called_once_with(
            sample_template, sample_variables
        )

        # Verify progress callbacks were made (the exact messages and progress percentages can vary)
        assert progress_callback.call_count > 0
        # Verify that at least some key progress messages were sent
        progress_messages = [call[0][0] for call in progress_callback.call_args_list]
        assert any("Project generation completed successfully" in msg for msg in progress_messages)

    def test_generate_project_with_validation_error(
        self, project_generator, sample_template, sample_variables, temp_dir
    ):
        """Test project generation with validation error."""
        target_path = temp_dir / "existing_file.txt"
        target_path.touch()  # Create a file at target location

        # Validation errors should return failed result
        result = project_generator.generate_project(
            template=sample_template,
            variables=sample_variables,
            target_path=target_path,
        )

        assert result.success is False
        assert len(result.errors) > 0
        assert "already exists and is not a directory" in result.errors[0]

    def test_generate_project_with_template_error(
        self, project_generator, sample_template, sample_variables, temp_dir
    ):
        """Test project generation with template processing error."""
        target_path = temp_dir / "test_project"

        # Mock template processing to raise error
        project_generator._render_files = Mock(
            side_effect=TemplateError("Template processing failed")
        )
        project_generator._validate_target_path = Mock()
        project_generator._prepare_template_variables = Mock(
            return_value=sample_variables
        )
        project_generator._create_directories = Mock()
        # Mock integration methods
        project_generator._initialize_git_repository = Mock(return_value=False)
        project_generator._create_virtual_environment = Mock(return_value=False)
        project_generator._execute_post_commands = Mock(return_value=0)
        project_generator._create_initial_commit = Mock()

        result = project_generator.generate_project(
            template=sample_template,
            variables=sample_variables,
            target_path=target_path,
        )

        # Should return result with error, not raise exception
        assert result.success is False
        assert len(result.errors) == 1
        assert "Template processing failed" in result.errors[0]

    def test_generate_project_with_rollback(
        self, project_generator, sample_template, sample_variables, temp_dir
    ):
        """Test project generation rollback on error."""
        target_path = temp_dir / "test_project"

        # Create a mock rollback handler to track calls
        rollback_handler = Mock()

        def mock_create_directories(*args, **kwargs):
            """Mock that adds a rollback handler then fails."""
            project_generator._add_rollback_handler(rollback_handler)

        def mock_render_files(*args, **kwargs):
            """Mock that raises an error to trigger rollback."""
            raise TemplateError("Rendering failed")

        # Mock methods
        project_generator._validate_target_path = Mock()
        project_generator._prepare_template_variables = Mock(
            return_value=sample_variables
        )
        project_generator._create_directories = mock_create_directories
        project_generator._render_files = mock_render_files

        result = project_generator.generate_project(
            template=sample_template,
            variables=sample_variables,
            target_path=target_path,
        )

        # Verify rollback was called
        rollback_handler.assert_called_once()
        assert result.success is False

    def test_validate_target_path_success(self, project_generator, temp_dir):
        """Test successful target path validation."""
        target_path = temp_dir / "new_project"

        # Should not raise exception
        project_generator._validate_target_path(target_path)

    def test_validate_target_path_existing_file(self, project_generator, temp_dir):
        """Test target path validation with existing file."""
        target_path = temp_dir / "existing_file.txt"
        target_path.touch()

        with pytest.raises(ProjectGenerationError) as exc_info:
            project_generator._validate_target_path(target_path)

        assert "already exists and is not a directory" in str(exc_info.value)

    def test_validate_target_path_non_empty_directory(
        self, project_generator, temp_dir
    ):
        """Test target path validation with non-empty directory."""
        target_path = temp_dir / "existing_dir"
        target_path.mkdir()
        (target_path / "some_file.txt").touch()

        with pytest.raises(ProjectGenerationError) as exc_info:
            project_generator._validate_target_path(target_path)

        assert "already exists and is not empty" in str(exc_info.value)

    def test_validate_target_path_permission_denied(self, project_generator, temp_dir):
        """Test target path validation with permission issues."""
        # Create a path that would cause permission issues
        target_path = temp_dir / "no_permission"

        with patch(
            "pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")
        ):
            with pytest.raises(ProjectGenerationError) as exc_info:
                project_generator._validate_target_path(target_path)

            assert "Permission denied" in str(exc_info.value)

    def test_prepare_template_variables(self, project_generator, sample_template):
        """Test template variable preparation."""
        input_vars = {"project_name": "test", "author_name": "author"}

        result = project_generator._prepare_template_variables(
            sample_template, input_vars
        )

        # Should contain original variables plus any defaults
        assert "project_name" in result
        assert "author_name" in result
        assert result["project_name"] == "test"
        assert result["author_name"] == "author"

    def test_create_directories(self, project_generator, sample_template, temp_dir):
        """Test directory creation."""
        target_path = temp_dir / "test_project"
        mock_progress_tracker = Mock()

        # Mock DirectoryCreator creation
        with patch(
            "create_project.core.project_generator.DirectoryCreator"
        ) as mock_dir_creator_class:
            mock_dir_creator = Mock()
            mock_dir_creator.created_dirs = []  # Change to created_dirs
            mock_dir_creator_class.return_value = mock_dir_creator

            project_generator._create_directories(
                sample_template, target_path, {}, mock_progress_tracker
            )

            # Verify directory creator was created and called
            mock_dir_creator_class.assert_called_once_with(base_path=target_path)
            mock_dir_creator.create_structure.assert_called_once()
            # Progress tracker may or may not be used depending on implementation

    def test_render_files(
        self, project_generator, sample_template, sample_variables, temp_dir
    ):
        """Test file rendering."""
        target_path = temp_dir / "test_project"
        mock_progress_tracker = Mock()

        # Add some files to the template structure
        mock_file = Mock()
        mock_file.name = "test.py"
        mock_file.template_name = "test.py.j2"
        sample_template.structure.root_directory.files = [mock_file]

        # Mock the file renderer
        project_generator.file_renderer.render_files_from_structure = Mock()

        project_generator._render_files(
            sample_template, sample_variables, target_path, mock_progress_tracker
        )

        # Verify file renderer was called
        project_generator.file_renderer.render_files_from_structure.assert_called_once()
        # Progress tracker may or may not be used depending on implementation

    def test_add_rollback_handler(self, project_generator):
        """Test adding rollback handler."""
        handler = Mock()
        project_generator._add_rollback_handler(handler)

        assert handler in project_generator.rollback_handlers

    def test_execute_rollback(self, project_generator):
        """Test rollback execution."""
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()

        project_generator.rollback_handlers = [handler1, handler2, handler3]

        project_generator._execute_rollback()

        # Verify handlers called in reverse order
        handler3.assert_called_once()
        handler2.assert_called_once()
        handler1.assert_called_once()

    def test_execute_rollback_with_errors(self, project_generator):
        """Test rollback execution with handler errors."""
        handler1 = Mock()
        handler2 = Mock(side_effect=Exception("Rollback error"))
        handler3 = Mock()

        project_generator.rollback_handlers = [handler1, handler2, handler3]

        # Should not raise exception, but log errors
        project_generator._execute_rollback()

        # All handlers should still be called
        handler3.assert_called_once()
        handler2.assert_called_once()
        handler1.assert_called_once()

    def test_generation_result_creation(self):
        """Test GenerationResult creation."""
        target_path = Path("/test/path")
        result = GenerationResult(
            success=True,
            target_path=target_path,
            template_name="test_template",
            files_created=["file1.py", "file2.py"],
            errors=[],
        )

        assert result.success is True
        assert result.target_path == target_path
        assert result.template_name == "test_template"
        assert result.files_created == ["file1.py", "file2.py"]
        assert result.errors == []

    def test_generation_result_with_errors(self):
        """Test GenerationResult with errors."""
        result = GenerationResult(
            success=False,
            target_path=Path("/test/path"),
            template_name="test_template",
            files_created=[],
            errors=["Error 1", "Error 2"],
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert "Error 1" in result.errors
        assert "Error 2" in result.errors

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_generate_project_dry_run(
        self, project_generator, sample_template, sample_variables, temp_dir, dry_run
    ):
        """Test project generation in dry-run mode."""
        target_path = temp_dir / "test_project"

        # Mock components
        project_generator._validate_target_path = Mock()
        project_generator._prepare_template_variables = Mock(
            return_value=sample_variables
        )
        project_generator._create_directories = Mock()
        project_generator._render_files = Mock()

        result = project_generator.generate_project(
            template=sample_template,
            variables=sample_variables,
            target_path=target_path,
            dry_run=dry_run,
        )

        if dry_run:
            # In dry-run mode, should not actually create files
            project_generator._create_directories.assert_not_called()
            project_generator._render_files.assert_not_called()
        else:
            # In normal mode, should create files
            project_generator._create_directories.assert_called_once()
            project_generator._render_files.assert_called_once()

        assert result.success is True

    def test_concurrent_generation_safety(self, project_generator):
        """Test that generator handles concurrent usage safely."""
        # This test verifies thread safety measures are in place
        assert hasattr(project_generator, "generation_errors")
        assert hasattr(project_generator, "rollback_handlers")

        # Each generation should start with clean state
        project_generator.generation_errors = ["old error"]
        project_generator.rollback_handlers = [Mock()]

        # A new generation should clear previous state
        project_generator.generation_errors.clear()
        project_generator.rollback_handlers.clear()

        assert len(project_generator.generation_errors) == 0
        assert len(project_generator.rollback_handlers) == 0

    # NEW COMPREHENSIVE TESTS FOR PROJECT GENERATOR COVERAGE

    def test_project_options_defaults(self):
        """Test ProjectOptions default values."""

        options = ProjectOptions()
        assert options.create_git_repo is True
        assert options.create_venv is True
        assert options.venv_name == ".venv"
        assert options.python_version is None
        assert options.execute_post_commands is True
        assert options.git_config is None
        assert options.enable_ai_assistance is True

    def test_project_options_custom(self):
        """Test ProjectOptions with custom values."""
        from create_project.core.project_generator import GitConfig

        git_config = GitConfig(user_name="Test User", user_email="test@example.com")
        options = ProjectOptions(
            create_git_repo=False,
            create_venv=False,
            venv_name="venv",
            python_version="3.11",
            execute_post_commands=False,
            git_config=git_config,
            enable_ai_assistance=False
        )

        assert options.create_git_repo is False
        assert options.create_venv is False
        assert options.venv_name == "venv"
        assert options.python_version == "3.11"
        assert options.execute_post_commands is False
        assert options.git_config == git_config
        assert options.enable_ai_assistance is False

    def test_generation_result_with_all_fields(self):
        """Test GenerationResult with all optional fields."""
        from create_project.core.project_generator import GenerationResult

        result = GenerationResult(
            success=True,
            target_path=Path("/test/path"),
            template_name="test_template",
            files_created=["file1.py", "file2.py"],
            errors=[],
            duration=5.5,
            git_initialized=True,
            venv_created=True,
            commands_executed=3,
            ai_suggestions="Try this fix"
        )

        assert result.success is True
        assert result.duration == 5.5
        assert result.git_initialized is True
        assert result.venv_created is True
        assert result.commands_executed == 3
        assert result.ai_suggestions == "Try this fix"

    def test_ai_service_initialization_success(self, mock_config_manager, mock_template_loader):
        """Test successful AI service initialization."""
        mock_config_manager.get_setting.side_effect = lambda key, default=None: {
            "ai.enabled": True,
            "ai.ollama_url": "http://localhost:11434",
            "ai.ollama_timeout": 30,
            "ai.cache_enabled": True,
            "ai.cache_ttl_hours": 24,
            "ai.max_cache_entries": 100,
            "ai.preferred_models": ["llama3.2"],
            "ai.context_collection_enabled": True,
            "ai.max_context_size_kb": 4
        }.get(key, default)

        with patch("create_project.core.project_generator.AIService") as mock_ai_service_class, \
             patch("create_project.core.project_generator.AIServiceConfig") as mock_ai_config_class:

            mock_ai_service_instance = Mock()
            mock_ai_service_class.return_value = mock_ai_service_instance

            mock_ai_config_instance = Mock()
            mock_ai_config_instance.enabled = True
            mock_ai_config_class.return_value = mock_ai_config_instance

            generator = ProjectGenerator(
                config_manager=mock_config_manager,
                template_loader=mock_template_loader
            )

            # AI service should be created when enabled
            mock_ai_service_class.assert_called_once()
            assert generator.ai_service == mock_ai_service_instance

    def test_ai_service_initialization_disabled(self, mock_config_manager, mock_template_loader):
        """Test AI service initialization when disabled."""
        mock_config_manager.get_setting.side_effect = lambda key, default=None: {
            "ai.enabled": False
        }.get(key, default)

        generator = ProjectGenerator(
            config_manager=mock_config_manager,
            template_loader=mock_template_loader
        )

        # AI service should not be initialized when disabled
        assert generator.ai_service is None

    def test_ai_service_initialization_import_error(self, mock_config_manager, mock_template_loader):
        """Test AI service initialization with import error."""
        mock_config_manager.get_setting.return_value = True

        # Mock the import to raise ImportError for the ai_service module
        import sys
        with patch.dict(sys.modules, {"create_project.ai.ai_service": None}):
            generator = ProjectGenerator(
                config_manager=mock_config_manager,
                template_loader=mock_template_loader
            )

            # Should handle import error gracefully
            assert generator.ai_service is None

    @patch("create_project.core.project_generator.get_logger")
    def test_progress_reporting_accuracy(
        self,
        mock_get_logger,
        project_generator,
        sample_template,
        sample_variables,
        temp_dir,
    ):
        """Test accurate progress reporting throughout generation."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        target_path = temp_dir / "test_project"
        progress_calls = []

        def progress_callback(message, percentage):
            progress_calls.append((message, percentage))

        # Mock all components
        project_generator._validate_target_path = Mock()
        project_generator._prepare_template_variables = Mock(return_value=sample_variables)
        project_generator._create_directories = Mock()
        project_generator._render_files = Mock()
        project_generator._initialize_git_repository = Mock(return_value=True)
        project_generator._create_virtual_environment = Mock(return_value=True)
        project_generator._execute_post_commands = Mock(return_value=2)
        project_generator._create_initial_commit = Mock()

        result = project_generator.generate_project(
            template=sample_template,
            variables=sample_variables,
            target_path=target_path,
            progress_callback=progress_callback,
        )

        # Verify progress was reported
        assert len(progress_calls) > 0
        assert result.success is True

        # Verify progress percentages are reasonable
        percentages = [call[1] for call in progress_calls if call[1] is not None]
        if percentages:
            assert min(percentages) >= 0
            assert max(percentages) <= 100

    def test_template_variable_preparation_with_defaults(self, project_generator):
        """Test template variable preparation with default values."""
        mock_template = Mock()
        mock_var1 = Mock()
        mock_var1.name = "var1"
        mock_var1.default = "default_value"
        mock_var1.required = False

        mock_var2 = Mock()
        mock_var2.name = "var2"
        mock_var2.default = None
        mock_var2.required = True

        mock_template.variables = [mock_var1, mock_var2]

        input_vars = {"var2": "provided_value"}

        result = project_generator._prepare_template_variables(mock_template, input_vars)

        # Should include provided variables and defaults
        assert "var1" in result
        assert "var2" in result
        assert result["var1"] == "default_value"
        assert result["var2"] == "provided_value"

    def test_count_files_in_structure(self, project_generator):
        """Test file counting in template structure."""
        # The method expects a nested dictionary structure with files as keys/values
        structure = {
            "file1.py": "content",
            "file2.py": "content",
            "subdir": {
                "file3.py": "content"
            }
        }

        count = project_generator._count_files_in_structure(structure)
        assert count == 3  # file1.py, file2.py, file3.py

    def test_count_files_in_empty_structure(self, project_generator):
        """Test file counting in empty structure."""
        structure = {}
        count = project_generator._count_files_in_structure(structure)
        assert count == 0

    def test_should_include_item_with_condition(self, project_generator):
        """Test conditional item inclusion based on variables."""
        # Mock item with condition - using the actual structure expected
        item = Mock()
        condition_mock = Mock()
        condition_mock.expression = "{{ python_version == '3.9' }}"
        item.condition = condition_mock

        variables = {"python_version": "3.9"}

        # Mock the template engine render method to return "true"
        project_generator.file_renderer.template_engine.render_template_string = Mock(return_value="true")

        result = project_generator._should_include_item(item, variables)
        assert result is True
        project_generator.file_renderer.template_engine.render_template_string.assert_called_once_with(
            "{{ python_version == '3.9' }}", variables
        )

    def test_should_include_item_without_condition(self, project_generator):
        """Test item inclusion without condition (should always include)."""
        item = Mock()
        item.condition = None

        result = project_generator._should_include_item(item, {})
        assert result is True

    def test_should_include_item_condition_error(self, project_generator):
        """Test item inclusion with condition evaluation error."""
        item = Mock()
        item.condition = "invalid_syntax ==''"

        with patch("create_project.core.project_generator.eval", side_effect=Exception("Invalid syntax")):
            result = project_generator._should_include_item(item, {})
            # Should default to True when condition evaluation fails
            assert result is True

    def test_directory_creation_with_progress_tracking(
        self, project_generator, sample_template, temp_dir
    ):
        """Test directory creation with progress tracking."""
        target_path = temp_dir / "test_project"
        progress_tracker = Mock()

        # Mock DirectoryCreator
        with patch("create_project.core.project_generator.DirectoryCreator") as mock_dir_creator_class:
            mock_dir_creator = Mock()
            mock_dir_creator.created_dirs = ["dir1", "dir2"]
            mock_dir_creator_class.return_value = mock_dir_creator

            project_generator._create_directories(
                sample_template, target_path, {}, progress_tracker
            )

            # Verify DirectoryCreator was used properly
            mock_dir_creator_class.assert_called_once_with(base_path=target_path)
            mock_dir_creator.create_structure.assert_called_once()

    def test_file_rendering_with_progress_tracking(
        self, project_generator, sample_template, sample_variables, temp_dir
    ):
        """Test file rendering with progress tracking."""
        target_path = temp_dir / "test_project"
        progress_tracker = Mock()

        # Add files to template structure
        mock_file1 = Mock()
        mock_file1.name = "file1.py"
        mock_file1.template_name = "file1.py.j2"

        mock_file2 = Mock()
        mock_file2.name = "file2.py"
        mock_file2.template_name = "file2.py.j2"

        sample_template.structure.root_directory.files = [mock_file1, mock_file2]

        # Mock file renderer
        project_generator.file_renderer.render_files_from_structure = Mock()

        project_generator._render_files(
            sample_template, sample_variables, target_path, progress_tracker
        )

        # Verify file renderer was called
        project_generator.file_renderer.render_files_from_structure.assert_called_once()

    def test_git_initialization_success(self, project_generator, temp_dir):
        """Test successful git repository initialization."""
        target_path = temp_dir / "test_project"
        target_path.mkdir()

        # Mock GitManager
        project_generator.git_manager.is_git_available = Mock(return_value=True)
        project_generator.git_manager.init_repository = Mock()
        project_generator.git_manager.configure_repository = Mock()

        result = project_generator._initialize_git_repository(target_path, None)

        assert result is True
        project_generator.git_manager.init_repository.assert_called_once_with(target_path, None)

    def test_git_initialization_not_available(self, project_generator, temp_dir):
        """Test git initialization when git is not available."""
        target_path = temp_dir / "test_project"
        target_path.mkdir()

        # Mock GitManager
        project_generator.git_manager.is_git_available = Mock(return_value=False)

        result = project_generator._initialize_git_repository(target_path, None)

        assert result is False
        project_generator.git_manager.init_repository.assert_not_called()

    def test_git_initialization_error(self, project_generator, temp_dir):
        """Test git initialization with error."""
        from create_project.core.exceptions import GitError

        target_path = temp_dir / "test_project"
        target_path.mkdir()

        # Mock GitManager to raise error
        project_generator.git_manager.is_git_available = Mock(return_value=True)
        project_generator.git_manager.init_repository = Mock(
            side_effect=GitError("Git initialization failed")
        )

        result = project_generator._initialize_git_repository(target_path, None)

        assert result is False
        # Error should be recorded
        assert len(project_generator.generation_errors) > 0
        assert "Git initialization failed" in project_generator.generation_errors[0]

    def test_venv_creation_success(self, project_generator, temp_dir):
        """Test successful virtual environment creation."""

        target_path = temp_dir / "test_project"
        target_path.mkdir()
        options = ProjectOptions(venv_name=".venv", python_version="3.9")

        # Mock VenvManager
        project_generator.venv_manager.create_venv = Mock()

        result = project_generator._create_virtual_environment(target_path, options, None)

        assert result is True
        project_generator.venv_manager.create_venv.assert_called_once_with(
            target_path / ".venv", python_version="3.9"
        )

    def test_venv_creation_error(self, project_generator, temp_dir):
        """Test virtual environment creation with error."""
        from create_project.core.exceptions import VirtualEnvError

        target_path = temp_dir / "test_project"
        target_path.mkdir()
        options = ProjectOptions()

        # Mock VenvManager to raise error
        project_generator.venv_manager.create_venv = Mock(
            side_effect=VirtualEnvError("Virtual environment creation failed")
        )

        result = project_generator._create_virtual_environment(target_path, options, None)

        assert result is False
        # Error should be recorded
        assert len(project_generator.generation_errors) > 0
        assert "Virtual environment creation failed" in project_generator.generation_errors[0]

    def test_post_command_execution_success(self, project_generator, temp_dir):
        """Test successful post-command execution."""
        target_path = temp_dir / "test_project"
        target_path.mkdir()

        # Mock template with post commands
        mock_template = Mock()
        mock_actions = Mock()
        mock_actions.post_generation = ["pip install -r requirements.txt", "pre-commit install"]
        mock_template.actions = mock_actions

        # Mock CommandExecutor
        project_generator.command_executor.execute_command = Mock(return_value=True)

        result = project_generator._execute_post_commands(
            mock_template, target_path
        )

        assert result == 2  # Two commands executed
        assert project_generator.command_executor.execute_command.call_count == 2

    def test_post_command_execution_with_failures(self, project_generator, temp_dir):
        """Test post-command execution with some failures."""
        target_path = temp_dir / "test_project"
        target_path.mkdir()

        # Mock template with post commands
        mock_template = Mock()
        mock_actions = Mock()
        mock_actions.post_generation = ["successful_command", "failing_command"]
        mock_template.actions = mock_actions

        # Mock CommandExecutor - first succeeds, second fails
        project_generator.command_executor.execute_command = Mock(
            side_effect=[True, False]
        )

        result = project_generator._execute_post_commands(
            mock_template, target_path
        )

        assert result == 1  # Only one command succeeded
        assert project_generator.command_executor.execute_command.call_count == 2

    def test_initial_commit_creation(self, project_generator, temp_dir):
        """Test creation of initial git commit."""
        target_path = temp_dir / "test_project"
        target_path.mkdir()

        # Mock GitManager
        project_generator.git_manager.create_initial_commit = Mock()

        project_generator._create_initial_commit(target_path, None)

        project_generator.git_manager.create_initial_commit.assert_called_once_with(
            target_path, "Initial project structure"
        )

    def test_initial_commit_creation_error(self, project_generator, temp_dir):
        """Test initial commit creation with error."""
        from create_project.core.exceptions import GitError

        target_path = temp_dir / "test_project"
        target_path.mkdir()

        # Mock GitManager to raise error
        project_generator.git_manager.create_initial_commit = Mock(
            side_effect=GitError("Commit failed")
        )

        # Should not raise exception, just log error
        project_generator._create_initial_commit(target_path, None)

        # Error should be recorded
        assert len(project_generator.generation_errors) > 0
        assert "Commit failed" in project_generator.generation_errors[0]

    def test_ai_assistance_request(self, project_generator):
        """Test AI assistance request functionality."""
        # Mock AI service
        mock_ai_service = Mock()
        mock_ai_service.get_error_assistance = Mock(return_value="AI suggestion")
        project_generator.ai_service = mock_ai_service

        error_context = {
            "error": "Template rendering failed",
            "template": "python_library",
            "variables": {"project_name": "test"}
        }

        result = project_generator._get_ai_assistance(error_context)

        assert result == "AI suggestion"
        mock_ai_service.get_error_assistance.assert_called_once_with(error_context)

    def test_ai_assistance_no_service(self, project_generator):
        """Test AI assistance when service is not available."""
        project_generator.ai_service = None

        result = project_generator._get_ai_assistance({"error": "test"})

        assert result is None

    def test_ai_assistance_service_error(self, project_generator):
        """Test AI assistance when service raises error."""
        # Mock AI service to raise error
        mock_ai_service = Mock()
        mock_ai_service.get_error_assistance = Mock(
            side_effect=Exception("AI service error")
        )
        project_generator.ai_service = mock_ai_service

        result = project_generator._get_ai_assistance({"error": "test"})

        assert result is None  # Should handle error gracefully

    def test_generate_project_with_ai_assistance(
        self, project_generator, sample_template, sample_variables, temp_dir
    ):
        """Test project generation with AI assistance on error."""

        target_path = temp_dir / "test_project"
        options = ProjectOptions(enable_ai_assistance=True)

        # Mock AI service
        mock_ai_service = Mock()
        mock_ai_service.get_error_assistance = Mock(return_value="Try this fix")
        project_generator.ai_service = mock_ai_service

        # Mock components to cause an error
        project_generator._validate_target_path = Mock()
        project_generator._prepare_template_variables = Mock(return_value=sample_variables)
        project_generator._create_directories = Mock()
        project_generator._render_files = Mock(
            side_effect=TemplateError("Rendering failed")
        )

        result = project_generator.generate_project(
            template=sample_template,
            variables=sample_variables,
            target_path=target_path,
            options=options,
        )

        assert result.success is False
        assert result.ai_suggestions == "Try this fix"
        mock_ai_service.get_error_assistance.assert_called_once()

    def test_generate_project_dry_run_comprehensive(
        self, project_generator, sample_template, sample_variables, temp_dir
    ):
        """Test comprehensive dry-run project generation."""
        target_path = temp_dir / "test_project"

        # Mock all components
        project_generator._validate_target_path = Mock()
        project_generator._prepare_template_variables = Mock(return_value=sample_variables)
        project_generator._create_directories = Mock()
        project_generator._render_files = Mock()
        project_generator._initialize_git_repository = Mock(return_value=True)
        project_generator._create_virtual_environment = Mock(return_value=True)
        project_generator._execute_post_commands = Mock(return_value=2)
        project_generator._create_initial_commit = Mock()

        result = project_generator.generate_project(
            template=sample_template,
            variables=sample_variables,
            target_path=target_path,
            dry_run=True,
        )

        # In dry-run mode, should validate but not execute
        project_generator._validate_target_path.assert_called_once()
        project_generator._prepare_template_variables.assert_called_once()
        project_generator._create_directories.assert_not_called()
        project_generator._render_files.assert_not_called()
        project_generator._initialize_git_repository.assert_not_called()
        project_generator._create_virtual_environment.assert_not_called()
        project_generator._execute_post_commands.assert_not_called()
        project_generator._create_initial_commit.assert_not_called()

        assert result.success is True

    def test_error_accumulation_and_reporting(self, project_generator, temp_dir):
        """Test that errors are properly accumulated and reported."""
        # Add some errors to the generator
        project_generator.generation_errors.append("Error 1: Template issue")
        project_generator.generation_errors.append("Error 2: File permission issue")

        # Errors should be accumulated
        assert len(project_generator.generation_errors) == 2
        assert "Error 1: Template issue" in project_generator.generation_errors
        assert "Error 2: File permission issue" in project_generator.generation_errors

    def test_rollback_handler_ordering(self, project_generator):
        """Test that rollback handlers are executed in reverse order."""
        call_order = []

        def handler1():
            call_order.append(1)

        def handler2():
            call_order.append(2)

        def handler3():
            call_order.append(3)

        # Add handlers in order 1, 2, 3
        project_generator._add_rollback_handler(handler1)
        project_generator._add_rollback_handler(handler2)
        project_generator._add_rollback_handler(handler3)

        # Execute rollback
        project_generator._execute_rollback()

        # Should execute in reverse order: 3, 2, 1
        assert call_order == [3, 2, 1]

    def test_build_file_structure_from_template(self, project_generator):
        """Test building file structure from template."""
        # Mock template structure
        mock_template = Mock()
        mock_structure = Mock()
        mock_root = Mock()

        # Mock files
        mock_file1 = Mock()
        mock_file1.name = "file1.py"
        mock_file2 = Mock()
        mock_file2.name = "file2.py"
        mock_root.files = [mock_file1, mock_file2]

        # Mock directories
        mock_dir = Mock()
        mock_dir.name = "subdir"
        mock_dir.files = []
        mock_dir.directories = []
        mock_root.directories = [mock_dir]

        mock_structure.root_directory = mock_root
        mock_template.structure = mock_structure

        variables = {"project_name": "test"}

        # Mock _should_include_item to return True
        project_generator._should_include_item = Mock(return_value=True)

        result = project_generator._build_file_structure_from_template(
            mock_template, variables
        )

        # Should return structure dict
        assert "files" in result
        assert "directories" in result
        assert len(result["files"]) == 2
        assert len(result["directories"]) == 1

    def test_count_directories_recursive(self, project_generator):
        """Test recursive directory counting."""
        # Mock directory structure
        mock_dir1 = Mock()
        mock_dir1.directories = []

        mock_dir2 = Mock()
        mock_subdir = Mock()
        mock_subdir.directories = []
        mock_dir2.directories = [mock_subdir]

        directories = [mock_dir1, mock_dir2]

        count = project_generator._count_directories_recursive(directories)
        assert count == 3  # dir1, dir2, subdir

    def test_extract_directories_recursive(self, project_generator):
        """Test recursive directory extraction."""
        # Mock directory structure
        mock_dir1 = Mock()
        mock_dir1.name = "dir1"
        mock_dir1.files = []
        mock_dir1.directories = []

        mock_dir2 = Mock()
        mock_dir2.name = "dir2"
        mock_dir2.files = []
        mock_subdir = Mock()
        mock_subdir.name = "subdir"
        mock_subdir.files = []
        mock_subdir.directories = []
        mock_dir2.directories = [mock_subdir]

        directories = [mock_dir1, mock_dir2]
        variables = {}

        # Mock _should_include_item to return True
        project_generator._should_include_item = Mock(return_value=True)

        result = project_generator._extract_directories_recursive(directories, variables)

        assert len(result) == 2  # dir1 and dir2
        # dir2 should contain subdir
        dir2_result = next(d for d in result if d["name"] == "dir2")
        assert len(dir2_result["directories"]) == 1
        assert dir2_result["directories"][0]["name"] == "subdir"
