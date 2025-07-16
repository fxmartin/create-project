# Contributing to Python Project Creator

Thank you for your interest in contributing to Python Project Creator! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## 🤝 Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## 🚀 Getting Started

### Prerequisites

- Python 3.9.6 or higher
- Git
- uv package manager

### Quick Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/create-project.git
   cd create-project
   ```

3. Set up the development environment:
   ```bash
   ./scripts/setup-dev.sh  # On macOS/Linux
   # OR
   ./scripts/setup-dev.ps1  # On Windows
   ```

4. Validate your setup:
   ```bash
   uv run python scripts/validate-env.py
   ```

## 🛠️ Development Setup

### Environment Setup

The project uses `uv` for dependency management. After cloning the repository:

```bash
# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your preferred settings

# Install pre-commit hooks
uv run pre-commit install
```

### IDE Configuration

We recommend using VS Code with the provided configuration:

1. Open the project in VS Code
2. Install recommended extensions when prompted
3. The project includes debugging configurations and tasks

For PyCharm users:
1. Import the project
2. Configure the interpreter to use the uv-created virtual environment
3. Enable ruff for code formatting

## 🔄 Development Workflow

### Branching Strategy

We use a simplified Git flow:

- `main` - Production-ready code
- `develop` - Development branch (if used)
- `feature/description` - Feature branches
- `bugfix/description` - Bug fix branches
- `hotfix/description` - Urgent fixes

### Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes following the coding standards
3. Write or update tests
4. Run the test suite:
   ```bash
   uv run pytest
   ```

5. Run code quality checks:
   ```bash
   uv run ruff check .
   uv run ruff format .
   uv run mypy create_project/
   ```

6. Commit your changes using conventional commits:
   ```bash
   git commit -m "feat: add new feature"
   ```

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat: add project template validation
fix: resolve configuration loading issue
docs: update README installation instructions
test: add unit tests for configuration manager
```

## 📏 Coding Standards

### Python Code Style

- Follow PEP 8 guidelines
- Use ruff for linting and formatting
- Maximum line length: 88 characters
- Use type hints for all functions and methods
- Write docstrings for all public functions, classes, and modules

### Code Quality Tools

The project uses several tools to maintain code quality:

- **ruff**: Fast linter and formatter
- **mypy**: Static type checking
- **pytest**: Testing framework
- **pre-commit**: Git hooks for code quality

### File Organization

- Use descriptive names for files and directories
- Keep related functionality together
- Follow the established project structure
- Add `__init__.py` files to make directories Python packages

### Documentation

- All public functions must have docstrings
- Use Google-style docstrings
- Include type hints in function signatures
- Document complex algorithms and business logic
- Update README.md for user-facing changes

Example docstring:
```python
def create_project(name: str, template: str, location: Path) -> bool:
    """
    Create a new project from a template.
    
    Args:
        name: The project name
        template: Template identifier
        location: Directory where project will be created
        
    Returns:
        True if project was created successfully, False otherwise
        
    Raises:
        ValueError: If template is not found
        PermissionError: If location is not writable
    """
```

## 🧪 Testing

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── gui/           # GUI tests
└── conftest.py    # Pytest configuration
```

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Include both positive and negative test cases
- Use fixtures for common test data
- Mock external dependencies

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_config.py

# Run with coverage
uv run pytest --cov=create_project --cov-report=html

# Run tests in parallel
uv run pytest -n auto
```

### GUI Testing

For PyQt GUI tests:
- Use pytest-qt for GUI testing
- Test user interactions and workflows
- Use QTest utilities for simulating user input
- Test both successful and error scenarios

## 📚 Documentation

### User Documentation

- Update README.md for user-facing changes
- Add examples for new features
- Update command-line help text
- Create or update user guides in `docs/user/`

### Developer Documentation

- Document architectural decisions
- Update API documentation
- Add inline comments for complex logic
- Update this contributing guide as needed

### Documentation Standards

- Use Markdown for documentation
- Include code examples where appropriate
- Keep documentation up-to-date with code changes
- Use clear, concise language
- Include diagrams for complex concepts

## 📤 Submitting Changes

### Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add entry to CHANGELOG.md (if exists)
4. Create a pull request with:
   - Clear title and description
   - Link to related issues
   - Screenshots for UI changes
   - Test results summary

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

### Review Process

1. Automated checks must pass
2. At least one maintainer review required
3. Address feedback and update PR
4. Final approval from maintainer
5. Merge when ready

## 🚀 Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):
- MAJOR: Incompatible API changes
- MINOR: New functionality (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Workflow

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release branch
4. Run full test suite
5. Create GitHub release with tag
6. Automated deployment to PyPI

## 🐛 Reporting Issues

### Bug Reports

Include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs
- Screenshots (if applicable)

### Feature Requests

Include:
- Problem description
- Proposed solution
- Use cases
- Alternative solutions considered

## 💡 Getting Help

- Check existing issues and documentation
- Ask questions in GitHub Discussions
- Join our community channels
- Contact maintainers directly

## 🏆 Recognition

Contributors are recognized in:
- GitHub contributors page
- CHANGELOG.md
- Release notes
- Project documentation

## 📄 License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for contributing to Python Project Creator! 🎉