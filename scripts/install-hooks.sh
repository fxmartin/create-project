#!/bin/bash

# ABOUTME: Pre-commit hooks installation script
# ABOUTME: Installs and configures pre-commit hooks for code quality

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

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    log_error "This script must be run from the project root directory"
    exit 1
fi

log_info "Installing pre-commit hooks..."

# Install pre-commit hooks
if uv run pre-commit install; then
    log_success "Pre-commit hooks installed successfully"
else
    log_error "Failed to install pre-commit hooks"
    exit 1
fi

# Install commit message hook
if uv run pre-commit install --hook-type commit-msg; then
    log_success "Commit message hook installed successfully"
else
    log_warning "Failed to install commit message hook"
fi

# Run pre-commit on all files to ensure everything works
log_info "Running pre-commit on all files to validate setup..."
if uv run pre-commit run --all-files; then
    log_success "Pre-commit validation passed"
else
    log_warning "Pre-commit found issues that need to be fixed"
    log_info "This is normal for the first run. Issues should be auto-fixed."
fi

log_success "Pre-commit setup complete!"
log_info "Hooks will now run automatically on commit."
log_info "You can manually run them with: uv run pre-commit run --all-files"