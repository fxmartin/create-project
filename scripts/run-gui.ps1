# ABOUTME: PowerShell launch script for GUI mode on Windows
# ABOUTME: Launches the Create Project GUI with environment detection

$ErrorActionPreference = "Stop"

# Get script and project directories
$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Path $scriptDir

Write-Host "Create Project - GUI Mode" -ForegroundColor Green
Write-Host "========================="

# Check if uv is available
try {
    $null = Get-Command uv -ErrorAction Stop
} catch {
    Write-Host "Error: uv is not installed" -ForegroundColor Red
    Write-Host "Please install uv first: https://github.com/astral-sh/uv"
    exit 1
}

# Check if virtual environment exists
$venvPath = Join-Path $projectRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    Set-Location $projectRoot
    & uv venv
    & uv sync
}

# Check for PyQt6
Set-Location $projectRoot
$pyqt6Check = & uv run python -c "import PyQt6" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyQt6 not found. Installing..." -ForegroundColor Yellow
    & uv add pyqt6
}

# Launch GUI with debug mode if requested
$debugMode = ($args -contains "--debug") -or ($env:DEBUG -eq "1")
if ($debugMode) {
    Write-Host "Launching GUI in debug mode..." -ForegroundColor Green
    $env:CREATE_PROJECT_DEBUG = "1"
    & uv run python -m create_project --gui --debug
} else {
    Write-Host "Launching GUI..." -ForegroundColor Green
    & uv run python -m create_project --gui
}

exit $LASTEXITCODE