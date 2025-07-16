#!/bin/bash

# ABOUTME: Developer utility scripts for common tasks
# ABOUTME: Provides convenient commands for development workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    echo "Python Project Creator - Development Utilities"
    echo
    echo "Usage: $0 <command> [options]"
    echo
    echo "Commands:"
    echo "  test              Run all tests"
    echo "  test-unit         Run unit tests only"
    echo "  test-integration  Run integration tests only"
    echo "  test-gui          Run GUI tests only"
    echo "  test-coverage     Run tests with coverage report"
    echo "  lint              Run linting (ruff check)"
    echo "  format            Format code (ruff format)"
    echo "  typecheck         Run type checking (mypy)"
    echo "  quality           Run all quality checks"
    echo "  clean             Clean build artifacts"
    echo "  build             Build package"
    echo "  run               Run the application"
    echo "  validate          Validate development environment"
    echo "  install-hooks     Install pre-commit hooks"
    echo "  update-deps       Update dependencies"
    echo "  help              Show this help message"
    echo
    echo "Examples:"
    echo "  $0 test           # Run all tests"
    echo "  $0 quality        # Run linting, formatting, and type checking"
    echo "  $0 clean          # Clean build artifacts"
}

# Run tests
run_tests() {
    log_info "Running all tests..."
    uv run pytest tests/ -v
}

run_unit_tests() {
    log_info "Running unit tests..."
    uv run pytest tests/unit/ -v
}

run_integration_tests() {
    log_info "Running integration tests..."
    uv run pytest tests/integration/ -v
}

run_gui_tests() {
    log_info "Running GUI tests..."
    uv run pytest tests/gui/ -v
}

run_coverage() {
    log_info "Running tests with coverage..."
    uv run pytest --cov=create_project --cov-report=html --cov-report=term
    log_success "Coverage report generated in htmlcov/"
}

# Code quality
run_lint() {
    log_info "Running linting..."
    uv run ruff check .
}

run_format() {
    log_info "Formatting code..."
    uv run ruff format .
}

run_typecheck() {
    log_info "Running type checking..."
    uv run mypy create_project/
}

run_quality() {
    log_info "Running all quality checks..."
    
    log_info "1. Linting..."
    run_lint
    
    log_info "2. Formatting check..."
    uv run ruff format --check .
    
    log_info "3. Type checking..."
    run_typecheck
    
    log_success "All quality checks passed!"
}

# Clean build artifacts
clean_build() {
    log_info "Cleaning build artifacts..."
    
    # Remove Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    
    # Remove build directories
    rm -rf build/ dist/ *.egg-info/
    
    # Remove test artifacts
    rm -rf .pytest_cache/ htmlcov/ .coverage
    
    # Remove mypy cache
    rm -rf .mypy_cache/
    
    # Remove ruff cache
    rm -rf .ruff_cache/
    
    log_success "Build artifacts cleaned!"
}

# Build package
build_package() {
    log_info "Building package..."
    clean_build
    uv build
    log_success "Package built successfully!"
}

# Run application
run_app() {
    log_info "Running application..."
    uv run python -m create_project
}

# Validate environment
validate_env() {
    log_info "Validating development environment..."
    uv run python scripts/validate-env.py
}

# Install pre-commit hooks
install_hooks() {
    log_info "Installing pre-commit hooks..."
    ./scripts/install-hooks.sh
}

# Update dependencies
update_deps() {
    log_info "Updating dependencies..."
    uv sync --upgrade
    log_success "Dependencies updated!"
}

# Main function
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    case "$1" in
        test)
            run_tests
            ;;
        test-unit)
            run_unit_tests
            ;;
        test-integration)
            run_integration_tests
            ;;
        test-gui)
            run_gui_tests
            ;;
        test-coverage)
            run_coverage
            ;;
        lint)
            run_lint
            ;;
        format)
            run_format
            ;;
        typecheck)
            run_typecheck
            ;;
        quality)
            run_quality
            ;;
        clean)
            clean_build
            ;;
        build)
            build_package
            ;;
        run)
            run_app
            ;;
        validate)
            validate_env
            ;;
        install-hooks)
            install_hooks
            ;;
        update-deps)
            update_deps
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"