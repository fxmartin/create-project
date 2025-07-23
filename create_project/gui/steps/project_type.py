# ABOUTME: Project type selection wizard step
# ABOUTME: Displays available templates with preview pane

from typing import TYPE_CHECKING, Any, Optional, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from create_project.gui.wizard.base_step import WizardStep
from create_project.templates.schema.template import Template

if TYPE_CHECKING:
    pass


class ProjectTypeStep(WizardStep):
    """First wizard step for selecting project type from available templates."""

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize the project type selection step."""
        # Initialize UI elements - will be set in _setup_ui
        self.template_list: QListWidget
        self.preview_browser: QTextBrowser
        self.templates: dict[str, Template] = {}

        super().__init__(
            "Select Project Type", "Choose a template for your new project", parent
        )

    def _setup_ui(self) -> None:
        """Set up the user interface for this step."""
        # Create splitter for list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Template list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)

        list_label = QLabel("Available Templates:")
        list_layout.addWidget(list_label)

        self.template_list = QListWidget()
        self.template_list.itemSelectionChanged.connect(self.on_template_selected)
        list_layout.addWidget(self.template_list)

        # Right side: Preview pane
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        preview_label = QLabel("Template Details:")
        preview_layout.addWidget(preview_label)

        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(True)
        preview_layout.addWidget(self.preview_browser)

        # Add widgets to splitter
        splitter.addWidget(list_widget)
        splitter.addWidget(preview_widget)
        splitter.setSizes([300, 400])  # Initial sizes

        # Add splitter to the main layout provided by base class
        main_layout = cast(QVBoxLayout, self.layout)
        main_layout.addWidget(splitter)

        # Load templates after UI is set up
        self.load_templates()

    def _connect_signals(self) -> None:
        """Connect signals for this step."""
        # Template selection is connected in _setup_ui
        pass

    def load_templates(self) -> None:
        """Load available templates from the template loader."""
        wizard = self.wizard()
        if (
            not wizard
            or not hasattr(wizard, "template_loader")
            or not wizard.template_loader
        ):
            return

        try:
            # Get list of available templates
            templates = wizard.template_loader.list_templates()

            # Clear existing items
            self.template_list.clear()
            self.templates.clear()

            # Add templates to the list
            if templates:
                for template_data in templates:
                    template_name = template_data.get("name", "Unknown Template")
                    # Store template data (convert dict to simple storage)
                    self.templates[template_name] = template_data

                    # Create list item
                    item = QListWidgetItem(template_name)
                    item.setData(Qt.ItemDataRole.UserRole, template_name)

                    # Add brief description as tooltip
                    if template_data.get("description"):
                        item.setToolTip(template_data["description"][:100] + "...")

                    self.template_list.addItem(item)
            else:
                # Fallback: Create some sample templates for demonstration
                sample_templates = [
                    {
                        "name": "Python Library",
                        "description": "A complete Python library package with testing and documentation",
                        "version": "1.0.0",
                        "author": "Template System",
                        "category": "library",
                        "tags": ["python", "library", "package"],
                        "structure": "Standard Python package structure",
                    },
                    {
                        "name": "CLI Script",
                        "description": "A command-line script with argument parsing",
                        "version": "1.0.0",
                        "author": "Template System",
                        "category": "script",
                        "tags": ["python", "cli", "script"],
                        "structure": "Simple script structure",
                    },
                ]

                for template_data in sample_templates:
                    template_name = template_data["name"]
                    self.templates[template_name] = template_data

                    item = QListWidgetItem(template_name)
                    item.setData(Qt.ItemDataRole.UserRole, template_name)
                    item.setToolTip(template_data["description"])

                    self.template_list.addItem(item)

            # Select first item if available
            if self.template_list.count() > 0:
                self.template_list.setCurrentRow(0)

        except Exception as e:
            # Clear any partially loaded data
            self.template_list.clear()
            self.templates.clear()
            self.show_error(f"Failed to load templates: {str(e)}")

    def on_template_selected(self) -> None:
        """Handle template selection and update preview."""
        current_item = self.template_list.currentItem()
        if not current_item:
            self.preview_browser.clear()
            return

        template_id = current_item.data(Qt.ItemDataRole.UserRole)
        template = self.templates.get(template_id)

        if not template:
            self.preview_browser.clear()
            return

        # Build preview HTML
        if isinstance(template, dict):
            # Handle dict-based template (fallback)
            html_parts = [
                f"<h2>{template.get('name', 'Unknown Template')}</h2>",
                f"<p><b>Description:</b> {template.get('description', 'No description available')}</p>",
                f"<p><b>Version:</b> {template.get('version', 'N/A')}</p>",
                f"<p><b>Author:</b> {template.get('author', 'N/A')}</p>",
                f"<p><b>Category:</b> {template.get('category', 'N/A')}</p>",
            ]

            if template.get("tags"):
                tags_str = ", ".join(template["tags"])
                html_parts.append(f"<p><b>Tags:</b> {tags_str}</p>")

            if template.get("structure"):
                html_parts.append("<h3>Project Structure:</h3>")
                html_parts.append("<pre>")
                html_parts.append(template["structure"])
                html_parts.append("</pre>")
        else:
            # Handle Template object (proper format)
            html_parts = [
                f"<h2>{template.name}</h2>",
                f"<p><b>Description:</b> {template.metadata.description}</p>",
                f"<p><b>Version:</b> {template.metadata.version}</p>",
                f"<p><b>Author:</b> {template.metadata.author}</p>",
                f"<p><b>Category:</b> {template.metadata.category.value}</p>",
            ]

            if template.metadata.tags:
                tags_str = ", ".join(template.metadata.tags)
                html_parts.append(f"<p><b>Tags:</b> {tags_str}</p>")

            if (
                hasattr(template, "compatibility")
                and template.compatibility.dependencies
            ):
                html_parts.append("<h3>Dependencies:</h3><ul>")
                for dep in template.compatibility.dependencies:
                    html_parts.append(f"<li>{dep}</li>")
                html_parts.append("</ul>")

            if template.structure:
                html_parts.append("<h3>Project Structure:</h3>")
                html_parts.append("<pre>")
                html_parts.append(self._format_structure(template.structure))
                html_parts.append("</pre>")

        self.preview_browser.setHtml("\n".join(html_parts))

        # Store selected template in wizard data
        wizard = self.wizard()
        if wizard and hasattr(wizard, "data"):
            wizard.data.template_id = template_id
            # Also store the template object for later use
            template = self.templates.get(template_id)
            if template and isinstance(template, dict):
                wizard.data.template_name = template.get("name")
                # Store the file path if available
                if "file_path" in template:
                    wizard.data.template_path = template["file_path"]

    def _format_structure(self, structure: Any, indent: int = 0) -> str:
        """Format template structure for display."""
        if hasattr(structure, "root_directory"):
            # It's a ProjectStructure
            root = structure.root_directory
            return self._format_directory_item(root, indent)
        else:
            # It's a DirectoryItem
            return self._format_directory_item(structure, indent)

    def _format_directory_item(self, directory: Any, indent: int = 0) -> str:
        """Format a single directory item."""
        lines = []
        prefix = "  " * indent

        # Add subdirectories
        if hasattr(directory, "directories") and directory.directories:
            for subdir in directory.directories:
                lines.append(f"{prefix}{subdir.name}/")
                # Recursively format subdirectories
                subdir_lines = self._format_directory_item(subdir, indent + 1)
                if subdir_lines:
                    lines.append(subdir_lines)

        # Add files
        if hasattr(directory, "files") and directory.files:
            for file_item in directory.files:
                lines.append(f"{prefix}{file_item.name}")

        return "\n".join(lines)

    def validate_page(self) -> bool:
        """Validate that a template has been selected."""
        if not self.template_list.currentItem():
            self.show_error("Please select a project template")
            return False

        # Ensure template is stored in wizard data
        wizard = self.wizard()
        if wizard and hasattr(wizard, "data") and not wizard.data.template_id:
            current_item = self.template_list.currentItem()
            if current_item:
                wizard.data.template_id = current_item.data(Qt.ItemDataRole.UserRole)

        return True

    def initializePage(self) -> None:
        """Called when the page is shown."""
        super().initializePage()
        # Reload templates in case they changed
        self.load_templates()

    def cleanupPage(self) -> None:
        """Called when navigating away from the page."""
        super().cleanupPage()
        # Keep selection when going back
