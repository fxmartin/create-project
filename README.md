# Python Project Structure Creator

A PyQt-based GUI application that automates the creation of Python project directory structures with templates, configuration, and best practices.

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd create-project

# Set up development environment (one command!)
./scripts/setup-dev.sh  # On macOS/Linux
# OR
./scripts/setup-dev.ps1  # On Windows

# Run the application
uv run python -m create_project
```

## ✨ Features

- **Project Templates**: Built-in templates for common Python project types
- **GUI Interface**: Easy-to-use PyQt wizard interface
- **Custom Templates**: Support for user-defined project templates
- **Configuration Management**: Persistent settings and preferences
- **Structure Validation**: Ensures project structure integrity
- **Cross-Platform**: Works on macOS, Windows, and Linux
- **AI Integration**: Optional Ollama integration for intelligent assistance

## 📋 Prerequisites

### System Requirements

- **Python**: 3.9.6 or higher
- **Operating System**: macOS 10.14+, Windows 10+, or Linux (Ubuntu 20.04+)
- **Memory**: 4GB RAM minimum (8GB recommended for development)
- **Storage**: 500MB free space

### Platform-Specific Requirements

#### macOS
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python via Homebrew
brew install python@3.11

# Install development tools
xcode-select --install
```

#### Windows
```powershell
# Install Python from python.org or via winget
winget install Python.Python.3.11

# Install Visual C++ Build Tools (for some dependencies)
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

#### Linux (Ubuntu/Debian)
```bash
# Update package list and install dependencies
sudo apt update
sudo apt install python3.11 python3.11-dev python3-pip
sudo apt install build-essential libpq-dev
```

## 🛠️ Development Setup

### Step 1: Install Python Version Manager (Recommended)

We recommend using `pyenv` for managing Python versions:

#### macOS/Linux
```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to shell configuration
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# Reload shell
source ~/.bashrc

# Install Python
pyenv install 3.11.8
pyenv local 3.11.8
```

#### Windows
Use `pyenv-win` or `conda` for Python version management.

### Step 2: Install uv (Fast Python Package Manager)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 3: Clone and Set Up Repository

```bash
# Clone the repository
git clone <repository-url>
cd create-project

# Create and configure environment
cp .env.example .env
# Edit .env with your preferred settings

# Install dependencies
uv sync

# Verify installation
uv run python -c "print('Setup complete!')"
```

### Step 4: Verify Development Environment

```bash
# Run environment validation script
uv run python scripts/validate-env.py

# Expected output:
# ✓ Python version: 3.11.8
# ✓ uv version: 0.1.0
# ✓ All dependencies installed
# ✓ Configuration valid
# ✓ Development environment ready!
```

## 📦 Dependencies

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | >=6.9.1 | GUI framework |
| requests | >=2.32.4 | HTTP client |
| PyYAML | >=6.0.2 | YAML parsing |
| Jinja2 | >=3.1.6 | Template engine |
| pydantic | >=2.11.7 | Data validation |
| python-dotenv | >=1.1.1 | Environment management |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.4.1 | Testing framework |
| pytest-qt | >=4.5.0 | PyQt testing |
| ruff | >=0.12.3 | Linting & formatting |
| mypy | >=1.17.0 | Type checking |
| pre-commit | >=3.5.0 | Git hooks |

All dependencies are managed through `pyproject.toml` and installed automatically with `uv sync`.

## 💻 IDE Setup

### VS Code (Recommended)

1. Install recommended extensions:
   ```bash
   code --install-extension ms-python.python
   code --install-extension ms-python.vscode-pylance
   code --install-extension charliermarsh.ruff
   ```

2. The project includes VS Code configuration in `.vscode/`

### PyCharm

1. Open the project in PyCharm
2. Configure interpreter: `File > Settings > Project > Python Interpreter`
3. Select the virtual environment created by uv

## 🧪 Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=create_project --cov-report=html

# Run specific test categories
uv run pytest tests/unit/          # Unit tests only
uv run pytest tests/integration/   # Integration tests only
uv run pytest tests/gui/           # GUI tests only

# Run tests in parallel
uv run pytest -n auto

# Run with verbose output
uv run pytest -v
```

### Writing Tests

See `docs/developer/testing.md` for comprehensive testing guidelines.

## 🔧 Development Workflow

### 1. Pre-commit Hooks

Set up pre-commit hooks to ensure code quality:

```bash
uv run pre-commit install
```

This will run:
- Code formatting with `ruff format`
- Linting with `ruff check`
- Type checking with `mypy`
- Test execution for changed files

### 2. Code Style

We use `ruff` for code formatting and linting:

```bash
# Format code
uv run ruff format .

# Check for issues
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .
```

### 3. Type Checking

```bash
# Run type checking
uv run mypy create_project/
```

## 🐛 Troubleshooting

### Common Issues

#### Issue: `uv: command not found`
**Solution**: Ensure uv is in your PATH:
```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

#### Issue: PyQt6 installation fails
**Solution**: Install system Qt dependencies:
```bash
# macOS
brew install qt6

# Linux
sudo apt install qt6-base-dev
```

#### Issue: Permission denied errors
**Solution**: Ensure you have write permissions:
```bash
chmod -R u+w .
```

#### Issue: Module import errors
**Solution**: Ensure you're running with uv:
```bash
# Wrong
python -m create_project

# Correct
uv run python -m create_project
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Set in .env file
APP_DEBUG=true
LOG_LEVEL=DEBUG

# Or via environment variable
APP_DEBUG=true uv run python -m create_project
```

## 📂 Project Structure

```
create-project/
├── create_project/          # Main package
│   ├── __init__.py
│   ├── __main__.py         # Entry point
│   ├── main.py             # Application initialization
│   ├── core/               # Core business logic
│   │   ├── __init__.py
│   │   ├── generator.py    # Project generation
│   │   └── validator.py    # Structure validation
│   ├── gui/                # PyQt GUI components
│   │   ├── __init__.py
│   │   ├── wizard.py       # Main wizard window
│   │   └── steps/          # Wizard step components
│   ├── utils/              # Utility functions
│   │   ├── __init__.py
│   │   ├── logger.py       # Logging configuration
│   │   └── helpers.py      # Helper functions
│   ├── templates/          # Project templates
│   │   ├── builtin/        # Built-in templates
│   │   └── user/           # User-defined templates
│   ├── resources/          # Application resources
│   │   ├── styles/         # QSS stylesheets
│   │   ├── icons/          # GUI icons
│   │   └── licenses/       # License templates
│   └── config/             # Configuration management
│       ├── __init__.py
│       ├── config_manager.py
│       ├── models.py       # Pydantic models
│       └── settings.json   # Default settings
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest configuration
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── gui/               # GUI tests
├── docs/                   # Documentation
│   ├── user/              # User documentation
│   ├── developer/         # Developer documentation
│   └── templates/         # Template documentation
├── scripts/               # Utility scripts
│   ├── setup-dev.sh       # Development setup (Unix)
│   ├── setup-dev.ps1      # Development setup (Windows)
│   └── validate-env.py    # Environment validation
├── .github/               # GitHub configuration
│   └── workflows/         # CI/CD workflows
├── pyproject.toml         # Project configuration
├── uv.lock               # Dependency lock file
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore rules
├── .pre-commit-config.yaml # Pre-commit hooks
├── README.md             # This file
├── LICENSE               # Apache 2.0 license
└── CONTRIBUTING.md       # Contribution guidelines
```

## 🚢 Deployment

### Building Standalone Executable

```bash
# Build for current platform
uv run python scripts/build.py

# Output will be in dist/
```

### Creating Distribution Package

```bash
# Build PyPI package
uv build

# Upload to PyPI (requires credentials)
uv publish
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:

- Code of Conduct
- Development workflow
- Commit message conventions
- Pull request process
- Testing requirements

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write or update tests
5. Ensure all tests pass (`uv run pytest`)
6. Commit your changes (`git commit -m 'feat: add amazing feature'`)
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📝 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🌟 Status

[![Tests](https://github.com/username/create-project/actions/workflows/test.yml/badge.svg)](https://github.com/username/create-project/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/username/create-project/branch/main/graph/badge.svg)](https://codecov.io/gh/username/create-project)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)

This project is in active development. See:
- [TODO.md](TODO.md) for current development tasks
- [CHANGELOG.md](CHANGELOG.md) for version history
- [GitHub Issues](https://github.com/username/create-project/issues) for bug reports and feature requests

## 💬 Support

- **Documentation**: See the `docs/` directory
- **Issues**: [GitHub Issues](https://github.com/username/create-project/issues)
- **Discussions**: [GitHub Discussions](https://github.com/username/create-project/discussions)

---

Made with ❤️ by the Python Project Creator team