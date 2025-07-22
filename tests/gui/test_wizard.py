# ABOUTME: Test suite for the main project creation wizard
# ABOUTME: Tests wizard navigation, validation, and project generation

"""
Test suite for ProjectWizard.

Tests the main wizard functionality including:
- Wizard initialization
- Step navigation
- Field validation
- Project generation
- Error handling
"""

from pathlib import Path

import pytest
from PyQt6.QtCore import Qt

from create_project.gui.wizard import ProjectWizard, WizardData


class TestWizardData:
    """Test suite for the WizardData class."""

    def test_wizard_data_initialization(self):
        """Test WizardData initialization with defaults."""
        data = WizardData()

        assert data.template_id is None
        assert data.template_name is None
        assert data.project_name is None
        assert data.author is None
        assert data.version is None
        assert data.description is None
        assert data.location is None
        assert data.license is None
        assert data.init_git is True
        assert data.create_venv is True
        assert data.venv_tool is None
        assert data.additional_options == {}

    def test_wizard_data_target_path(self):
        """Test target path calculation."""
        data = WizardData()

        # No path when missing components
        assert data.target_path is None

        # Set location only
        data.location = Path("/home/user/projects")
        assert data.target_path is None

        # Set project name
        data.project_name = "my_project"
        assert data.target_path == Path("/home/user/projects/my_project")

    def test_wizard_data_to_variables(self):
        """Test conversion to template variables."""
        data = WizardData(
            project_name="test_project",
            author="Test Author",
            version="1.0.0",
            description="Test description",
            license="MIT",
            additional_options={"include_tests": True, "python_version": "3.9"},
        )

        variables = data.to_variables()

        assert variables["project_name"] == "test_project"
        assert variables["author"] == "Test Author"
        assert variables["version"] == "1.0.0"
        assert variables["description"] == "Test description"
        assert variables["license"] == "MIT"
        assert variables["include_tests"] is True
        assert variables["python_version"] == "3.9"


class TestProjectWizard:
    """Test suite for the ProjectWizard class."""

    def test_wizard_initialization(
        self, qtbot, mock_config_manager, mock_template_engine
    ):
        """Test that the wizard initializes correctly with dependencies."""
        wizard = ProjectWizard(
            config_manager=mock_config_manager, template_engine=mock_template_engine
        )
        qtbot.addWidget(wizard)

        assert wizard is not None
        assert wizard.config_manager == mock_config_manager
        assert wizard.template_engine == mock_template_engine
        assert wizard.ai_service is None  # No AI service provided
        assert wizard.windowTitle() == "Create Python Project"

    def test_wizard_has_expected_pages(
        self, qtbot, mock_config_manager, mock_template_engine
    ):
        """Test that the wizard contains all expected pages."""
        wizard = ProjectWizard(
            config_manager=mock_config_manager, template_engine=mock_template_engine
        )
        qtbot.addWidget(wizard)

        # Expected pages:
        # 1. Project Type Selection
        # 2. Basic Information
        # 3. Location Selection
        # 4. Options Configuration
        # 5. Review and Create
        assert wizard.pageIds() == [0, 1, 2, 3, 4]

        # Check page titles
        expected_titles = [
            "Select Project Type",
            "Basic Information",
            "Project Location",  # Updated to match LocationStep
            "Configure Options",
            "Review and Create",
        ]

        for page_id, expected_title in enumerate(expected_titles):
            page = wizard.page(page_id)
            assert page is not None
            assert page.title() == expected_title

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_navigation_forward(
        self, qtbot, qt_bot_helper, mock_config_manager, mock_template_engine
    ):
        """Test forward navigation through wizard steps."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_navigation_backward(
        self, qtbot, qt_bot_helper, mock_config_manager, mock_template_engine
    ):
        """Test backward navigation through wizard steps."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_validation_blocks_navigation(
        self, qtbot, qt_bot_helper, mock_config_manager, mock_template_engine
    ):
        """Test that validation errors prevent forward navigation."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_cancel_confirmation(
        self, qtbot, qt_bot_helper, mock_config_manager, mock_template_engine
    ):
        """Test that canceling the wizard shows confirmation dialog."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_help_button_functionality(
        self, qtbot, qt_bot_helper, mock_config_manager, mock_template_engine
    ):
        """Test that the help button provides context-sensitive help."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_project_generation_success(
        self, qtbot, qt_bot_helper, mock_config_manager, mock_template_engine
    ):
        """Test successful project generation from wizard."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_project_generation_error_handling(
        self,
        qtbot,
        qt_bot_helper,
        mock_config_manager,
        mock_template_engine,
        mock_ai_service,
    ):
        """Test error handling during project generation."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_wizard_remembers_values_on_back(
        self, qtbot, qt_bot_helper, mock_config_manager, mock_template_engine
    ):
        """Test that wizard preserves entered values when navigating back."""
        pass


class TestWizardIntegration:
    """Integration tests for wizard with backend services."""

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_wizard_loads_templates_from_engine(
        self, qtbot, mock_config_manager, mock_template_engine
    ):
        """Test that wizard correctly loads templates from template engine."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_wizard_saves_settings_to_config(
        self, qtbot, mock_config_manager, mock_template_engine
    ):
        """Test that wizard saves user preferences to configuration."""
        pass

    @pytest.mark.skip(reason="ProjectWizard not yet implemented")
    def test_wizard_uses_ai_service_on_error(
        self, qtbot, mock_config_manager, mock_template_engine, mock_ai_service
    ):
        """Test that wizard uses AI service for error assistance."""
        pass


# Example test that can run now to verify test infrastructure
def test_gui_test_infrastructure_working(qtbot):
    """Verify that GUI test infrastructure is properly set up."""
    from PyQt6.QtWidgets import QPushButton, QWidget

    # Create a simple widget
    widget = QWidget()
    button = QPushButton("Test Button", widget)

    # Add widget to qtbot
    qtbot.addWidget(widget)

    # Verify widget exists
    assert widget is not None
    assert button is not None
    assert button.text() == "Test Button"

    # Test clicking
    clicked = False

    def on_click():
        nonlocal clicked
        clicked = True

    button.clicked.connect(on_click)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

    assert clicked is True
