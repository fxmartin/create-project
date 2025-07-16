# Current Project Structure Analysis

## Overview
This document analyzes the 6 project types supported by the Python Project Creator based on the Real Python article "Python Application Layouts: A Reference" and identifies common patterns for template design.

## Project Types Analysis

### 1. One-Off Script
**Description**: Simple Python script for personal use or basic distribution
**Use Cases**: Quick automation, data processing, simple utilities

**Structure**:
```
project_name/
├── .gitignore
├── project_name.py           # Main script
├── LICENSE
├── README.md
├── requirements.txt
└── tests.py
```

**Key Characteristics**:
- Single file execution
- Minimal dependencies
- Simple structure
- Basic testing

**Variables**:
- `project_name`: Name of the project and main script
- `author`: Script author
- `description`: Brief description
- `license`: License type
- `python_version`: Minimum Python version

### 2. CLI Application (Installable Single Package)
**Description**: Command-line application packaged as installable Python package
**Use Cases**: CLI tools, utilities, simple commands

**Structure**:
```
project_name/
├── project_name/
│   ├── __init__.py
│   ├── project_name.py       # Main module
│   └── helpers.py            # Helper functions
├── tests/
│   ├── project_name_tests.py
│   └── helpers_tests.py
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── setup.py
```

**Key Characteristics**:
- Proper Python package structure
- Separated concerns (main + helpers)
- Organized test structure
- Installable via pip

**Variables**:
- `project_name`: Package name
- `author`: Package author
- `description`: Package description
- `license`: License type
- `python_version`: Minimum Python version
- `entry_point`: CLI command name
- `include_tests`: Whether to include test files

### 3. CLI Application with Internal Packages
**Description**: Complex CLI application with multiple internal packages
**Use Cases**: Large CLI tools, multi-command applications, complex utilities

**Structure**:
```
project_name/
├── bin/                      # Executable files
├── docs/                     # Documentation
│   ├── module1.md
│   └── module2.md
├── project_name/
│   ├── __init__.py
│   ├── runner.py             # Main runner
│   ├── module1/
│   │   ├── __init__.py
│   │   ├── module1.py
│   │   └── helpers.py
│   └── module2/
│       ├── __init__.py
│       ├── helpers.py
│       └── module2.py
├── data/                     # Data files
│   ├── input.csv
│   └── output.xlsx
├── tests/
│   ├── module1/
│   │   ├── helpers_tests.py
│   │   └── module1_tests.py
│   └── module2/
│       ├── helpers_tests.py
│       └── module2_tests.py
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── setup.py
```

**Key Characteristics**:
- Modular architecture
- Separated executables
- Comprehensive documentation
- Data directory for testing
- Hierarchical test structure

**Variables**:
- `project_name`: Package name
- `author`: Package author
- `description`: Package description
- `license`: License type
- `python_version`: Minimum Python version
- `modules`: List of internal modules
- `include_data_dir`: Whether to include data directory
- `include_docs`: Whether to include documentation

### 4. Django Web Application
**Description**: Django-based web application with apps structure
**Use Cases**: Web applications, APIs, content management systems

**Structure**:
```
project_name/
├── app_name/                 # Django app
│   ├── migrations/
│   │   └── __init__.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── docs/                     # Documentation
├── project_name/             # Django project
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── static/                   # Static files
│   └── style.css
├── templates/                # HTML templates
│   └── base.html
├── .gitignore
├── manage.py
├── LICENSE
├── README.md
└── requirements.txt
```

**Key Characteristics**:
- Django project/app structure
- Separated static and template files
- Django-specific configuration
- Database migrations support

**Variables**:
- `project_name`: Django project name
- `app_name`: Initial Django app name
- `author`: Project author
- `description`: Project description
- `license`: License type
- `django_version`: Django version
- `database`: Database backend (sqlite, postgresql, mysql)
- `include_static`: Whether to include static files directory
- `include_templates`: Whether to include templates directory

### 5. Flask Web Application
**Description**: Flask-based web application with microframework structure
**Use Cases**: Web applications, APIs, microservices

**Structure**:
```
project_name/
├── project_name/
│   ├── __init__.py
│   ├── db.py                 # Database handling
│   ├── schema.sql            # Database schema
│   ├── auth.py               # Authentication
│   ├── blog.py               # Main logic
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   └── blog/
│   │       ├── create.html
│   │       ├── index.html
│   │       └── update.html
│   └── static/
│       └── style.css
├── tests/
│   ├── conftest.py
│   ├── data.sql
│   ├── test_factory.py
│   ├── test_db.py
│   ├── test_auth.py
│   └── test_blog.py
├── venv/                     # Virtual environment
├── .gitignore
├── setup.py
├── LICENSE
├── README.md
└── MANIFEST.in
```

**Key Characteristics**:
- Flask package structure
- Integrated templates and static files
- Comprehensive test suite
- Virtual environment included

**Variables**:
- `project_name`: Flask project name
- `author`: Project author
- `description`: Project description
- `license`: License type
- `flask_version`: Flask version
- `database`: Database type (sqlite, postgresql, mysql)
- `include_auth`: Whether to include authentication
- `include_blueprints`: Whether to use Flask blueprints
- `include_api`: Whether to include API endpoints

### 6. Python Library/Package
**Description**: Reusable Python library for distribution via PyPI
**Use Cases**: Utility libraries, frameworks, shared components

**Structure**:
```
project_name/
├── project_name/
│   ├── __init__.py
│   ├── core.py               # Core functionality
│   ├── utils.py              # Utility functions
│   ├── exceptions.py         # Custom exceptions
│   └── submodule/
│       ├── __init__.py
│       └── submodule.py
├── tests/
│   ├── __init__.py
│   ├── test_core.py
│   ├── test_utils.py
│   └── test_submodule.py
├── docs/
│   ├── source/
│   │   ├── conf.py
│   │   └── index.rst
│   └── Makefile
├── examples/
│   └── example_usage.py
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
├── setup.py
├── pyproject.toml
└── MANIFEST.in
```

**Key Characteristics**:
- Library-focused structure
- Comprehensive documentation
- Example usage
- PyPI distribution ready
- Sphinx documentation support

**Variables**:
- `project_name`: Library name
- `author`: Library author
- `description`: Library description
- `license`: License type
- `python_version`: Minimum Python version
- `include_docs`: Whether to include Sphinx documentation
- `include_examples`: Whether to include example usage
- `include_submodules`: Whether to include submodules
- `pypi_upload`: Whether to prepare for PyPI upload

## Common Patterns Identified

### 1. Universal Elements
Present in all project types:
- `.gitignore` - Git ignore file
- `LICENSE` - License file
- `README.md` - Project documentation
- `requirements.txt` - Dependencies (or pyproject.toml)

### 2. Python Package Structure
Common patterns:
- `__init__.py` files for package identification
- Main module named after project
- Helper/utility modules
- Proper import structure

### 3. Testing Structure
Common patterns:
- `tests/` directory
- Test files mirror source structure
- Test naming convention: `test_*.py`
- Test configuration files (conftest.py for pytest)

### 4. Configuration Files
Common patterns:
- `setup.py` for package installation
- `pyproject.toml` for modern Python packaging
- `MANIFEST.in` for package data
- Framework-specific config files

### 5. Documentation
Common patterns:
- `README.md` for basic documentation
- `docs/` directory for detailed documentation
- Inline documentation with docstrings
- Examples and usage guides

### 6. Directory Organization
Common patterns:
- Source code in named subdirectory
- Tests in separate directory
- Static assets in dedicated directories
- Configuration files at root level

## Template Variables Analysis

### Core Variables (All Projects)
- `project_name`: Project identifier
- `author`: Project author
- `email`: Author email
- `description`: Project description
- `license`: License type (MIT, Apache, GPL, etc.)
- `python_version`: Minimum Python version
- `create_venv`: Whether to create virtual environment
- `init_git`: Whether to initialize git repository

### Project-Specific Variables
- **Script**: `script_name`, `executable`
- **CLI**: `entry_point`, `command_name`, `include_helpers`
- **Complex CLI**: `modules`, `include_data_dir`, `include_docs`
- **Django**: `app_name`, `django_version`, `database`, `include_admin`
- **Flask**: `flask_version`, `database`, `include_auth`, `include_blueprints`
- **Library**: `include_docs`, `include_examples`, `pypi_upload`

### Optional Features (Conditional)
- `include_tests`: Whether to include test files
- `testing_framework`: pytest, unittest, etc.
- `include_ci`: Whether to include CI/CD configuration
- `include_docker`: Whether to include Docker configuration
- `include_pre_commit`: Whether to include pre-commit hooks

## Validation Rules

### Project Name
- Must be valid Python identifier
- Must be filesystem-safe
- Should follow Python naming conventions
- Cannot conflict with existing PyPI packages (for libraries)

### Author Information
- Valid email format
- Non-empty author name
- Optional GitHub username

### Dependencies
- Valid Python version specifiers
- Compatible dependency versions
- Framework-specific requirements

### File Paths
- Cross-platform compatibility
- No reserved names
- Proper file extensions
- Valid directory structure

## Template Design Implications

### 1. Hierarchical Structure
Templates should support nested directory structures with conditional generation based on project type and options.

### 2. Variable Substitution
All file names and content should support variable substitution using consistent syntax (Jinja2 recommended).

### 3. Conditional Logic
Templates should support conditional file/directory generation based on user choices and project type.

### 4. Template Inheritance
Common elements should be shared across project types to maintain consistency and reduce duplication.

### 5. Validation Integration
Templates should include validation rules for generated content to ensure project integrity.

## Conclusion

The analysis reveals clear patterns across all project types:
- Consistent directory organization principles
- Common file types and purposes
- Shared variable requirements
- Similar validation needs

This analysis provides the foundation for designing a flexible YAML-based template schema that can accommodate all project types while maintaining consistency and extensibility.