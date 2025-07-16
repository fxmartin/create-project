# Python Project Structure Creator - GUI Application Specification

## Overview
A PyQt-based GUI application that automates the creation of Python project folder structures based on best practices from the Real Python article on Python Application Layouts. The tool provides a wizard-style interface with AI-powered error assistance via Ollama integration.

## Core Requirements

### 1. User Interface Framework
- **Framework**: PyQt
- **Style**: Wizard-style interface with step-by-step screens
- **Platform**: macOS only
- **Visual Design**: Professional, modern appearance

### 2. Project Types Supported
Based on Real Python article patterns:
- One-off Script
- CLI Application (Installable Single Package)
- CLI Application with Internal Packages
- Django Web Application
- Flask Web Application
- Python Library/Package

### 3. Extensibility
- Support for custom project templates via external YAML files
- Template definition files stored in application directory
- Templates can include conditional logic

## Wizard Flow

### Step 1: Project Type Selection
- **Layout**: List with preview (list on left, detailed description/preview on right)
- **Display**: Project type name, description, and example structure
- **Navigation**: Next button enabled when selection made

### Step 2: Basic Information
- **Fields**:
  - Project name (validated for filesystem compatibility)
  - Author name (pre-filled from settings)
  - Project description (optional)
- **Validation**: Real-time validation with error indicators

### Step 3: Project Location
- **Features**:
  - Folder browser dialog
  - Path validation (write permissions, existing directories)
  - Default location from settings
- **Display**: Full path preview of where project will be created

### Step 4: Project Options
- **Universal Options**:
  - License type (MIT, Apache, GPL, etc.)
  - Initialize git repository
  - Create virtual environment
  - Install initial dependencies
  - Generate sample code
  - Set up testing framework
- **Dynamic Options**: Additional options based on selected project type

### Step 5: Review and Create
- **Display**:
  - Summary of selected project type and options
  - Preview of folder structure to be created
  - List of files to be generated
  - Estimated disk space usage
  - Dependencies to be installed
  - Commands to be executed (git init, pip install, etc.)
- **Features**:
  - Save configuration as preset
  - Export configuration for sharing
  - Preview generated file contents (README.md, etc.)
- **Actions**: Create Project, Back, Cancel

## Template System

### Template Definition (YAML)
```yaml
name: "Custom CLI App"
description: "A command-line application with custom structure"
author: "Template Author"
version: "1.0.0"
structure:
  - path: "src/{{project_name}}"
    type: "directory"
  - path: "src/{{project_name}}/__init__.py"
    type: "file"
    template: "init_template.py"
  - path: "tests/"
    type: "directory"
    condition: "include_tests"
files:
  - name: "init_template.py"
    content: |
      """{{project_description}}"""
      __version__ = "0.1.0"
      __author__ = "{{author}}"
options:
  - name: "include_tests"
    type: "boolean"
    default: true
    description: "Include test directory and files"
post_commands:
  - command: "git init"
    condition: "init_git"
  - command: "python -m venv venv"
    condition: "create_venv"
```

### Template Features
- Variable substitution with {{placeholder}} syntax
- Conditional file/folder creation
- Post-creation command execution
- Support for binary files (copy mode)

## Error Handling & AI Integration

### Error Handling Approach
- **Style**: Progressive disclosure
- **Levels**:
  1. Simple error message
  2. "Show Details" button reveals technical details
  3. "Get AI Help" button (if Ollama available)

### Ollama Integration
- **Model**: gemma3n:latest (configurable in settings)
- **Context Sent**: Error message + OS info + Python version + attempted action
- **Display**: AI suggestions in popup window
- **Fallback**: Feature disabled if Ollama not available
- **Caching**: Cache responses to avoid repeated API calls
- **Startup Check**: Validate Ollama availability at application launch

### Response Caching
- Cache key: Hash of error message + context
- Storage: JSON file in application directory
- Expiration: 24 hours
- Size limit: 100 cached responses (LRU eviction)

## Settings & Configuration

### User Settings (settings.json)
```json
{
  "author": {
    "name": "Default Author",
    "email": "author@example.com"
  },
  "defaults": {
    "project_location": "~/Development",
    "license": "MIT",
    "virtual_env_tool": "venv",
    "git_branch": "main"
  },
  "ui": {
    "theme": "default",
    "window_size": [800, 600]
  },
  "ollama": {
    "model": "gemma3n:latest",
    "endpoint": "http://localhost:11434"
  }
}
```

### Environment Configuration (.env)
```env
LOG_LEVEL=INFO
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_TIMEOUT=30
```

## Technical Architecture

### Data Persistence
- **Settings**: JSON files in application directory
- **Presets**: YAML files in application directory
- **Templates**: YAML files in templates/ subdirectory
- **Cache**: JSON file for Ollama responses
- **No Database**: Use filesystem-based storage only

### Threading Model
- **UI Thread**: Handle user interface and user interactions
- **Background Thread**: Template rendering, file generation, git operations
- **Progress Updates**: Thread-safe progress reporting to UI
- **Cancellation**: Support for canceling long-running operations

### File Structure
```
app/
├── main.py                    # Application entry point
├── gui/
│   ├── __init__.py
│   ├── wizard.py              # Main wizard window
│   ├── steps/                 # Individual wizard steps
│   │   ├── __init__.py
│   │   ├── project_type.py
│   │   ├── basic_info.py
│   │   ├── location.py
│   │   ├── options.py
│   │   └── review.py
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── error.py
│   │   └── ai_help.py
│   └── widgets/
│       ├── __init__.py
│       └── custom_widgets.py
├── core/
│   ├── __init__.py
│   ├── template_engine.py     # Template processing
│   ├── project_generator.py   # Project creation logic
│   ├── git_manager.py         # Git operations
│   └── ollama_client.py       # AI integration
├── utils/
│   ├── __init__.py
│   ├── config_manager.py      # Settings management
│   └── validators.py          # Input validation
├── templates/                 # Built-in project templates
│   ├── one_off_script.yaml
│   ├── cli_app.yaml
│   ├── cli_app_internal.yaml
│   ├── django_app.yaml
│   ├── flask_app.yaml
│   └── python_library.yaml
├── resources/
│   ├── icons/                 # UI icons
│   └── styles/                # QSS stylesheets
├── logger.py                  # Enhanced logging utility (existing)
├── settings.json              # User settings
├── .env                       # Environment configuration
├── logs/                      # Application logs
└── cache/                     # Ollama response cache
```

## Logging & Debugging

### Logging Configuration
- **Implementation**: Use existing `logger.py` file in project root
- **Framework**: Enhanced logging utility with colored terminal output
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Features**:
  - Colored console output based on log levels
  - Performance optimizations through caching
  - Terminal detection for color support
  - Environment variable configuration via LOG_LEVEL
- **Format**: `%(levelname)s: %(message)s` (colored in terminals)
- **Output**: 
  - Console (during development) - colored output
  - File: `logs/app.log` (rotating, max 10MB, 5 backups)
- **Level Configuration**: Set via LOG_LEVEL in .env file

### Integration with Existing Logger
The application should import and use the existing `logger.py` module:
```python
from logger import Logger, log_info, log_error, log_debug, log_warn

# Create application-specific logger
app_logger = Logger("ProjectCreator")

# Or use convenience functions
log_info("Application started")
log_error("Failed to create project", exc_info=True)
log_warn("Template validation warning")
log_debug("Processing template variables")
```

### Comprehensive Logging Requirements
**CRITICAL**: The application must implement extensive logging throughout all components to provide detailed execution tracing. This includes:

#### Mandatory Logging Levels
- **INFO**: All significant application events and state changes
- **WARNING**: All non-critical issues, validation problems, and recoverable errors
- **ERROR**: All exceptions, failures, and critical issues
- **DEBUG**: Detailed execution flow for troubleshooting

#### Required Logging Coverage
Every major operation must be logged with appropriate level:

**Application Lifecycle:**
```python
log_info("Application starting up")
log_info("Loading configuration from settings.json")
log_info("Initializing UI components")
log_info("Checking Ollama availability")
log_info("Application ready for user interaction")
```

**User Interactions:**
```python
log_info(f"User selected project type: {project_type}")
log_info(f"User entered project name: {project_name}")
log_info(f"User chose location: {project_path}")
log_debug("Validating user input")
log_warn("Project name contains special characters")
```

**Template Processing:**
```python
log_info(f"Loading template: {template_name}")
log_debug(f"Template variables: {variables}")
log_info("Starting template rendering")
log_debug(f"Processing file: {file_path}")
log_warn("Template missing optional variable")
```

**File Operations:**
```python
log_info(f"Creating project directory: {project_path}")
log_debug(f"Creating subdirectory: {subdir}")
log_info(f"Generating file: {file_name}")
log_debug(f"Writing {len(content)} bytes to {file_path}")
log_warn(f"File already exists, skipping: {file_path}")
```

**Git Operations:**
```python
log_info("Initializing git repository")
log_debug("Setting up .gitignore")
log_info("Making initial commit")
log_warn("Git user not configured")
```

**Ollama Integration:**
```python
log_info("Connecting to Ollama API")
log_debug(f"Sending request to model: {model}")
log_info("Received AI response")
log_warn("Ollama response timeout, using cached result")
```

**Error Handling:**
```python
log_error("Failed to create directory", exc_info=True)
log_error(f"Template validation failed: {validation_error}")
log_warn("Permission denied, trying alternative location")
```

### Log Categories
All categories must include INFO, WARNING, and ERROR messages for complete traceability:

- **UI Events**: User interactions, wizard navigation, button clicks, form submissions
- **Template Processing**: Template loading, variable substitution, file generation, validation
- **File Operations**: Directory creation, file generation, permission checks, disk space
- **Git Operations**: Repository initialization, commits, configuration, status checks
- **Ollama Integration**: API calls, responses, errors, caching, availability checks
- **Settings**: Configuration loading, validation, updates, environment variables
- **Performance**: Execution times, resource usage, cache hit/miss ratios
- **Security**: Input validation, path sanitization, permission checks
- **Errors**: All exceptions and error conditions with full context

### Logging Performance Requirements
- **Startup**: Log application initialization within first 5 seconds
- **Operation Tracing**: Every user action must generate at least one log entry
- **Progress Tracking**: Long operations must log progress updates every 2-3 seconds
- **Error Context**: All errors must include sufficient context for debugging
- **Debug Mode**: When LOG_LEVEL=DEBUG, provide step-by-step execution details

## Distribution & Installation

### Package Distribution
- **PyPI Package**: `pip install python-project-creator`
- **Dependencies**: Listed in pyproject.toml
- **Entry Point**: Command-line script that launches GUI

### Standalone Executable
- **Tool**: PyInstaller
- **Bundle**: One-file executable for macOS
- **Size Optimization**: Exclude unnecessary modules
- **Resources**: Embed templates, icons, and stylesheets

### Requirements
- **Python**: 3.8+
- **PyQt**: 5.15+ or 6.0+
- **Additional**: requests, pyyaml, jinja2
- **Logging**: Use existing `logger.py` module (no additional dependencies)

## Development Considerations

### Testing Strategy
- **Unit Tests**: Core functionality, template engine, validators
- **Integration Tests**: File generation, git operations
- **GUI Tests**: Widget behavior, wizard flow
- **Manual Testing**: User experience, edge cases

### Performance Considerations
- **Lazy Loading**: Load templates only when needed
- **Background Processing**: Keep UI responsive during project creation
- **Memory Management**: Clean up resources after project creation
- **Caching**: Cache template parsing results

### Security Considerations
- **Input Validation**: Sanitize all user inputs (with INFO/WARN logging)
- **File Permissions**: Validate write permissions before creation (with DEBUG logging)
- **Command Injection**: Sanitize commands passed to subprocess (with WARN logging)
- **Path Traversal**: Validate all file paths (with DEBUG logging)
- **Logging Security**: Ensure no sensitive data (passwords, tokens) appears in logs

## Success Metrics
- **User Experience**: Complete wizard flow in under 2 minutes
- **Reliability**: 99%+ success rate for project creation
- **Performance**: Project creation completes in under 30 seconds
- **Extensibility**: Easy addition of new project templates
- **Error Recovery**: Clear error messages with actionable solutions

## Future Enhancements
- **Template Marketplace**: Share and download community templates
- **Project Updates**: Update existing projects with new structure
- **IDE Integration**: Plugins for popular IDEs
- **Team Templates**: Shared templates for development teams
- **Version Control**: Template versioning and updates