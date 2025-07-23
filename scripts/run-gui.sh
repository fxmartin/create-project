#!/bin/bash
# ABOUTME: Bash launch script for GUI mode on macOS/Linux
# ABOUTME: Launches the Create Project GUI with environment detection

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Create Project - GUI Mode${NC}"
echo "========================="

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Please install uv first: https://github.com/astral-sh/uv"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    cd "$PROJECT_ROOT"
    uv venv
    uv sync
fi

# Check for PyQt6
cd "$PROJECT_ROOT"
if ! uv run python -c "import PyQt6" 2>/dev/null; then
    echo -e "${YELLOW}PyQt6 not found. Installing...${NC}"
    uv add pyqt6
fi

# Launch GUI with debug mode if requested
if [ "$1" == "--debug" ] || [ "$DEBUG" == "1" ]; then
    echo -e "${GREEN}Launching GUI in debug mode...${NC}"
    export CREATE_PROJECT_DEBUG=1
    uv run python -m create_project --gui --debug
else
    echo -e "${GREEN}Launching GUI...${NC}"
    uv run python -m create_project --gui
fi