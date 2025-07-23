# GUI Architecture Documentation

## Overview

The Create Project GUI is built using PyQt6 and follows a modular, wizard-based architecture. The system is designed for maintainability, testability, and extensibility, with clear separation of concerns between UI components, business logic, and data management.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUI Application Layer                    │
├─────────────────────────────────────────────────────────────────┤
│  create_project.gui.app                                        │
│  ├── QApplication Setup                                        │
│  ├── Configuration Loading                                     │
│  ├── Service Initialization                                    │
│  └── Wizard Lifecycle Management                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Wizard Framework                        │
├─────────────────────────────────────────────────────────────────┤
│  create_project.gui.wizard.wizard                             │
│  ├── ProjectWizard (QWizard)                                  │
│  │   ├── Step Management & Navigation                        │
│  │   ├── Data Collection & Validation                        │
│  │   └── Project Generation Orchestration                    │
│  └── ProjectGenerationThread (QThread)                        │
│      ├── Background Project Generation                        │
│      ├── Progress Reporting                                   │
│      └── Error Handling with AI Context                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│    Wizard Steps     │ │      Dialogs        │ │   Custom Widgets    │
├─────────────────────┤ ├─────────────────────┤ ├─────────────────────┤
│ ProjectTypeStep     │ │ ProgressDialog      │ │ ValidatedLineEdit   │
│ BasicInfoStep       │ │ ErrorDialog         │ │ CollapsibleSection  │
│ LocationStep        │ │ AIHelpDialog        │ │ FilePathEdit        │
│ OptionsStep         │ │ SettingsDialog      │ │ LicensePreview      │
│ ReviewStep          │ │                     │ │                     │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Resource Management                        │
├─────────────────────────────────────────────────────────────────┤
│  create_project.resources                                      │
│  ├── StyleManager - QSS stylesheet generation                  │
│  ├── IconManager - Icon loading and caching                    │
│  └── Theme Management - Light/dark theme support               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend Integration                      │
├─────────────────────────────────────────────────────────────────┤
│  ├── ConfigManager - Settings persistence                      │
│  ├── TemplateEngine - Template loading and processing          │
│  ├── ProjectGenerator - Core project generation logic          │
│  └── AIService - Ollama integration for error assistance       │
└─────────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. Application Layer (`create_project.gui.app`)

**Purpose**: Application entry point and lifecycle management.

**Key Responsibilities**:
- PyQt6 application initialization and configuration
- Service dependency injection (ConfigManager, TemplateEngine, AIService)
- Global exception handling and error reporting  
- Application-wide styling and theming

**Key Classes**:
- `main()` - Application entry point
- `setup_application()` - QApplication configuration
- `load_configuration()` - Configuration loading
- `initialize_services()` - Service initialization

### 2. Wizard Framework (`create_project.gui.wizard`)

**Purpose**: Core wizard logic and project generation orchestration.

#### ProjectWizard (QWizard)
- **Navigation Management**: Controls step-by-step workflow
- **Data Collection**: Aggregates user input across all steps
- **Validation Orchestration**: Coordinates validation across steps
- **Signal Coordination**: Manages communication between components

**Key Signals**:
```python
project_created = pyqtSignal(Path)  # Emitted on successful creation
```

#### ProjectGenerationThread (QThread)
- **Background Processing**: Runs project generation without blocking UI
- **Progress Reporting**: Real-time progress updates with percentage and messages
- **Error Context**: Collects comprehensive error information for AI assistance
- **Cancellation Support**: User can cancel long-running operations

**Key Signals**:
```python
progress = pyqtSignal(int, str)           # Progress updates
finished = pyqtSignal(bool, str)          # Completion status
error_occurred = pyqtSignal(object, dict) # Error context for AI help
```

### 3. Wizard Steps (`create_project.gui.steps`)

Each step inherits from `QWizardPage` and implements the step lifecycle:

#### Base Step Pattern
```python
class WizardStepBase(QWizardPage):
    def isComplete(self) -> bool:
        """Return True if step data is valid"""
        
    def validatePage(self) -> bool:
        """Validate before proceeding to next step"""
        
    def initializePage(self):
        """Initialize step when first shown"""
        
    def cleanupPage(self):
        """Cleanup when leaving step"""
```

#### Step Implementations

**ProjectTypeStep**:
- Template selection with rich preview
- Template metadata display (description, tags, dependencies)
- Integration with TemplateEngine for dynamic template loading

**BasicInfoStep**:
- Form-based input with real-time validation
- Project name validation (Python identifier format)
- Semantic version validation
- Author/description collection

**LocationStep**:
- Directory selection with QFileDialog integration
- Path validation (existence, permissions)
- Existing directory warnings
- Real-time path preview

**OptionsStep**:  
- Dynamic options based on selected template
- License selection with preview dialog
- Git initialization toggle
- Virtual environment tool selection
- Template-specific variable collection

**ReviewStep**:
- Collapsible sections for organized data display
- Project structure preview using QTreeWidget
- Final validation before project generation
- Create button triggers generation

### 4. Dialog Components (`create_project.gui.dialogs`)

#### ProgressDialog
- **Modal Progress Display**: Shows generation progress with detailed logging
- **Cancellation Support**: Confirmation dialog prevents accidental cancellation
- **Visual States**: Success (green), error (red), cancelled (orange)
- **Thread-Safe Updates**: Safely receives updates from background thread

#### ErrorDialog  
- **Progressive Disclosure**: Expandable sections for error details
- **AI Help Integration**: "Get AI Help" button when AI service available
- **Clipboard Support**: Copy error details functionality
- **GitHub Integration**: Pre-filled issue reporting

#### AIHelpDialog
- **Streaming Responses**: Real-time AI response display
- **Markdown Rendering**: Basic markdown to HTML conversion
- **Worker Thread**: Non-blocking AI queries using AIQueryWorker
- **Retry Support**: Retry functionality for failed or unsatisfactory responses

#### SettingsDialog
- **Tabbed Interface**: General, AI Settings, Template Paths
- **ConfigManager Integration**: Bidirectional settings synchronization
- **Connection Testing**: Ollama connection validation
- **Template Management**: Add/remove custom template directories

### 5. Custom Widgets (`create_project.gui.widgets`)

#### ValidatedLineEdit
```python
# Real-time regex validation with visual feedback
widget = ValidatedLineEdit(r"^[a-z_][a-z0-9_]*$", "Python identifier")
widget.validationChanged.connect(self.on_validation_change)
```

#### CollapsibleSection
```python
# Animated expand/collapse widget for grouping content
section = CollapsibleSection("Advanced Options")
section.set_content_widget(options_widget)
section.expanded.connect(self.on_section_expanded)
```

#### FilePathEdit
```python
# File/directory selection with integrated browse button
path_edit = FilePathEdit(mode="directory")
path_edit.path_changed.connect(self.on_path_changed)
```

### 6. Resource Management (`create_project.resources`)

#### StyleManager
- **Theme Support**: Light and dark theme variants
- **Component Styling**: Wizard, dialog, and widget-specific styles
- **QSS Generation**: Dynamic stylesheet creation
- **Cache Management**: Performance optimization through style caching

#### IconManager  
- **Icon Loading**: PNG, SVG, ICO format support
- **Theme Variants**: Light/dark icon variants
- **Fallback System**: Graceful degradation when icons missing
- **Category Organization**: Icons organized by functional categories

## Signal/Slot Documentation

### Primary Signal Flow

```
User Input → Step Validation → Wizard Navigation → Data Collection → Project Generation
     ↓              ↓                 ↓                  ↓                    ↓
Step Signals → Validation → Navigation → Data Signals → Generation → Completion
```

### Key Signal Connections

#### Wizard-Level Signals
```python
# Project creation completion
wizard.project_created.connect(on_project_created)

# Error handling with AI assistance  
generation_thread.error_occurred.connect(wizard._on_generation_error)
wizard._on_generation_error.connect(error_dialog.show_with_ai_help)
```

#### Step-Level Signals
```python
# Step completion changes
step.completeChanged.connect(wizard.update_buttons)

# Real-time validation
validated_edit.validationChanged.connect(step.update_completion)

# Template selection
project_type_step.template_selected.connect(wizard.update_template_data)
```

#### Dialog Signals
```python
# Progress updates
generation_thread.progress.connect(progress_dialog.update_progress)

# AI help requests
error_dialog.help_requested.connect(ai_help_dialog.show)

# Settings changes
settings_dialog.settings_changed.connect(config_manager.save_settings)
```

## Navigation Flow

### Wizard Step Sequence

```
1. ProjectTypeStep     │ Template Selection
   ├── Template List   │ • Choose from built-in templates
   ├── Preview Pane    │ • Rich HTML preview
   └── Validation      │ • Template selection required
                       │
2. BasicInfoStep       │ Project Information  
   ├── Project Name    │ • Python identifier validation
   ├── Author          │ • Required field
   ├── Version         │ • Semantic version format
   └── Description     │ • Optional field
                       │
3. LocationStep        │ Project Location
   ├── Directory Path  │ • File browser integration
   ├── Path Validation │ • Existence and permissions check
   └── Conflict Warn   │ • Existing directory warnings
                       │
4. OptionsStep         │ Configuration Options
   ├── License Select  │ • License dropdown with preview
   ├── Git Init        │ • Repository initialization toggle
   ├── VEnv Tool       │ • Virtual environment tool choice
   └── Template Vars   │ • Dynamic template-specific options
                       │
5. ReviewStep          │ Review & Create
   ├── Summary View    │ • Collapsible sections
   ├── Structure Tree  │ • Project structure preview
   └── Create Button   │ • Triggers project generation
```

### Navigation Rules

**Forward Navigation**:
- Each step must pass `validatePage()` before proceeding
- Validation errors prevent navigation and show error messages
- Wizard buttons (Next/Back) automatically manage enabled state

**Backward Navigation**:
- Always allowed (no validation required)
- Data persists when navigating backward
- `cleanupPage()` called when leaving step

**Completion Logic**:
- Step completion determined by `isComplete()` implementation
- `completeChanged` signal updates wizard button states
- Final step completion triggers project generation

## Data Flow Architecture

### Data Collection Pipeline

```
Step Input → Field Validation → Wizard Data → Options Processing → Generation Parameters
```

#### WizardData Dataclass
```python
@dataclass
class WizardData:
    template_id: str = ""
    template_name: str = ""
    template_path: str = ""
    project_name: str = ""
    author: str = ""
    version: str = "1.0.0"
    description: str = ""
    target_path: str = ""
    license: str = "MIT"
    init_git: bool = True
    create_venv: bool = True
    venv_tool: str = "uv"
    additional_options: Dict[str, Any] = field(default_factory=dict)
```

#### Data Persistence

**Cross-Step Persistence**:
- Wizard fields registered using `registerField()`
- Data automatically persists during navigation
- Field values accessible via `wizard.field("fieldName")`

**Settings Persistence**:
- ConfigManager handles settings file I/O
- Default values loaded during wizard initialization
- Changes saved immediately on settings dialog acceptance

### Validation Architecture

#### Multi-Level Validation

**Field-Level Validation**:
```python
# Real-time validation as user types
def _validate_project_name(self, text: str) -> bool:
    pattern = r"^[a-zA-Z][a-zA-Z0-9_]*$"
    return re.match(pattern, text) is not None
```

**Step-Level Validation**:
```python  
# Validation before navigation
def validatePage(self) -> bool:
    if not self.project_name:
        self.show_error("Project name is required")
        return False
    return True
```

**Cross-Step Validation**:
```python
# Final validation before generation
def validate_all_data(self) -> List[str]:
    errors = []
    for step in self.wizard_steps:
        step_errors = step.validate_data()
        errors.extend(step_errors)
    return errors
```

## Extension Points

### Adding New Wizard Steps

1. **Create Step Class**:
```python
class CustomStep(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Custom Step")
        self._setup_ui()
    
    def isComplete(self) -> bool:
        return self._validate_inputs()
        
    def validatePage(self) -> bool:
        return self._final_validation()
```

2. **Register with Wizard**:
```python
def _add_pages(self):
    # Existing steps...
    self.addPage(CustomStep())
```

3. **Update Data Collection**:
```python
def collect_data(self) -> Dict[str, Any]:
    data = super().collect_data()
    data["custom_field"] = self.field("customField")
    return data
```

### Adding New Dialogs

1. **Inherit from QDialog**:
```python
class CustomDialog(QDialog):
    # Custom signal definitions
    data_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
```

2. **Integrate with Main Application**:
```python
# Connect to wizard or main window
custom_dialog = CustomDialog(self)
custom_dialog.data_changed.connect(self.on_custom_data)
```

### Adding Custom Widgets

1. **Widget Implementation**:
```python
class CustomWidget(QWidget):
    value_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def value(self) -> Any:
        return self._current_value
        
    def setValue(self, value: Any):
        self._current_value = value
        self.value_changed.emit(value)
```

2. **Integration with Steps**:
```python
# Use in wizard steps
custom_widget = CustomWidget()
layout.addWidget(custom_widget)
custom_widget.value_changed.connect(self.on_value_changed)
```

## Testing Architecture

### Test Organization

```
tests/gui/
├── conftest.py                    # Test fixtures and mocks
├── test_wizard.py                 # Wizard framework tests
├── test_*_step.py                 # Individual step tests
├── test_*_dialog.py               # Dialog component tests
├── test_custom_widgets.py         # Custom widget tests
├── test_step_validation.py        # Validation logic tests
├── test_integration.py            # End-to-end workflow tests
└── test_wizard_generator_integration.py  # Backend integration tests
```

### Testing Patterns

#### Widget Testing with pytest-qt
```python
def test_widget_behavior(qtbot):
    widget = CustomWidget()
    qtbot.addWidget(widget)
    
    # Simulate user interaction
    qtbot.keyClicks(widget.input_field, "test input")
    
    # Verify behavior
    assert widget.value() == "test input"
```

#### Signal Testing
```python
def test_signal_emission(qtbot):
    widget = CustomWidget()
    
    with qtbot.waitSignal(widget.value_changed, timeout=1000):
        widget.setValue("new value")
```

#### Mock Integration
```python
@pytest.fixture
def mock_config_manager():
    mock = MagicMock()
    mock.get.side_effect = lambda key, default=None: {
        "defaults.author": "Test Author"
    }.get(key, default)
    return mock
```

## Performance Considerations

### UI Responsiveness

**Background Processing**:
- All long-running operations moved to QThread
- UI remains responsive during project generation
- Progress reporting provides user feedback

**Lazy Loading**:
- Templates loaded on-demand
- Icon loading with caching
- Stylesheet generation cached

**Memory Management**:
- Wizard step cleanup on navigation
- Resource cleanup on dialog close
- Cache size limits to prevent memory leaks

### Optimization Strategies

**Template Loading**:
```python
# Cache loaded templates to avoid repeated file I/O
@lru_cache(maxsize=32)
def load_template(template_path: str) -> Template:
    return self._load_template_from_file(template_path)
```

**Style Management**:
```python
# Cache generated stylesheets
def get_stylesheet(self, component: str = None) -> str:
    cache_key = f"{self._theme}/{component or 'global'}"
    if cache_key in self._cache:
        return self._cache[cache_key]
    # Generate and cache...
```

## Security Considerations

### Input Validation

**Path Traversal Prevention**:
```python
def validate_project_path(self, path: str) -> bool:
    # Resolve absolute path and check for traversal
    resolved = Path(path).resolve()
    return not any(part == ".." for part in resolved.parts)
```

**Template Variable Sanitization**:
```python
def sanitize_template_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
    # Remove potentially dangerous variables
    safe_vars = {k: v for k, v in variables.items() 
                if not k.startswith('__') and k in ALLOWED_VARIABLES}
    return safe_vars
```

### Error Handling

**Information Disclosure Prevention**:
- Error messages sanitized for user display
- Full stack traces only in debug logs
- AI error context strips sensitive information

**Graceful Degradation**:
- Application continues if AI service unavailable
- Template loading failures show user-friendly errors
- Missing resources fall back to defaults

## Deployment and Distribution

### Entry Points

The application provides multiple entry points for different use cases:

```toml
[project.scripts]
create-project = "create_project.main:main"        # CLI mode
create-project-gui = "create_project.gui.app:main" # GUI mode
```

### Launch Scripts

Cross-platform launch scripts in `scripts/`:
- `run-gui.sh` - macOS/Linux launcher
- `run-gui.ps1` - Windows PowerShell launcher  
- `run-gui.py` - Cross-platform Python launcher

### Packaging Considerations

**Dependencies**:
- PyQt6 requires platform-specific binaries
- All dependencies specified in pyproject.toml
- Development dependencies separate from runtime

**Resource Bundling**:
- Templates and resources included in package
- Icon assets embedded for offline use
- Stylesheets generated at runtime

## Future Extension Opportunities

### Plugin Architecture
- Step plugin system for custom workflow steps
- Template plugin system for external template sources
- Widget plugin system for custom input components

### Advanced Features
- Project templates with Git repository integration
- Real-time collaboration on project creation
- Integration with IDEs and development tools
- Cloud-based template sharing and discovery

### Accessibility Improvements
- High-contrast theme support
- Keyboard navigation enhancements
- Screen reader compatibility
- Font size scaling support

---

This architecture documentation provides a comprehensive overview of the GUI system's design, implementation patterns, and extension points. It serves as both a reference for current developers and a guide for future enhancements.