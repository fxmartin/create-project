# ABOUTME: Test suite for options configuration wizard step
# ABOUTME: Tests dynamic options loading, validation, and license preview functionality

"""Test suite for the options configuration wizard step."""

from unittest.mock import Mock

import pytest
from PyQt6.QtWidgets import QCheckBox, QComboBox, QLineEdit

from create_project.gui.steps.options import OptionsStep
from create_project.gui.wizard.wizard import WizardData
from create_project.templates.schema import (
    ChoiceItem,
    Template,
    TemplateVariable,
    VariableType,
)
from create_project.templates.schema.structure import ProjectStructure, TemplateFile


@pytest.fixture
def sample_template():
    """Create a sample template with various options."""
    return Template(
        id="test_template",
        name="Test Template",
        description="Test template for testing",
        version="1.0.0",
        author="Test Author",
        tags=["test"],
        structure=ProjectStructure(
            directories=["src", "tests"],
            files=[TemplateFile(path="README.md", content="# {{project_name}}")],
        ),
        variables=[
            TemplateVariable(
                name="database",
                type=VariableType.CHOICE,
                description="Database backend",
                choices=[
                    ChoiceItem(value="PostgreSQL"),
                    ChoiceItem(value="MySQL"),
                    ChoiceItem(value="SQLite"),
                ],
                default="SQLite",
                required=True,
            ),
            TemplateVariable(
                name="api_framework",
                type=VariableType.STRING,
                description="API framework to use",
                default="FastAPI",
                required=True,
            ),
            TemplateVariable(
                name="include_tests",
                type=VariableType.BOOLEAN,
                description="Include test files",
                default=True,
                required=False,
            ),
            TemplateVariable(
                name="docker",
                type=VariableType.BOOLEAN,
                description="Include Docker configuration",
                default=False,
                required=False,
            ),
        ],
    )


@pytest.fixture
def options_step(qtbot, mock_wizard):
    """Create an OptionsStep instance."""
    step = OptionsStep()
    step._wizard = mock_wizard
    mock_wizard.data = WizardData()
    mock_wizard.data.template_id = "test_template"
    qtbot.addWidget(step)
    return step


@pytest.fixture
def mock_wizard():
    """Create a mock wizard with necessary attributes."""
    wizard = Mock()
    wizard.data = WizardData()
    wizard.config_manager = Mock()
    wizard.config_manager.get_setting.return_value = "Test Author"
    wizard.template_loader = Mock()
    return wizard


class TestOptionsStep:
    """Test suite for OptionsStep class."""

    def test_initialization(self, qtbot):
        """Test OptionsStep initialization."""
        step = OptionsStep()
        qtbot.addWidget(step)

        assert step.title() == "Configuration Options"
        assert step.subTitle() == "Configure project options"
        assert hasattr(step, "license_manager")
        assert hasattr(step, "license_combo")
        assert hasattr(step, "git_checkbox")
        assert hasattr(step, "venv_combo")
        assert hasattr(step, "preview_button")

    def test_license_population(self, options_step):
        """Test that licenses are populated correctly."""
        license_combo = options_step.license_combo

        # Should have at least "No License" option
        assert license_combo.count() > 0
        assert license_combo.itemText(0) == "No License"
        assert license_combo.itemData(0) is None

        # Should have common licenses
        license_texts = [
            license_combo.itemText(i) for i in range(license_combo.count())
        ]
        assert any("MIT" in text for text in license_texts)

    def test_default_values(self, options_step):
        """Test default values for universal options."""
        # Git should be checked by default
        assert options_step.git_checkbox.isChecked()

        # Virtual environment should default to uv
        assert "uv" in options_step.venv_combo.currentText()

    def test_template_options_loading(self, options_step, sample_template):
        """Test loading of template-specific options."""
        # Mock template loader
        options_step._wizard.template_loader.load_template.return_value = (
            sample_template
        )

        # Initialize page
        options_step.initializePage()

        # Template group should be visible
        assert options_step.template_group.isVisible()

        # Check that options are created
        assert "database" in options_step.option_widgets
        assert "api_framework" in options_step.option_widgets
        assert "include_tests" in options_step.option_widgets
        assert "docker" in options_step.option_widgets

        # Check widget types
        assert isinstance(options_step.option_widgets["database"], QComboBox)
        assert isinstance(options_step.option_widgets["api_framework"], QLineEdit)
        assert isinstance(options_step.option_widgets["include_tests"], QCheckBox)
        assert isinstance(options_step.option_widgets["docker"], QCheckBox)

    def test_template_options_defaults(self, options_step, sample_template):
        """Test that template option defaults are set correctly."""
        options_step._wizard.template_loader.load_template.return_value = (
            sample_template
        )
        options_step.initializePage()

        # Check defaults
        database_combo = options_step.option_widgets["database"]
        assert database_combo.currentText() == "SQLite"

        api_framework_edit = options_step.option_widgets["api_framework"]
        assert api_framework_edit.text() == "FastAPI"

        include_tests_check = options_step.option_widgets["include_tests"]
        assert include_tests_check.isChecked()

        docker_check = options_step.option_widgets["docker"]
        assert not docker_check.isChecked()

    def test_no_template_options(self, options_step):
        """Test behavior when template has no options."""
        template = Template(
            id="minimal",
            name="Minimal",
            description="Minimal template",
            version="1.0.0",
            author="Test",
            tags=[],
            structure=ProjectStructure(directories=[], files=[]),
        )

        options_step._wizard.template_loader.load_template.return_value = template
        options_step.initializePage()

        # Template group should be hidden
        assert not options_step.template_group.isVisible()

    def test_validation_required_fields(self, options_step, sample_template):
        """Test validation of required fields."""
        options_step._wizard.template_loader.load_template.return_value = (
            sample_template
        )
        options_step.initializePage()

        # Clear required text field
        api_framework_edit = options_step.option_widgets["api_framework"]
        api_framework_edit.clear()

        # Validation should fail
        assert not options_step.validatePage()

        # Fill required field
        api_framework_edit.setText("Django")
        assert options_step.validatePage()

    def test_cleanup_page(self, options_step, sample_template):
        """Test cleanup and data collection."""
        options_step._wizard.template_loader.load_template.return_value = (
            sample_template
        )
        options_step.initializePage()

        # Set some values
        options_step.license_combo.setCurrentIndex(1)  # Assume MIT
        options_step.git_checkbox.setChecked(False)
        options_step.venv_combo.setCurrentText("virtualenv")

        database_combo = options_step.option_widgets["database"]
        database_combo.setCurrentText("PostgreSQL")

        # Cleanup page
        options_step.cleanupPage()

        # Check wizard data was updated
        wizard_data = options_step._wizard.data
        assert "options" in wizard_data.__dict__

        options = wizard_data.options
        assert options["git_init"] is False
        assert options["venv_tool"] == "virtualenv"
        assert options["database"] == "PostgreSQL"

    def test_license_preview_signal(self, qtbot, options_step):
        """Test license preview signal emission."""
        # Set a license
        if options_step.license_combo.count() > 1:
            options_step.license_combo.setCurrentIndex(1)

            with qtbot.waitSignal(options_step.license_preview_requested) as blocker:
                options_step.preview_button.click()

            # Signal should be emitted with license ID
            assert len(blocker.args) == 1
            assert blocker.args[0] is not None

    @pytest.mark.skip(reason="Requires display")
    def test_dynamic_widget_cleanup(self, options_step, sample_template):
        """Test that dynamic widgets are properly cleaned up."""
        # Load template options twice
        options_step._wizard.template_loader.load_template.return_value = (
            sample_template
        )
        options_step.initializePage()

        initial_widget_count = len(options_step.dynamic_widgets)

        # Load again (simulating navigation back and forth)
        options_step.initializePage()

        # Should have same number of widgets (old ones cleaned up)
        assert len(options_step.dynamic_widgets) == initial_widget_count

    def test_venv_tool_extraction(self, options_step):
        """Test virtual environment tool extraction from combo text."""
        options_step.venv_combo.setCurrentText("uv (recommended)")
        options_step.cleanupPage()

        options = options_step._wizard.data.options
        assert options["venv_tool"] == "uv"

        options_step.venv_combo.setCurrentText("none")
        options_step.cleanupPage()

        options = options_step._wizard.data.options
        assert options["venv_tool"] is None

    def test_error_handling(self, options_step):
        """Test error handling for template loading failures."""
        # Simulate template loading error
        options_step._wizard.template_loader.load_template.side_effect = Exception(
            "Load error"
        )

        # Should not crash
        options_step.initializePage()

        # Template group should be hidden
        assert not options_step.template_group.isVisible()

    def test_author_prefill(self, options_step):
        """Test that author field is prefilled from config."""
        # Create template with author option
        template = Template(
            id="author_test",
            name="Author Test",
            description="Test",
            version="1.0.0",
            author="Test",
            tags=[],
            structure=ProjectStructure(directories=[], files=[]),
            variables=[
                TemplateVariable(
                    name="author",
                    type=VariableType.STRING,
                    description="Author",
                    required=True
                )
            ],
        )

        options_step._wizard.template_loader.load_template.return_value = template
        options_step._wizard.config_manager.get_setting.return_value = "John Doe"

        options_step.initializePage()

        # Author field should be prefilled
        author_edit = options_step.option_widgets.get("author")
        assert author_edit is not None
        assert author_edit.text() == "John Doe"
