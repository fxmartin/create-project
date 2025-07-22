# ABOUTME: Options configuration step for project wizard
# ABOUTME: Provides dynamic options based on selected template including license, Git, and venv settings

"""
Options configuration wizard step.

This module implements the options configuration step in the project creation
wizard. It provides:
- License selection with preview functionality
- Git initialization settings
- Virtual environment tool selection
- Dynamic template-specific options
"""

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from create_project.gui.wizard.base_step import WizardStep
from create_project.licenses.manager import LicenseManager
from create_project.templates.schema import Template, TemplateVariable
from create_project.utils.logger import get_logger

logger = get_logger(__name__)


class OptionsStep(WizardStep):
    """Options configuration step in the project wizard."""

    # Signal emitted when license preview is requested
    license_preview_requested = pyqtSignal(str)  # license_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the options step.

        Args:
            parent: Parent widget
        """
        # Initialize attributes before calling super().__init__
        # License manager for license operations
        self.license_manager = LicenseManager()

        # Track dynamic widgets for cleanup
        self.dynamic_widgets: List[QWidget] = []

        # Option widgets mapping
        self.option_widgets: Dict[str, QWidget] = {}
        
        super().__init__(
            title="Configuration Options",
            subtitle="Configure project options",
            parent=parent,
        )

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Create scroll area for options
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)

        # Main content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)

        # Universal options group
        self.universal_group = QGroupBox("Project Settings")
        universal_layout = QFormLayout()
        universal_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        # License selection
        license_layout = QHBoxLayout()
        self.license_combo = QComboBox()
        self.license_combo.setMinimumWidth(200)

        # Populate license options
        self._populate_licenses()

        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self._on_preview_license)
        self.preview_button.setMaximumWidth(100)

        license_layout.addWidget(self.license_combo, 1)
        license_layout.addWidget(self.preview_button)
        universal_layout.addRow("License:", license_layout)

        # Git initialization
        self.git_checkbox = QCheckBox("Initialize Git repository")
        self.git_checkbox.setChecked(True)
        universal_layout.addRow("Version Control:", self.git_checkbox)

        # Virtual environment tool
        self.venv_combo = QComboBox()
        self.venv_combo.addItems(["uv (recommended)", "virtualenv", "venv", "none"])
        self.venv_combo.setCurrentIndex(0)
        universal_layout.addRow("Virtual Environment:", self.venv_combo)

        self.universal_group.setLayout(universal_layout)
        content_layout.addWidget(self.universal_group)

        # Template-specific options group (will be populated dynamically)
        self.template_group = QGroupBox("Template Options")
        self.template_layout = QFormLayout()
        self.template_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self.template_group.setLayout(self.template_layout)
        self.template_group.hide()  # Hidden by default
        content_layout.addWidget(self.template_group)

        # Add stretch to push content to top
        content_layout.addStretch()

        # Set scroll area content
        scroll_area.setWidget(content_widget)

        # Add to main layout
        self.layout.addWidget(scroll_area)

        # Store widgets for later access
        self.option_widgets["license"] = self.license_combo
        self.option_widgets["git_init"] = self.git_checkbox
        self.option_widgets["venv_tool"] = self.venv_combo

        logger.debug("Options step UI setup complete")

    def _populate_licenses(self) -> None:
        """Populate the license combo box."""
        try:
            # Add "No License" option first
            self.license_combo.addItem("No License", None)

            # Get available license IDs
            license_ids = self.license_manager.get_available_licenses()
            
            # Add available licenses
            for license_id in license_ids:
                license = self.license_manager.get_license(license_id)
                display_name = f"{license.name} ({license_id})"
                self.license_combo.addItem(display_name, license_id)

            # Set MIT as default if available
            for i in range(self.license_combo.count()):
                if self.license_combo.itemData(i) == "MIT":
                    self.license_combo.setCurrentIndex(i)
                    break

        except Exception as e:
            logger.error(f"Failed to populate licenses: {e}")
            self.license_combo.addItem("No License", None)

    def _on_preview_license(self) -> None:
        """Handle license preview button click."""
        license_id = self.license_combo.currentData()
        if license_id:
            self.license_preview_requested.emit(license_id)
            logger.debug(f"License preview requested for: {license_id}")

    def initializePage(self) -> None:
        """Initialize the page with wizard data."""
        super().initializePage()

        # Get selected template
        wizard = self.wizard()
        if not wizard or not hasattr(wizard, "data"):
            logger.error("No wizard or data available")
            return
            
        template_id = wizard.data.template_id
        if not template_id:
            logger.error("No template selected")
            return

        # Load template to get options
        try:
            template = self._load_template(template_id)
            if template and hasattr(template, 'variables') and template.variables:
                self._populate_template_options(template.variables)
            else:
                self.template_group.hide()
        except Exception as e:
            logger.error(f"Failed to load template options: {e}")
            self.template_group.hide()

        # Set author from config if available
        if hasattr(self.wizard(), "config_manager"):
            default_author = self.wizard().config_manager.get_setting(
                "general.default_author", ""
            )
            if default_author and "author" in self.option_widgets:
                widget = self.option_widgets["author"]
                if isinstance(widget, QLineEdit):
                    widget.setText(default_author)

        logger.debug("Options step initialized")

    def _load_template(self, template_id: str) -> Optional[Template]:
        """
        Load template by ID.

        Args:
            template_id: Template identifier

        Returns:
            Template schema or None if not found
        """
        if hasattr(self.wizard(), "template_engine"):
            try:
                # Try to get template path from wizard data
                wizard = self.wizard()
                if hasattr(wizard, "data") and hasattr(wizard.data, "template_path"):
                    template_path = wizard.data.template_path
                    if template_path:
                        return self.wizard().template_engine.load_template(template_path)
                
                # Fallback: Try to find template by name in the builtin directory
                from pathlib import Path
                builtin_dir = Path("create_project/templates/builtin")
                for yaml_file in builtin_dir.glob("*.yaml"):
                    try:
                        metadata = self.wizard().template_loader.load_template_metadata(yaml_file)
                        if metadata.get("name") == template_id:
                            return self.wizard().template_engine.load_template(yaml_file)
                    except:
                        pass
                
                logger.error(f"Template {template_id} not found")
            except Exception as e:
                logger.error(f"Failed to load template {template_id}: {e}")
        return None

    def _populate_template_options(self, options: List[TemplateVariable]) -> None:
        """
        Populate template-specific options.

        Args:
            options: List of template options
        """
        # Clear existing dynamic widgets
        self._clear_dynamic_widgets()

        # For now, put all options in General category since TemplateVariable doesn't have groups
        categorized: Dict[str, List[TemplateVariable]] = {"General": options}

        # Create widgets for each option
        has_options = False
        for category, category_options in categorized.items():
            if category != "General":
                # Add category separator
                separator = QLabel(f"<b>{category}</b>")
                self.template_layout.addRow(separator)
                self.dynamic_widgets.append(separator)

            for option in category_options:
                widget = self._create_option_widget(option)
                if widget:
                    has_options = True
                    # Use description as label, fallback to name
                    display_label = option.description or option.name
                    label = (
                        f"{display_label}:"
                        if option.required
                        else f"{display_label} (optional):"
                    )
                    self.template_layout.addRow(label, widget)
                    self.dynamic_widgets.append(widget)
                    self.option_widgets[option.name] = widget

        # Show/hide template group based on whether we have options
        self.template_group.setVisible(has_options)

    def _create_option_widget(self, option: TemplateVariable) -> Optional[QWidget]:
        """
        Create a widget for a template option.

        Args:
            option: Template option definition

        Returns:
            Widget for the option or None
        """
        try:
            from create_project.templates.schema.variables import VariableType
            
            if option.type in [VariableType.STRING, VariableType.EMAIL, VariableType.URL, VariableType.PATH]:
                widget = QLineEdit()
                if option.default:
                    widget.setText(str(option.default))
                if option.help_text:
                    widget.setToolTip(option.help_text)
                return widget

            elif option.type == VariableType.BOOLEAN:
                widget = QCheckBox()
                if option.default is not None:
                    widget.setChecked(bool(option.default))
                if option.help_text:
                    widget.setToolTip(option.help_text)
                return widget

            elif option.type == VariableType.CHOICE:
                widget = QComboBox()
                if option.choices:
                    # Add choice items
                    for choice in option.choices:
                        widget.addItem(choice.get_display_label(), choice.value)
                    # Set default
                    if option.default:
                        index = widget.findData(option.default)
                        if index >= 0:
                            widget.setCurrentIndex(index)
                if option.help_text:
                    widget.setToolTip(option.help_text)
                return widget

            else:
                logger.warning(f"Unsupported variable type for GUI: {option.type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create widget for option {option.name}: {e}")
            return None

    def _clear_dynamic_widgets(self) -> None:
        """Clear all dynamic widgets from the template layout."""
        for widget in self.dynamic_widgets:
            self.template_layout.removeWidget(widget)
            widget.deleteLater()
        self.dynamic_widgets.clear()

        # Clear from option widgets map
        keys_to_remove = []
        for key in self.option_widgets:
            if key not in ["license", "git_init", "venv_tool"]:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self.option_widgets[key]

    def validatePage(self) -> bool:
        """
        Validate the page before allowing navigation.

        Returns:
            True if validation passes
        """
        # Check required template options
        wizard = self.wizard()
        if wizard and hasattr(wizard, "data"):
            template_id = wizard.data.template_id
            if template_id:
                try:
                    template = self._load_template(template_id)
                    if template and hasattr(template, 'variables') and template.variables:
                        for option in template.variables:
                            if option.required and option.name in self.option_widgets:
                                widget = self.option_widgets[option.name]

                                if (
                                    isinstance(widget, QLineEdit)
                                    and not widget.text().strip()
                                ):
                                    self.show_error(f"{option.description or option.name} is required")
                                    widget.setFocus()
                                    return False

                                elif (
                                    isinstance(widget, QComboBox)
                                    and widget.currentIndex() < 0
                                ):
                                    self.show_error(f"{option.description or option.name} must be selected")
                                    widget.setFocus()
                                    return False

                except Exception as e:
                    logger.error(f"Failed to validate template options: {e}")

        return super().validatePage()

    def cleanupPage(self) -> None:
        """Clean up when leaving the page."""
        # Collect all option values
        options: Dict[str, Any] = {}

        # Universal options
        license_id = self.license_combo.currentData()
        options["license"] = license_id
        options["git_init"] = self.git_checkbox.isChecked()

        # Virtual environment tool (extract actual tool name)
        venv_text = self.venv_combo.currentText()
        if "uv" in venv_text:
            options["venv_tool"] = "uv"
        elif venv_text == "none":
            options["venv_tool"] = None
        else:
            options["venv_tool"] = venv_text

        # Template-specific options
        for name, widget in self.option_widgets.items():
            if name not in ["license", "git_init", "venv_tool"]:
                if isinstance(widget, QLineEdit):
                    options[name] = widget.text().strip()
                elif isinstance(widget, QCheckBox):
                    options[name] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    options[name] = widget.currentText()

        # Update wizard data
        wizard = self.wizard()
        if wizard and hasattr(wizard, "data"):
            # Store universal options
            wizard.data.license = options.get("license")
            wizard.data.init_git = options.get("git_init", True)
            wizard.data.create_venv = options.get("venv_tool") is not None
            wizard.data.venv_tool = options.get("venv_tool")
            
            # Store template-specific options
            wizard.data.additional_options = {
                k: v for k, v in options.items() 
                if k not in ["license", "git_init", "venv_tool"]
            }

        logger.debug(f"Updated wizard data: options={options}")

        super().cleanupPage()

    def get_options(self) -> Dict[str, Any]:
        """Get all configured options.
        
        Returns:
            Dictionary of option names to values
        """
        options: Dict[str, Any] = {}

        # Universal options
        license_id = self.license_combo.currentData()
        options["license"] = license_id
        options["git_init"] = self.git_checkbox.isChecked()

        # Virtual environment tool 
        venv_text = self.venv_combo.currentText()
        if "uv" in venv_text:
            options["venv_tool"] = "uv"
        elif "virtualenv" in venv_text:
            options["venv_tool"] = "virtualenv"
        elif "venv" in venv_text and "virtualenv" not in venv_text:
            options["venv_tool"] = "venv"
        elif venv_text == "none":
            options["venv_tool"] = "none"
        else:
            options["venv_tool"] = venv_text

        # Template-specific options
        for name, widget in self.option_widgets.items():
            if name not in ["license", "git_init", "venv_tool"]:
                if isinstance(widget, QLineEdit):
                    options[name] = widget.text().strip()
                elif isinstance(widget, QCheckBox):
                    options[name] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    options[name] = widget.currentText()

        return options
