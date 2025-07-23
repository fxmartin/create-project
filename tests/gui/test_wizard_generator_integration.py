# ABOUTME: Integration tests for wizard and project generator connection
# ABOUTME: Tests project generation flow from UI through to completion

"""
Integration tests for wizard-generator connection.

Tests the complete flow from wizard UI through project generation,
including progress updates, error handling, and success scenarios.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PyQt6.QtWidgets import QProgressDialog

from create_project.ai.ai_service import AIService
from create_project.core.project_generator import GenerationResult
from create_project.gui.wizard.wizard import (
    ProjectGenerationThread,
    ProjectWizard,
    WizardData,
)
from create_project.templates.engine import TemplateEngine
from create_project.templates.schema import (
    DirectoryItem,
    FileItem,
    ProjectStructure,
    Template,
    TemplateCategory,
    TemplateMetadata,
)


class TestProjectGenerationThread:
    """Test the project generation thread."""

    def test_thread_initialization(self):
        """Test thread is properly initialized with dependencies."""
        # Create mocks
        template_engine = Mock(spec=TemplateEngine)
        template_loader = Mock()
        wizard_data = WizardData(
            template_id="test-template",
            project_name="test_project"
        )
        ai_service = Mock(spec=AIService)

        # Create thread
        thread = ProjectGenerationThread(
            template_engine=template_engine,
            template_loader=template_loader,
            wizard_data=wizard_data,
            ai_service=ai_service
        )

        assert thread.template_engine == template_engine
        assert thread.template_loader == template_loader
        assert thread.wizard_data == wizard_data
        assert thread.ai_service == ai_service
        assert thread._cancelled is False

    def test_thread_run_success(self, qtbot):
        """Test successful project generation in thread."""
        # Create mocks
        template_engine = Mock(spec=TemplateEngine)
        template_loader = Mock()
        wizard_data = WizardData(
            template_id="test-template",
            template_name="Test Template",
            project_name="test_project",
            author="Test Author",
            version="0.1.0",
            location=Path("/tmp"),
            init_git=True,
            create_venv=True,
            venv_tool="uv"
        )

        # Mock template
        mock_template = Mock(spec=Template)
        mock_template.name = "Test Template"
        mock_template.structure = Mock(spec=ProjectStructure)

        # Set up mocks
        template_loader.list_templates.return_value = [
            {
                "template_id": "test-template",
                "file_path": "/path/to/template.yaml"
            }
        ]
        template_engine.load_template.return_value = mock_template

        # Create thread
        thread = ProjectGenerationThread(
            template_engine=template_engine,
            template_loader=template_loader,
            wizard_data=wizard_data,
            ai_service=None
        )

        # Mock ProjectGenerator
        with patch("create_project.gui.wizard.wizard.ProjectGenerator") as mock_generator_class:
            mock_generator = Mock()
            mock_generator_class.return_value = mock_generator

            # Mock successful generation
            mock_result = GenerationResult(
                success=True,
                target_path=Path("/tmp/test_project"),
                template_name="Test Template",
                files_created=[],
                errors=[]
            )
            mock_generator.generate.return_value = mock_result

            # Connect signals to track emissions
            progress_emissions = []
            finished_emissions = []

            thread.progress.connect(lambda p, m: progress_emissions.append((p, m)))
            thread.finished.connect(lambda s, m: finished_emissions.append((s, m)))

            # Run thread
            thread.run()

            # Verify signals emitted
            assert len(progress_emissions) >= 2
            assert progress_emissions[0] == (0, "Starting project generation...")
            assert progress_emissions[1] == (20, "Creating project structure...")

            assert len(finished_emissions) == 1
            print(f"Finished emissions: {finished_emissions}")  # Debug
            assert finished_emissions[0][0] is True  # Success
            assert "successfully" in finished_emissions[0][1]

    def test_thread_run_failure(self, qtbot):
        """Test failed project generation in thread."""
        # Create mocks
        template_engine = Mock(spec=TemplateEngine)
        template_loader = Mock()
        wizard_data = WizardData(
            template_id="test-template",
            project_name="test_project",
            location=Path("/tmp")
        )

        # Template not found
        template_loader.list_templates.return_value = []

        # Create thread
        thread = ProjectGenerationThread(
            template_engine=template_engine,
            template_loader=template_loader,
            wizard_data=wizard_data,
            ai_service=None
        )

        # Connect signals
        finished_emissions = []
        thread.finished.connect(lambda s, m: finished_emissions.append((s, m)))

        # Run thread
        thread.run()

        # Verify failure signal
        assert len(finished_emissions) == 1
        assert finished_emissions[0][0] is False  # Failure
        assert "not found" in finished_emissions[0][1]

    def test_thread_cancellation(self):
        """Test thread cancellation."""
        thread = ProjectGenerationThread(
            template_engine=Mock(),
            template_loader=Mock(),
            wizard_data=WizardData(),
            ai_service=None
        )

        assert thread._cancelled is False
        thread.cancel()
        assert thread._cancelled is True


class TestWizardGeneratorIntegration:
    """Test the complete wizard to generator integration."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for wizard."""
        config_manager = MagicMock()  # Use MagicMock to allow any method
        template_engine = Mock(spec=TemplateEngine)
        template_loader = Mock()
        ai_service = Mock(spec=AIService)

        # Configure mocks
        config_manager.get.return_value = {
            "author": "Default Author",
            "default_location": str(Path.home())
        }

        template_loader.list_templates.return_value = [
            {
                "template_id": "python-library",
                "name": "Python Library",
                "file_path": "/templates/python_library.yaml"
            }
        ]

        return {
            "config_manager": config_manager,
            "template_engine": template_engine,
            "template_loader": template_loader,
            "ai_service": ai_service
        }

    def test_wizard_create_button_triggers_generation(self, qtbot, mock_dependencies):
        """Test that clicking Create button in review step triggers generation."""
        # Create wizard
        wizard = ProjectWizard(**mock_dependencies)
        qtbot.addWidget(wizard)

        # Set wizard data
        wizard.wizard_data = WizardData(
            template_id="python-library",
            template_name="Python Library",
            project_name="test_project",
            author="Test Author",
            version="0.1.0",
            location=Path("/tmp"),
            init_git=True,
            create_venv=True
        )

        # Navigate to review page
        wizard.setCurrentId(wizard.PAGE_REVIEW)
        review_page = wizard.currentPage()

        # Mock _start_generation
        wizard._start_generation = Mock()

        # Click create button
        review_page.create_clicked.emit()

        # Verify generation started
        wizard._start_generation.assert_called_once()

    def test_progress_dialog_updates(self, qtbot, mock_dependencies):
        """Test progress dialog receives updates during generation."""
        # Create wizard
        wizard = ProjectWizard(**mock_dependencies)
        qtbot.addWidget(wizard)

        # Set wizard data
        wizard.wizard_data = WizardData(
            template_id="python-library",
            project_name="test_project",
            location=Path("/tmp")
        )

        # Start generation
        wizard._start_generation()

        # Verify progress dialog created
        assert wizard.progress_dialog is not None
        assert isinstance(wizard.progress_dialog, QProgressDialog)
        assert wizard.progress_dialog.windowTitle() == "Project Generation"

        # Verify thread created and started
        assert wizard.generation_thread is not None

        # Simulate progress update
        wizard._on_generation_progress(50, "Processing templates...")

        # Verify dialog updated
        assert wizard.progress_dialog.value() == 50
        assert wizard.progress_dialog.labelText() == "Processing templates..."

    def test_successful_generation_shows_message(self, qtbot, mock_dependencies):
        """Test successful generation shows success message."""
        # Create wizard
        wizard = ProjectWizard(**mock_dependencies)
        qtbot.addWidget(wizard)

        wizard.wizard_data = WizardData(
            project_name="test_project",
            location=Path("/tmp")
        )

        # Create progress dialog
        wizard.progress_dialog = QProgressDialog()

        # Mock QMessageBox
        with patch("create_project.gui.wizard.wizard.QMessageBox") as mock_msgbox:
            # Simulate successful generation
            wizard._on_generation_finished(True, "Project created successfully!")

            # Verify progress dialog closed
            assert wizard.progress_dialog is None

            # Verify success message shown
            mock_msgbox.information.assert_called_once()
            args = mock_msgbox.information.call_args[0]
            assert args[1] == "Success"
            assert "successfully" in args[2]

    def test_failed_generation_shows_error(self, qtbot, mock_dependencies):
        """Test failed generation shows error dialog."""
        # Create wizard with AI service
        wizard = ProjectWizard(**mock_dependencies)
        qtbot.addWidget(wizard)

        wizard.wizard_data = WizardData()
        wizard.progress_dialog = QProgressDialog()

        # Mock AI service as available
        wizard.ai_service.is_available.return_value = True

        # Mock ErrorDialog
        with patch("create_project.gui.wizard.wizard.ErrorDialog") as mock_error_dialog:
            # Simulate failed generation
            error_message = "Failed to create project: Permission denied"
            wizard._on_generation_finished(False, error_message)

            # Verify error dialog shown with AI service
            mock_error_dialog.assert_called_once()
            args = mock_error_dialog.call_args
            assert error_message in args[0]
            assert args[1]["ai_service"] == wizard.ai_service

    def test_cancellation_handling(self, qtbot, mock_dependencies):
        """Test cancellation of generation process."""
        # Create wizard
        wizard = ProjectWizard(**mock_dependencies)
        qtbot.addWidget(wizard)

        wizard.wizard_data = WizardData(
            template_id="python-library",
            project_name="test_project",
            location=Path("/tmp")
        )

        # Start generation
        wizard._start_generation()

        # Mock thread cancel
        wizard.generation_thread.cancel = Mock()

        # Cancel via progress dialog
        wizard.progress_dialog.canceled.emit()

        # Verify thread cancelled
        wizard.generation_thread.cancel.assert_called_once()

    def test_wizard_data_flow_to_generator(self, qtbot, mock_dependencies):
        """Test wizard data correctly flows to project generator."""
        # Create wizard
        wizard = ProjectWizard(**mock_dependencies)
        qtbot.addWidget(wizard)

        # Set complete wizard data
        wizard.wizard_data = WizardData(
            template_id="python-library",
            template_name="Python Library",
            project_name="my_project",
            author="John Doe",
            version="1.0.0",
            description="A test project",
            location=Path("/home/user/projects"),
            license="MIT",
            init_git=True,
            create_venv=True,
            venv_tool="uv",
            additional_options={
                "include_tests": True,
                "include_docs": False
            }
        )

        # Mock template
        mock_template = Mock(spec=Template)
        mock_dependencies["template_loader"].list_templates.return_value = [{
            "template_id": "python-library",
            "file_path": "/template.yaml"
        }]
        mock_dependencies["template_engine"].load_template.return_value = mock_template

        # Mock ProjectGenerator
        with patch("create_project.gui.wizard.wizard.ProjectGenerator") as mock_generator_class:
            mock_generator = Mock()
            mock_generator_class.return_value = mock_generator
            mock_generator.generate.return_value = GenerationResult(
                success=True,
                target_path=Path("/home/user/projects/my_project"),
                template_name="Python Library",
                files_created=[],
                errors=[]
            )

            # Start generation
            wizard._start_generation()
            wizard.generation_thread.run()

            # Verify generator called with correct parameters
            mock_generator.generate.assert_called_once()
            call_args = mock_generator.generate.call_args

            # Check template
            assert call_args[1]["template"] == mock_template

            # Check variables
            variables = call_args[1]["variables"]
            assert variables["project_name"] == "my_project"
            assert variables["author"] == "John Doe"
            assert variables["version"] == "1.0.0"
            assert variables["description"] == "A test project"
            assert variables["license"] == "MIT"
            assert variables["include_tests"] is True
            assert variables["include_docs"] is False

            # Check target path
            assert call_args[1]["target_path"] == Path("/home/user/projects/my_project")

            # Check options
            options = call_args[1]["options"]
            assert options.create_git_repo is True
            assert options.create_venv is True
            assert options.venv_tool == "uv"
            assert options.enable_ai_assistance is False  # No AI service

    @pytest.mark.integration
    def test_end_to_end_project_creation(self, qtbot, mock_dependencies, tmp_path):
        """Test complete end-to-end project creation flow."""
        # Use real template engine for this test
        template_engine = TemplateEngine()
        mock_dependencies["template_engine"] = template_engine

        # Create test template
        test_template = Template(
            metadata=TemplateMetadata(
                name="Test Template",
                description="A test template",
                version="1.0.0",
                category=TemplateCategory.LIBRARY,
                author="Test Author"
            ),
            structure=ProjectStructure(
                root_directory=DirectoryItem(
                    name="project_root",
                    files=[
                        FileItem(name="README.md", content="# {{ project_name }}")
                    ]
                )
            ),
            variables=[]
        )

        # Mock template loading
        mock_dependencies["template_loader"].list_templates.return_value = [{
            "template_id": "test-template",
            "file_path": "test.yaml"
        }]
        template_engine.load_template = Mock(return_value=test_template)

        # Create wizard
        wizard = ProjectWizard(**mock_dependencies)
        qtbot.addWidget(wizard)

        # Set wizard data
        project_path = tmp_path / "test_project"
        wizard.wizard_data = WizardData(
            template_id="test-template",
            template_name="Test Template",
            project_name="test_project",
            author="Test Author",
            version="0.1.0",
            location=tmp_path,
            init_git=False,  # Disable git for test
            create_venv=False  # Disable venv for test
        )

        # Track signals
        project_created_signal = []
        wizard.project_created.connect(lambda p: project_created_signal.append(p))

        # Start generation
        wizard._start_generation()

        # Run the thread synchronously for testing
        wizard.generation_thread.run()

        # Process the finished signal
        success_message = f"Project created successfully at {project_path}"
        wizard._on_generation_finished(True, success_message)

        # Verify project created signal emitted
        assert len(project_created_signal) == 1
        assert project_created_signal[0] == project_path
