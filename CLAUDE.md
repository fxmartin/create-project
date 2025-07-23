# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a PyQt-based GUI application for creating Python project structures. It's a mature, well-architected project with comprehensive testing, modern Python tooling, and professional development practices. The project is currently in Milestone 5 of 7 milestones, with a solid enterprise-grade foundation and core engine fully implemented.

**Key Technologies:**
- Python 3.9.6+ (strict requirement)
- PyQt6 for GUI framework
- uv for fast package management
- Pydantic for data validation
- structlog for advanced logging
- pytest with pytest-qt for testing
- httpx for async HTTP requests (Ollama AI integration)
- Jinja2 for template rendering

## Common Development Commands

### Environment Setup
```bash
# Initial setup (run once)
./scripts/setup-dev.sh  # macOS/Linux
# OR
./scripts/setup-dev.ps1  # Windows

# Verify environment
uv run python scripts/validate-env.py
```

### Running the Application
```bash
# Run the main application
uv run python -m create_project

# Run with debug logging
APP_DEBUG=true uv run python -m create_project
```

### Testing
```bash
# Run all tests (718 tests, 89.3% passing)
uv run pytest

# Run with coverage
uv run pytest --cov=create_project --cov-report=html

# Run specific test categories
uv run pytest tests/unit/          # Unit tests
uv run pytest tests/integration/   # Integration tests  
uv run pytest tests/gui/           # GUI tests

# Run tests in parallel
uv run pytest -n auto
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Type checking
uv run mypy create_project/
```

### Build and Package
```bash
# Build PyPI package
uv build

# Build standalone executable
uv run python scripts/build.py
```

## Architecture Overview

### Core Components

**Configuration System (`create_project/config/`):**
- Thread-safe configuration management with `ConfigManager`
- Pydantic models for type-safe configuration in `models.py`
- Supports JSON files, environment variables, and nested dot notation
- Comprehensive test suite (56 tests) ensuring reliability
- AI service configuration with Ollama connection settings

**Logging System (`create_project/utils/logger.py`):**
- Structured logging with structlog and colorlog
- File rotation and console output
- Configurable log levels and formats
- Thread-safe operation

**Project Structure:**
```
create_project/
├── config/              # ✅ Configuration management (complete)
├── utils/               # ✅ Logging and utilities (complete)
├── core/                # ✅ Business logic (complete)
├── templates/           # ✅ Project templates (complete)
├── ai/                  # ✅ Ollama AI integration (complete)
├── gui/                 # 🚧 PyQt interface (current)
└── resources/           # 📋 UI assets (planned)
```

### Development Status

**✅ Completed (Milestone 1-4):**
- Complete project structure with build system and CI/CD
- Thread-safe configuration management with Pydantic validation
- Advanced logging system with rotation
- Complete template system with 6 built-in templates
- Core project generation engine with atomic operations
- Git integration and virtual environment support
- Security features: command whitelisting, path traversal prevention
- Ollama AI integration with caching and error assistance
- 718 comprehensive tests (641 passing)

**🚧 Current Work (Milestone 5 - GUI Implementation):**
- PyQt6 wizard interface with 5 steps
- 9/35 tasks completed (25.7%)
- All wizard steps implemented with validation
- Working on custom widgets and dialogs

**📋 Upcoming (Milestones 6-7):**
- Integration & testing
- Distribution and packaging

## Testing Requirements

This project maintains **comprehensive test coverage** with strict requirements:

- **Unit Tests**: All business logic must be unit tested
- **Integration Tests**: Component interactions must be tested
- **GUI Tests**: PyQt components tested with pytest-qt
- **Thread Safety**: Concurrent operations tested
- **Configuration**: All config scenarios covered (26 tests)

**Test Organization:**
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for component interactions
- `tests/gui/` - GUI tests using pytest-qt
- `tests/config/` - Configuration system tests
- `tests/ai/` - AI module tests with mock infrastructure

## Code Style and Standards

### Strict Requirements
- **Python Version**: 3.9.6+ (strictly enforced)
- **Type Hints**: All functions must have type hints (mypy strict mode)
- **File Headers**: All files must start with 2-line ABOUTME comments
- **Testing**: TDD approach - write tests before implementation
- **Code Quality**: Pre-commit hooks enforce ruff formatting and linting

### Code Organization
- Use Pydantic models for all configuration and data validation
- Thread-safe operations for all shared resources
- Structured logging with appropriate log levels
- Follow existing patterns in config/ and utils/ directories

## Dependencies and Tools

### Core Dependencies
- PyQt6 >=6.9.1 (GUI framework)
- pydantic >=2.11.7 (data validation)
- structlog >=25.4.0 (structured logging)
- requests >=2.32.4 (HTTP client)
- jinja2 >=3.1.6 (templating)
- httpx >=0.25.0 (async HTTP for Ollama AI)

### Development Tools
- uv (package management - replaces pip/poetry)
- ruff >=0.12.3 (linting and formatting)
- mypy >=1.17.0 (type checking)
- pytest >=8.4.1 (testing)
- pytest-qt >=4.5.0 (GUI testing)
- pre-commit >=4.2.0 (git hooks)

## Important Notes

### Package Management
- **Always use uv**: Never use pip directly
- **Virtual Environment**: Managed automatically by uv
- **Dependencies**: Defined in pyproject.toml, locked in uv.lock

### Configuration
- Settings loaded from `config/settings.json` and `.env`
- Use `ConfigManager` for all configuration access
- Thread-safe operations are critical

### Logging
- Use structured logging via the logger utility
- Log levels: DEBUG, INFO, WARNING, ERROR
- Logs rotate automatically based on configuration

### Pre-commit Hooks
- **Required**: All commits must pass pre-commit hooks
- **Never use**: `--no-verify` flag when committing
- **Includes**: Code formatting, linting, type checking, security scanning

## Current Development Focus

The project is currently working on **Milestone 5: GUI Implementation**. Key areas of focus:

1. **Wizard Framework**: 5-step wizard with validation and data flow
2. **Custom Widgets**: Progress dialogs, error handling, settings management
3. **Visual Styling**: Professional QSS stylesheets
4. **Integration**: Connecting GUI to existing core engine

### Recent Major Achievements:
- Complete core engine with 8 components (PathHandler, DirectoryCreator, FileRenderer, GitManager, VenvManager, CommandExecutor, ThreadingModel, ProjectGenerator)
- Enterprise-grade AI integration with Ollama (auto-detection, caching, error context)
- All 5 wizard steps implemented with validation and data flow
- 718 comprehensive tests with 89.3% success rate

When contributing, focus on:
- Following the established patterns in config/, core/, and templates/
- Maintaining comprehensive test coverage with TDD approach
- Using Pydantic models for data validation
- Implementing thread-safe operations for GUI compatibility
- Designing for graceful degradation when external services unavailable