# Developer Setup Guide

This guide helps developers set up their environment for contributing to the Python Project Structure Creator.

## Prerequisites

### Required Software

- **Python 3.9.6 or higher** - The minimum required Python version
- **uv** - Modern Python package manager and project manager
- **Git** - For version control

### Installing uv

If you don't have uv installed, install it using:

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify installation:
```bash
uv --version
```

### Installing Python

Use uv to install Python if needed:
```bash
uv python install 3.12  # or your preferred version >= 3.9.6
```

## Development Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd create-project
```

### 2. Set Up Virtual Environment

uv will automatically create and manage the virtual environment:

```bash
# Install dependencies
uv sync

# This creates .venv/ and installs all dependencies
```

### 3. Verify Installation

Test that everything is working:

```bash
# Run the application
uv run python -m create_project

# Run tests
uv run pytest

# Check specific tests
uv run pytest tests/unit/test_structure.py -v
```

## Development Dependencies

The project uses these key dependencies:

### Runtime Dependencies
- **PyQt6** - GUI framework (will be added in future milestones)
- **requests** - HTTP library (for future features)
- **pyyaml** - YAML parsing for templates
- **jinja2** - Template engine

### Development Dependencies
- **pytest** - Testing framework
- **black** - Code formatting (will be added)
- **ruff** - Linting and formatting (will be added)
- **mypy** - Type checking (will be added)

### Adding Dependencies

To add new dependencies:

```bash
# Runtime dependency
uv add package-name

# Development dependency
uv add --dev package-name

# Install specific version
uv add "package-name>=1.0.0"
```

## Project Structure

```
create-project/
├── create_project/          # Main package
│   ├── __init__.py         # Package initialization
│   ├── main.py             # Main entry point
│   ├── __main__.py         # Module execution entry
│   ├── core/               # Core business logic
│   ├── gui/                # PyQt GUI components
│   ├── utils/              # Utility functions
│   │   └── structure_validator.py  # Project structure validation
│   ├── templates/          # Project templates
│   ├── resources/          # Application resources
│   └── config/             # Configuration management
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── gui/               # GUI tests
├── docs/                   # Documentation
├── scripts/               # Build and utility scripts
└── pyproject.toml         # Project configuration
```

## Development Workflow

### 1. Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run tests to ensure nothing is broken:
   ```bash
   uv run pytest
   ```

4. Add tests for new functionality

### 2. Testing

Run the full test suite:
```bash
uv run pytest
```

Run specific test files:
```bash
uv run pytest tests/unit/test_structure.py
uv run pytest tests/unit/test_imports.py
```

Run tests with verbose output:
```bash
uv run pytest -v
```

Run tests with coverage (when coverage is added):
```bash
uv run pytest --cov=create_project
```

### 3. Code Quality

The project follows these standards:

- **Type Hints**: Use type hints for all functions and methods
- **Documentation**: Add docstrings to all public functions and classes
- **Comments**: Use the `ABOUTME:` comment format at the top of each file
- **Testing**: Maintain test coverage above 80%
- **Error Handling**: Handle errors gracefully with appropriate logging

### 4. File Conventions

All Python files should start with:
```python
# ABOUTME: Brief description of what this file does
# ABOUTME: Additional context or purpose
```

## Build Process

### Running the Application

```bash
# Run as module
uv run python -m create_project

# Run main directly
uv run python create_project/main.py
```

### Building Distribution

```bash
# Build package
./scripts/build.sh

# Create executable (when PyInstaller is added)
./scripts/package.sh
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running commands with `uv run` to use the project's virtual environment

2. **Python Version**: Ensure you're using Python 3.9.6 or higher:
   ```bash
   uv run python --version
   ```

3. **Missing Dependencies**: Reinstall dependencies:
   ```bash
   uv sync --all-extras
   ```

4. **Test Failures**: Run tests individually to isolate issues:
   ```bash
   uv run pytest tests/unit/test_structure.py::TestProjectStructure::test_all_directories_exist -v
   ```

### Getting Help

- Check the main README.md for general project information
- Review the TODO.md for current development tasks
- Check existing tests for usage examples
- Look at the BUILD-PLAN.md for the overall project roadmap

## IDE Setup

### VS Code
Recommended extensions:
- Python
- Pylance
- Python Test Explorer

### PyCharm
1. Open the project directory
2. Configure the Python interpreter to use `.venv/bin/python`
3. Enable pytest as the test runner

## Contributing Guidelines

1. Follow the existing code style and conventions
2. Write tests for all new functionality
3. Update documentation for user-facing changes
4. Use meaningful commit messages
5. Keep pull requests focused and small when possible

## Next Steps

After setting up your development environment:
1. Review the BUILD-PLAN.md to understand the project roadmap
2. Check the TODO.md for current tasks
3. Run the test suite to ensure everything is working
4. Choose a task to work on or create an issue for new features