#!/bin/bash

# ABOUTME: Development environment setup script for macOS/Linux
# ABOUTME: Automates the complete development environment setup process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python_version() {
    log_info "Checking Python version..."
    
    if ! command_exists python3; then
        log_error "Python 3 is not installed. Please install Python 3.9.6 or higher."
        exit 1
    fi
    
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
    local required_version="3.9.6"
    
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9, 6) else 1)" 2>/dev/null; then
        log_error "Python ${python_version} is installed, but version ${required_version} or higher is required."
        log_info "Please install Python ${required_version} or higher."
        exit 1
    fi
    
    log_success "Python ${python_version} is installed and meets requirements."
}

# Install uv package manager
install_uv() {
    log_info "Checking uv installation..."
    
    if command_exists uv; then
        local uv_version=$(uv --version | cut -d' ' -f2)
        log_success "uv ${uv_version} is already installed."
        return 0
    fi
    
    log_info "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add uv to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if command_exists uv; then
        local uv_version=$(uv --version | cut -d' ' -f2)
        log_success "uv ${uv_version} installed successfully."
    else
        log_error "Failed to install uv. Please install manually."
        exit 1
    fi
}

# Install project dependencies
install_dependencies() {
    log_info "Installing project dependencies..."
    
    if [ ! -f "pyproject.toml" ]; then
        log_error "pyproject.toml not found. Are you in the project root directory?"
        exit 1
    fi
    
    # Sync dependencies
    uv sync
    
    log_success "Dependencies installed successfully."
}

# Create .env file from template
setup_env_file() {
    log_info "Setting up environment file..."
    
    if [ ! -f ".env.example" ]; then
        log_warning ".env.example not found. Skipping environment file setup."
        return 0
    fi
    
    if [ -f ".env" ]; then
        log_warning ".env file already exists. Skipping creation."
        return 0
    fi
    
    cp .env.example .env
    log_success ".env file created from template."
    log_info "Please review and customize the .env file as needed."
}

# Set up pre-commit hooks
setup_pre_commit() {
    log_info "Setting up pre-commit hooks..."
    
    # Install pre-commit if not already installed
    if ! uv run python -c "import pre_commit" 2>/dev/null; then
        log_info "Installing pre-commit..."
        uv add --dev pre-commit
    fi
    
    # Install pre-commit hooks
    if [ -f ".pre-commit-config.yaml" ]; then
        uv run pre-commit install
        log_success "Pre-commit hooks installed successfully."
    else
        log_warning ".pre-commit-config.yaml not found. Skipping pre-commit setup."
    fi
}

# Validate installation
validate_installation() {
    log_info "Validating installation..."
    
    # Check if we can import the main module
    if uv run python -c "import create_project" 2>/dev/null; then
        log_success "Main module can be imported successfully."
    else
        log_error "Failed to import main module. Installation may be incomplete."
        exit 1
    fi
    
    # Run basic tests if available
    if [ -d "tests" ]; then
        log_info "Running basic tests..."
        if uv run pytest tests/ -x -q; then
            log_success "Basic tests passed."
        else
            log_warning "Some tests failed. Please check the output above."
        fi
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    local directories=(
        "logs"
        "data"
        "build"
        "dist"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
}

# Main setup function
main() {
    log_info "Starting Python Project Creator development environment setup..."
    echo
    
    # Check if we're in the right directory
    if [ ! -f "pyproject.toml" ] || [ ! -d "create_project" ]; then
        log_error "This doesn't appear to be the Python Project Creator root directory."
        log_error "Please run this script from the project root directory."
        exit 1
    fi
    
    # Run setup steps
    check_python_version
    install_uv
    install_dependencies
    setup_env_file
    create_directories
    setup_pre_commit
    validate_installation
    
    echo
    log_success "Development environment setup completed successfully!"
    echo
    log_info "You can now:"
    log_info "  • Run the application: uv run python -m create_project"
    log_info "  • Run tests: uv run pytest"
    log_info "  • Format code: uv run ruff format ."
    log_info "  • Check code: uv run ruff check ."
    log_info "  • Type check: uv run mypy create_project/"
    echo
    log_info "For more information, see the README.md file."
    log_info "Happy coding! 🎉"
}

# Run main function
main "$@"