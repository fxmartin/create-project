# Create Project - User Guide

## Overview

Create Project is a PyQt6-based GUI application that automates the creation of Python project structures. It provides a user-friendly wizard interface to generate well-structured Python projects with templates, dependency management, Git integration, and AI assistance.

## Table of Contents

1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Wizard Walkthrough](#wizard-walkthrough)
4. [Template System](#template-system)
5. [Configuration](#configuration)
6. [AI Assistance](#ai-assistance)
7. [Command Line Interface](#command-line-interface)
8. [Troubleshooting](#troubleshooting)
9. [Keyboard Shortcuts](#keyboard-shortcuts)
10. [Advanced Features](#advanced-features)

## Installation

### Requirements

- Python 3.9.6 or higher
- PyQt6 (automatically installed)
- Internet connection (for AI features)

### From PyPI (Recommended)

```bash
pip install create-project
```

### From Source

```bash
git clone https://github.com/fxmartin/create-project.git
cd create-project
uv install
```

### Verify Installation

```bash
create-project --version
create-project-gui --help
```

## Getting Started

### Launch the GUI Application

**Option 1: Using the GUI entry point**
```bash
create-project-gui
```

**Option 2: Using the main CLI with GUI flag**
```bash
create-project --gui
```

**Option 3: Using launch scripts**
```bash
# macOS/Linux
./scripts/run-gui.sh

# Windows
./scripts/run-gui.ps1

# Cross-platform Python script
python scripts/run-gui.py
```

### First Run Setup

On first launch, the application will:
1. Create default configuration files
2. Set up logging directories
3. Initialize template system
4. Check for AI service availability (Ollama)

## Wizard Walkthrough

The Create Project wizard guides you through 5 steps to create your project:

### Step 1: Project Type Selection

**Purpose**: Choose your project template

**Interface Elements**:
- **Template List** (left panel): Shows available project templates
- **Preview Pane** (right panel): Displays template details, description, and structure

**Available Templates**:
1. **Python Library** - Distributable Python package with setup.py
2. **Python Package** - Importable Python package with __init__.py  
3. **CLI Application** - Command-line tool with argument parsing
4. **Django Web App** - Django web application with basic structure
5. **Flask Web App** - Flask web application with templates
6. **One-off Script** - Simple standalone Python script

**Actions**:
- Click on a template to see its preview
- Template preview shows:
  - Description and use cases
  - Dependencies and requirements
  - Project structure overview
  - Template-specific variables

**Navigation**:
- **Next**: Proceed to basic information (requires template selection)
- **Cancel**: Exit the wizard

---

### Step 2: Basic Information

**Purpose**: Enter core project details

**Required Fields**:
- **Project Name**: Python identifier format (letters, numbers, underscores)
  - ✅ Valid: `my_project`, `data_analyzer`, `web_scraper_v2`
  - ❌ Invalid: `my-project`, `2nd_project`, `my project`
- **Author**: Your name or organization
- **Version**: Semantic version format (e.g., 1.0.0, 0.1.0, 2.1.3)

**Optional Fields**:
- **Description**: Brief project description

**Real-time Validation**:
- Project name validated as you type
- Version format checked against semantic versioning
- Error messages appear below invalid fields
- Next button disabled until all required fields are valid

**Auto-fill Features**:
- Author field pre-filled from configuration
- Version defaults to 1.0.0
- Project name used for directory creation

**Navigation**:
- **Next**: Proceed to location selection (requires valid data)
- **Back**: Return to project type selection
- **Cancel**: Exit with confirmation dialog

---

### Step 3: Location Selection

**Purpose**: Choose where to create your project

**Interface Elements**:
- **Location Field**: Text input showing selected directory path
- **Browse Button**: Opens file dialog for directory selection
- **Path Preview**: Shows full project path (Location + Project Name)

**Path Validation**:
- **Existence Check**: Verifies parent directory exists
- **Permission Check**: Ensures write access to selected location
- **Path Preview**: Shows full project path as `{location}/{project_name}`

**Warnings and Notifications**:
- **Existing Directory Warning**: Shown if target directory already exists
  - Project will be created inside existing directory
  - Files may be overwritten (with confirmation)
- **Permission Issues**: Clear error messages for access problems

**Default Behavior**:
- Default location from configuration (typically ~/projects)
- Remembers last used location
- Cross-platform path handling

**Navigation**:
- **Next**: Proceed to options configuration (requires valid path)
- **Back**: Return to basic information
- **Cancel**: Exit with confirmation dialog

---

### Step 4: Options Configuration

**Purpose**: Configure project-specific options

**Universal Options** (all projects):

**License Selection**:
- **Dropdown Menu**: Choose from 5 available licenses
  - MIT License (default)
  - Apache License 2.0
  - GNU General Public License v3.0
  - BSD 3-Clause License
  - Unlicense
- **Preview Button**: Shows full license text in modal dialog
- **Copy to Clipboard**: Copy license text from preview dialog

**Development Tools**:
- **Git Initialization**: 
  - ☑️ Initialize Git repository (default: enabled)
  - Creates .gitignore file appropriate for Python projects
  - Makes initial commit with project structure
- **Virtual Environment Tool**:
  - **uv** (default) - Fast Python package manager
  - **virtualenv** - Traditional virtual environment tool
  - **venv** - Built-in Python virtual environment
  - **none** - Skip virtual environment creation

**Template-Specific Options**:
Dynamic options based on selected template:

- **Web Applications** (Django/Flask):
  - Database backend selection
  - Template engine preferences
  - Static file handling options

- **CLI Applications**:
  - Argument parser library (argparse, click, typer)
  - Configuration file format
  - Logging preferences

- **Libraries/Packages**:
  - Documentation tool (Sphinx, MkDocs)
  - Testing framework (pytest, unittest)
  - CI/CD integration options

**Dynamic UI Generation**:
Options are generated based on template variables:
- **String inputs**: Text fields with validation
- **Boolean options**: Checkboxes
- **Choice options**: Dropdown menus or radio buttons
- **Email fields**: Email format validation
- **URL fields**: URL format validation
- **Path fields**: File/directory selection

**Navigation**:
- **Next**: Proceed to review (all options have defaults)
- **Back**: Return to location selection
- **Cancel**: Exit with confirmation dialog

---

### Step 5: Review and Create

**Purpose**: Review all settings and create the project

**Summary Sections** (Collapsible):

**Basic Information**:
- Project name, author, version, description
- Template type and selected options
- License selection

**Location & Paths**:
- Target directory
- Full project path
- Existing directory warnings (if applicable)

**Configuration Options**:
- Git repository settings
- Virtual environment configuration
- Template-specific variables
- License and development tool selections

**Project Structure Preview**:
- **Tree View**: Hierarchical display of files and directories to be created
- **Template Files**: Shows which files will be generated
- **Directory Structure**: Preview of complete project layout
- **Expandable Nodes**: Click to expand/collapse directory contents

**Create Button**:
- **Validation**: Final validation of all collected data
- **Progress Dialog**: Opens modal progress dialog during creation
- **Error Handling**: Shows detailed error information if creation fails
- **AI Assistance**: Offers AI help if errors occur and AI service is available

**Navigation**:
- **Create**: Start project generation
- **Back**: Return to options configuration  
- **Cancel**: Exit with confirmation dialog

---

## Project Generation Process

### Progress Dialog

When you click "Create", a modal progress dialog appears showing:

**Progress Information**:
- **Progress Bar**: Visual indicator of generation progress (0-100%)
- **Status Messages**: Real-time updates of current operation
- **Detailed Log**: Scrollable log of all generation steps
- **Time Estimates**: Expected completion time

**Generation Steps**:
1. **Template Loading** (0-10%): Load and validate selected template
2. **Variable Processing** (10-30%): Process template variables and options
3. **Directory Creation** (30-40%): Create project directory structure
4. **File Generation** (40-70%): Generate files from templates
5. **Git Initialization** (70-80%): Initialize repository and make initial commit
6. **Virtual Environment** (80-90%): Create and configure virtual environment
7. **Post-processing** (90-100%): Run post-creation commands and finalization

**User Controls**:
- **Cancel Button**: Stop generation with confirmation dialog
  - Shows warning about partial project creation
  - Option to clean up incomplete project
- **Close Button**: Available after completion or cancellation
- **Auto-close**: Success dialog auto-closes after 2 seconds (optional)

**Status Indicators**:
- **Success**: Green progress bar, success icon
- **Error**: Red progress bar, error icon, detailed error message
- **Cancelled**: Orange progress bar, cancellation confirmation

### Error Handling

**Error Dialog Features**:
- **Error Summary**: Clear, user-friendly error description
- **Technical Details**: Expandable section with full error information
- **Error Context**: Relevant information about the failed operation
- **Timestamp**: When the error occurred

**Action Buttons**:
- **Get AI Help**: Launch AI assistance dialog (if AI service available)
- **Copy Details**: Copy error information to clipboard
- **Report Issue**: Pre-fill GitHub issue with error details
- **Retry**: Retry the failed operation (if applicable)
- **Close**: Close error dialog

**AI Help Integration**:
- Automatically triggered for project generation errors
- Provides context-aware suggestions
- Offers solutions based on error type and user environment

## Template System

### Built-in Templates

The application includes 6 professionally designed templates:

#### 1. Python Library
**Use Case**: Distributable Python packages for PyPI

**Generated Structure**:
```
my_library/
├── README.md
├── pyproject.toml
├── setup.py
├── src/
│   └── my_library/
│       ├── __init__.py
│       └── core.py
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── docs/
│   └── README.md
└── .gitignore
```

**Features**:
- PyPI-ready configuration
- Setuptools integration
- Pytest testing structure
- Documentation framework
- Version management

#### 2. Python Package
**Use Case**: Importable Python packages for applications

**Generated Structure**:
```
my_package/
├── __init__.py
├── main.py
├── utils/
│   ├── __init__.py
│   ├── helpers.py
│   └── constants.py
├── tests/
│   └── test_main.py
├── requirements.txt
└── README.md
```

**Features**:
- Simple package structure
- Utility modules
- Requirements management
- Testing setup

#### 3. CLI Application
**Use Case**: Command-line tools and utilities

**Generated Structure**:
```
my_cli/
├── main.py
├── cli/
│   ├── __init__.py
│   ├── commands.py
│   └── parser.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── tests/
│   └── test_cli.py
├── requirements.txt
└── README.md
```

**Features**:
- Argument parsing setup
- Configuration management
- Command structure
- Help system integration

#### 4. Django Web App
**Use Case**: Django web applications

**Generated Structure**:
```
my_django_app/
├── manage.py
├── my_django_app/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   └── __init__.py
├── templates/
├── static/
├── requirements.txt
└── README.md
```

**Features**:
- Django project structure
- Settings configuration
- URL routing setup
- Static file handling
- Template organization

#### 5. Flask Web App
**Use Case**: Flask web applications

**Generated Structure**:
```
my_flask_app/
├── app.py
├── config.py
├── templates/
│   ├── base.html
│   └── index.html
├── static/
│   ├── css/
│   └── js/
├── tests/
│   └── test_app.py
├── requirements.txt
└── README.md
```

**Features**:
- Flask application factory
- Template inheritance
- Static asset organization
- Configuration management
- Testing structure

#### 6. One-off Script
**Use Case**: Standalone Python scripts

**Generated Structure**:
```
my_script/
├── script.py
├── config.py
├── requirements.txt
└── README.md
```

**Features**:
- Simple script structure
- Configuration support
- Dependency management
- Documentation template

### Template Variables

Templates support dynamic variable substitution:

**Standard Variables** (available in all templates):
- `{{project_name}}` - Project name
- `{{author}}` - Author name
- `{{version}}` - Project version
- `{{description}}` - Project description
- `{{license}}` - Selected license
- `{{year}}` - Current year

**Template-Specific Variables**:
Each template can define custom variables with validation:
- String variables with regex validation
- Boolean variables for feature toggles
- Choice variables with predefined options
- Email variables with email format validation
- URL variables with URL format validation
- Path variables with file/directory selection

### Custom Templates

**Adding Custom Templates**:
1. Create template YAML file following the schema
2. Add to custom template directory (configured in settings)
3. Templates automatically discovered on restart

**Template Directory Locations**:
- **Built-in**: `create_project/templates/builtin/`
- **User**: `~/.create-project/templates/` (configurable)
- **Additional**: Configured in Settings → Template Paths

## Configuration

### Settings Dialog

Access via wizard menu or keyboard shortcut (Ctrl+, / Cmd+,)

#### General Tab

**Default Values**:
- **Default Author**: Pre-fills author field in wizard
- **Default Location**: Default project creation directory
- **Remember Last Location**: Use last selected location as default

**Application Preferences**:
- **Theme**: Light or Dark mode
- **Auto-close Progress**: Auto-close progress dialog on success
- **Confirmation Dialogs**: Show confirmation for destructive actions

#### AI Settings Tab

**Ollama Configuration**:
- **Enable AI Assistance**: Toggle AI features on/off
- **Ollama URL**: Ollama service URL (default: http://localhost:11434)
- **Model Selection**: Choose from available Ollama models
- **Connection Test**: Verify Ollama service connectivity

**AI Behavior**:
- **Auto-suggest on Errors**: Automatically show AI help for errors
- **Context Collection**: Include system info in AI requests
- **Response Caching**: Cache AI responses for faster access

#### Template Paths Tab

**Template Directories**:
- **Built-in Templates**: System template location (read-only)
- **User Template Directory**: Personal template storage
- **Additional Directories**: Custom template locations

**Management Actions**:
- **Add Directory**: Browse and add custom template directory
- **Remove Directory**: Remove custom template directory
- **Refresh Templates**: Rescan all directories for templates

### Configuration Files

**Location**: `~/.create-project/` or system config directory

**Files**:
- `settings.json` - Main configuration file
- `logs/` - Application log files
- `cache/` - AI response cache and temporary files
- `templates/` - User custom templates

**settings.json Structure**:
```json
{
  "defaults": {
    "author": "Your Name",
    "location": "/Users/yourname/projects"
  },
  "ai": {
    "enabled": true,
    "ollama_url": "http://localhost:11434",
    "model": "llama2"
  },
  "templates": {
    "directories": ["/custom/templates/path"],
    "user_path": "/Users/yourname/.create-project/templates"
  }
}
```

### Environment Variables

Override configuration with environment variables:

```bash
# AI Configuration
export CREATE_PROJECT_AI_ENABLED=true
export CREATE_PROJECT_OLLAMA_URL=http://localhost:11434
export CREATE_PROJECT_AI_MODEL=codellama

# Template Configuration  
export CREATE_PROJECT_TEMPLATE_DIR=/custom/templates

# Application Settings
export CREATE_PROJECT_DEBUG=true
export CREATE_PROJECT_LOG_LEVEL=DEBUG
```

## AI Assistance

### Ollama Integration

**Setup**:
1. Install Ollama: https://ollama.ai/
2. Install a code model: `ollama pull codellama`
3. Start Ollama service: `ollama serve`
4. Configure in Settings → AI Settings

**Supported Models**:
- **codellama** - Code generation and analysis
- **llama2** - General assistance and explanations
- **mistral** - Fast responses for simple queries
- **deepseek-coder** - Advanced code understanding

### AI Help Features

**Error Assistance**:
- Automatically triggered when project generation fails
- Analyzes error context and system information
- Provides specific solutions and suggestions
- Offers step-by-step troubleshooting guides

**Context Collection**:
- Operating system and Python version
- Selected template and project configuration
- Error stack traces and system logs
- Project generation parameters

**Privacy Protection**:
- Personal information automatically sanitized
- No sensitive data sent to AI service
- Local processing with Ollama (no cloud services)

### AI Help Dialog

**Features**:
- **Streaming Responses**: Real-time AI response display
- **Markdown Rendering**: Formatted responses with code highlighting
- **Copy to Clipboard**: Copy AI suggestions for reference
- **Retry Functionality**: Request alternative solutions
- **Context Aware**: Responses tailored to specific error context

**Response Types**:
- **Error Explanations**: What went wrong and why
- **Solution Steps**: Specific actions to resolve issues
- **Alternative Approaches**: Different ways to achieve the goal
- **Preventive Measures**: How to avoid similar issues

## Command Line Interface

### Basic Usage

**CLI Mode** (without GUI):
```bash
create-project my_project --template python_library --author "Your Name"
```

**GUI Mode**:
```bash
create-project --gui
create-project-gui
```

### CLI Options

**Required Arguments**:
```bash
create-project PROJECT_NAME
```

**Template Selection**:
```bash
--template TEMPLATE_ID     # Specify template to use
--list-templates          # Show available templates
```

**Project Information**:
```bash
--author "Author Name"    # Project author
--version "1.0.0"        # Project version  
--description "Desc"     # Project description
--location /path/to/dir  # Target directory
```

**Options**:
```bash
--license LICENSE        # License type (MIT, Apache, etc.)
--git / --no-git        # Git repository initialization
--venv TOOL             # Virtual environment tool (uv, venv, none)
--config CONFIG_FILE    # Custom configuration file
```

**AI and Debugging**:
```bash
--no-ai                 # Disable AI assistance
--debug                 # Enable debug logging
--verbose               # Verbose output
```

### Examples

**Create Python Library**:
```bash
create-project my_lib \
  --template python_library \
  --author "John Doe" \
  --description "My Python library" \
  --license MIT \
  --git
```

**Create CLI Application**:
```bash
create-project my_cli \
  --template cli_application \
  --location ~/projects \
  --venv uv \
  --debug
```

**List Available Templates**:
```bash
create-project --list-templates
```

**GUI Mode with Debug**:
```bash
create-project --gui --debug
```

## Troubleshooting

### Common Issues

#### "Template not found" Error
**Problem**: Selected template cannot be loaded
**Solutions**:
1. Check template file exists in template directory
2. Verify template YAML syntax is valid
3. Refresh template cache in Settings
4. Check file permissions on template directory

#### "Permission denied" Error
**Problem**: Cannot create files in target directory
**Solutions**:
1. Check write permissions on parent directory
2. Ensure target directory exists
3. Try different location (e.g., ~/projects)
4. Run with appropriate user permissions

#### "Git not found" Error
**Problem**: Git initialization fails
**Solutions**:
1. Install Git: https://git-scm.com/
2. Verify Git is in system PATH
3. Disable Git initialization if not needed
4. Check Git configuration (user.name, user.email)

#### "Virtual environment creation failed" Error
**Problem**: Cannot create virtual environment
**Solutions**:
1. Try different venv tool (uv → venv → virtualenv)
2. Check Python installation and version
3. Verify selected tool is installed
4. Disable virtual environment creation if not needed

#### "AI service unavailable" Error
**Problem**: Cannot connect to Ollama AI service
**Solutions**:
1. Install Ollama: https://ollama.ai/
2. Start Ollama service: `ollama serve`
3. Check Ollama URL in Settings
4. Verify firewall settings
5. Disable AI assistance if not needed

### Debug Mode

**Enable Debug Logging**:
```bash
create-project-gui --debug
```

**Debug Features**:
- Detailed logging to console and file
- Full stack traces for errors
- Template processing information
- Configuration loading details
- AI service communication logs

**Log Locations**:
- **Console**: Real-time debug output
- **File**: `~/.create-project/logs/create_project.log`
- **Error File**: `~/.create-project/logs/errors.log`

### Getting Help

**Application Help**:
- Help menu in GUI application
- Tooltips on form fields and buttons
- Status bar information

**Error Reporting**:
- Use "Report Issue" button in error dialogs
- Include log files and system information
- Describe steps to reproduce the problem

**Community Support**:
- GitHub Issues: https://github.com/fxmartin/create-project/issues
- Documentation: Project README and wiki
- Example templates and configurations

### Diagnostic Information

**System Information**:
- Python version and installation path
- PyQt6 version and Qt runtime
- Operating system and version
- Available disk space and permissions

**Configuration Status**:
- Configuration file locations and content
- Template directories and loaded templates
- AI service connectivity and available models
- Environment variables and overrides

**Health Check Command**:
```bash
create-project --check-health
```

## Keyboard Shortcuts

### Global Shortcuts

**Application**:
- `Ctrl+Q` / `Cmd+Q` - Quit application
- `Ctrl+,` / `Cmd+,` - Open Settings dialog
- `F1` - Show help information
- `Ctrl+Shift+D` - Toggle debug mode

### Wizard Navigation

**Step Navigation**:
- `Tab` - Next field
- `Shift+Tab` - Previous field
- `Enter` - Next step (if current step is complete)
- `Alt+Left` / `Cmd+Left` - Previous step
- `Alt+Right` / `Cmd+Right` - Next step
- `Escape` - Cancel wizard (with confirmation)

### Dialog Shortcuts

**Common Dialogs**:
- `Enter` - Accept dialog (OK button)
- `Escape` - Cancel dialog
- `Ctrl+C` / `Cmd+C` - Copy (in error dialogs, AI help)
- `Ctrl+A` / `Cmd+A` - Select all (in text fields)

**File Dialogs**:
- `Ctrl+H` / `Cmd+H` - Show hidden files
- `Ctrl+L` / `Cmd+L` - Location bar
- `Enter` - Select file/directory
- `Escape` - Cancel selection

### Text Field Shortcuts

**Editing**:
- `Ctrl+Z` / `Cmd+Z` - Undo
- `Ctrl+Y` / `Cmd+Y` - Redo
- `Ctrl+X` / `Cmd+X` - Cut
- `Ctrl+C` / `Cmd+C` - Copy
- `Ctrl+V` / `Cmd+V` - Paste
- `Ctrl+A` / `Cmd+A` - Select all

**Navigation**:
- `Home` / `Cmd+Left` - Beginning of line
- `End` / `Cmd+Right` - End of line
- `Ctrl+Home` / `Cmd+Up` - Beginning of field
- `Ctrl+End` / `Cmd+Down` - End of field

## Advanced Features

### Batch Project Creation

**CLI Batch Mode**:
Create multiple projects with configuration file:

```bash
create-project --batch projects.json
```

**projects.json Format**:
```json
{
  "projects": [
    {
      "name": "project1",
      "template": "python_library",
      "author": "John Doe",
      "location": "/path/to/projects"
    },
    {
      "name": "project2", 
      "template": "flask_app",
      "author": "John Doe",
      "location": "/path/to/projects"
    }
  ]
}
```

### Template Development

**Creating Custom Templates**:

1. **Template Structure**:
```yaml
# my_template.yaml
name: "My Custom Template"
description: "Custom project template"
version: "1.0.0"
author: "Your Name"

variables:
  - name: "custom_option"
    description: "Custom template option"
    type: "string"
    default: "default_value"
    validation: "^[a-zA-Z]+$"

structure:
  files:
    - source: "main.py.j2"
      destination: "{{project_name}}/main.py"
    - source: "README.md.j2"
      destination: "README.md"
  
  directories:
    - "{{project_name}}/utils"
    - "tests"

post_commands:
  - command: "pip install -e ."
    description: "Install package in development mode"
```

2. **Template Files**:
Create Jinja2 template files with variable substitution:

```python
# main.py.j2
"""
{{description}}

Author: {{author}}
Version: {{version}}
"""

def main():
    print("Hello from {{project_name}}!")
    print("Custom option: {{custom_option}}")

if __name__ == "__main__":
    main()
```

3. **Installation**:
- Place template files in custom template directory
- Add directory to Settings → Template Paths
- Restart application to refresh template list

### Integration with IDEs

**VS Code Integration**:
```bash
# Create project and open in VS Code
create-project my_project --template python_library && code my_project
```

**PyCharm Integration**:
```bash
# Create project and open in PyCharm
create-project my_project --template python_library && pycharm my_project
```

**Automated IDE Setup**:
Add post-commands to templates for IDE configuration:
```yaml
post_commands:
  - command: "code ."
    description: "Open in VS Code"
    condition: "{{ide_integration}}"
```

### CI/CD Integration

**GitHub Actions**:
Templates can include GitHub Actions workflows:

```yaml
# In template structure
files:
  - source: ".github/workflows/ci.yml.j2"
    destination: ".github/workflows/ci.yml"
```

**Jenkins Integration**:
```yaml
files:
  - source: "Jenkinsfile.j2"
    destination: "Jenkinsfile"
```

### Extension Development

**Plugin Architecture** (Future):
The application is designed to support plugins for:
- Custom wizard steps
- Additional template sources
- External service integrations
- Custom validation logic

**Hook Points**:
- Pre/post project generation
- Template loading and processing
- Wizard step validation
- Error handling and AI assistance

---

This user guide provides comprehensive documentation for using the Create Project application effectively. For additional help, consult the GitHub repository documentation or submit an issue for support.