# Python Project Structure Creator

A PyQt-based GUI application that automates the creation of Python project directory structures with templates, configuration, and best practices.

## Features

- **Project Templates**: Built-in templates for common Python project types
- **GUI Interface**: Easy-to-use PyQt wizard interface
- **Custom Templates**: Support for user-defined project templates
- **Configuration Management**: Persistent settings and preferences
- **Structure Validation**: Ensures project structure integrity
- **Cross-Platform**: Designed to work on macOS, Windows, and Linux

## Installation

### From Source

1. Clone the repository:
```bash
git clone <repository-url>
cd create-project
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Run the application:
```bash
uv run python -m create_project
```

### Requirements

- Python 3.9.6 or higher
- PyQt6 (for GUI)
- Additional dependencies listed in `pyproject.toml`

## Usage

### Command Line

Run the application as a module:
```bash
python -m create_project
```

Or with uv:
```bash
uv run python -m create_project
```

### GUI Application

The application provides a step-by-step wizard interface for:
1. Selecting project type
2. Configuring basic project information
3. Choosing project location
4. Setting project-specific options
5. Reviewing and creating the project

### Development

To run tests:
```bash
uv run pytest
```

To run specific test files:
```bash
uv run pytest tests/unit/test_structure.py
```

## Project Structure

```
create-project/
├── create_project/          # Main package
│   ├── core/               # Core business logic
│   ├── gui/                # PyQt GUI components
│   ├── utils/              # Utility functions
│   ├── templates/          # Project templates
│   │   ├── builtin/        # Built-in templates
│   │   └── user/           # User-defined templates
│   ├── resources/          # Application resources
│   │   ├── styles/         # QSS stylesheets
│   │   ├── icons/          # GUI icons
│   │   └── licenses/       # License templates
│   └── config/             # Configuration files
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── gui/               # GUI tests
├── docs/                   # Documentation
│   ├── user/              # User documentation
│   ├── developer/         # Developer documentation
│   └── templates/         # Template documentation
├── build/                  # Build artifacts
├── dist/                   # Distribution packages
└── scripts/               # Build scripts
```

## Development Setup

1. Ensure you have Python 3.9.6+ installed
2. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Clone the repository
4. Run `uv sync` to install dependencies
5. Run `uv run python -m create_project` to test the application

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests for new functionality
5. Ensure all tests pass: `uv run pytest`
6. Submit a pull request

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

## Status

This project is in active development. The basic project structure has been implemented and tested. See the TODO.md file for current development tasks and progress.