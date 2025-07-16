# ABOUTME: Development environment setup script for Windows PowerShell
# ABOUTME: Automates the complete development environment setup process

param(
    [switch]$Help
)

# Error handling
$ErrorActionPreference = "Stop"

# Colors for output
$Colors = @{
    Info = "Blue"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
}

# Logging functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Info
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Success
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Warning
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Error
}

# Check if command exists
function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Check Python version
function Test-PythonVersion {
    Write-Info "Checking Python version..."
    
    if (-not (Test-Command "python")) {
        Write-Error "Python is not installed or not in PATH. Please install Python 3.9.6 or higher."
        exit 1
    }
    
    try {
        $pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
        $requiredVersion = [version]"3.9.6"
        $currentVersion = [version]$pythonVersion
        
        if ($currentVersion -lt $requiredVersion) {
            Write-Error "Python $pythonVersion is installed, but version $requiredVersion or higher is required."
            Write-Info "Please install Python $requiredVersion or higher."
            exit 1
        }
        
        Write-Success "Python $pythonVersion is installed and meets requirements."
    }
    catch {
        Write-Error "Failed to check Python version: $_"
        exit 1
    }
}

# Install uv package manager
function Install-Uv {
    Write-Info "Checking uv installation..."
    
    if (Test-Command "uv") {
        $uvVersion = (uv --version).Split(' ')[1]
        Write-Success "uv $uvVersion is already installed."
        return
    }
    
    Write-Info "Installing uv package manager..."
    try {
        Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" | Invoke-Expression
        
        # Refresh PATH for current session
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        if (Test-Command "uv") {
            $uvVersion = (uv --version).Split(' ')[1]
            Write-Success "uv $uvVersion installed successfully."
        }
        else {
            Write-Error "Failed to install uv. Please install manually."
            exit 1
        }
    }
    catch {
        Write-Error "Failed to install uv: $_"
        exit 1
    }
}

# Install project dependencies
function Install-Dependencies {
    Write-Info "Installing project dependencies..."
    
    if (-not (Test-Path "pyproject.toml")) {
        Write-Error "pyproject.toml not found. Are you in the project root directory?"
        exit 1
    }
    
    try {
        uv sync
        Write-Success "Dependencies installed successfully."
    }
    catch {
        Write-Error "Failed to install dependencies: $_"
        exit 1
    }
}

# Create .env file from template
function Set-EnvFile {
    Write-Info "Setting up environment file..."
    
    if (-not (Test-Path ".env.example")) {
        Write-Warning ".env.example not found. Skipping environment file setup."
        return
    }
    
    if (Test-Path ".env") {
        Write-Warning ".env file already exists. Skipping creation."
        return
    }
    
    try {
        Copy-Item ".env.example" ".env"
        Write-Success ".env file created from template."
        Write-Info "Please review and customize the .env file as needed."
    }
    catch {
        Write-Error "Failed to create .env file: $_"
        exit 1
    }
}

# Set up pre-commit hooks
function Set-PreCommitHooks {
    Write-Info "Setting up pre-commit hooks..."
    
    try {
        # Check if pre-commit is installed
        uv run python -c "import pre_commit" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Info "Installing pre-commit..."
            uv add --dev pre-commit
        }
        
        # Install pre-commit hooks
        if (Test-Path ".pre-commit-config.yaml") {
            uv run pre-commit install
            Write-Success "Pre-commit hooks installed successfully."
        }
        else {
            Write-Warning ".pre-commit-config.yaml not found. Skipping pre-commit setup."
        }
    }
    catch {
        Write-Warning "Failed to set up pre-commit hooks: $_"
    }
}

# Validate installation
function Test-Installation {
    Write-Info "Validating installation..."
    
    try {
        # Check if we can import the main module
        uv run python -c "import create_project" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Main module can be imported successfully."
        }
        else {
            Write-Error "Failed to import main module. Installation may be incomplete."
            exit 1
        }
        
        # Run basic tests if available
        if (Test-Path "tests") {
            Write-Info "Running basic tests..."
            uv run pytest tests/ -x -q
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Basic tests passed."
            }
            else {
                Write-Warning "Some tests failed. Please check the output above."
            }
        }
    }
    catch {
        Write-Error "Failed to validate installation: $_"
        exit 1
    }
}

# Create necessary directories
function New-Directories {
    Write-Info "Creating necessary directories..."
    
    $directories = @("logs", "data", "build", "dist")
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            try {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                Write-Info "Created directory: $dir"
            }
            catch {
                Write-Warning "Failed to create directory $dir: $_"
            }
        }
    }
}

# Show help message
function Show-Help {
    Write-Host @"
Python Project Creator - Development Environment Setup Script

USAGE:
    .\scripts\setup-dev.ps1 [OPTIONS]

OPTIONS:
    -Help          Show this help message

DESCRIPTION:
    This script automates the setup of the development environment for
    the Python Project Creator project. It will:
    
    1. Check Python version (3.9.6+ required)
    2. Install uv package manager
    3. Install project dependencies
    4. Set up .env file from template
    5. Create necessary directories
    6. Set up pre-commit hooks
    7. Validate the installation
    
EXAMPLES:
    .\scripts\setup-dev.ps1          # Run full setup
    .\scripts\setup-dev.ps1 -Help    # Show this help
    
REQUIREMENTS:
    - Windows PowerShell 5.0+ or PowerShell Core 7.0+
    - Python 3.9.6 or higher
    - Internet connection for downloading dependencies
    
For more information, see the README.md file.
"@
}

# Main setup function
function Start-Setup {
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Info "Starting Python Project Creator development environment setup..."
    Write-Host ""
    
    # Check if we're in the right directory
    if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "create_project")) {
        Write-Error "This doesn't appear to be the Python Project Creator root directory."
        Write-Error "Please run this script from the project root directory."
        exit 1
    }
    
    try {
        # Run setup steps
        Test-PythonVersion
        Install-Uv
        Install-Dependencies
        Set-EnvFile
        New-Directories
        Set-PreCommitHooks
        Test-Installation
        
        Write-Host ""
        Write-Success "Development environment setup completed successfully!"
        Write-Host ""
        Write-Info "You can now:"
        Write-Info "  • Run the application: uv run python -m create_project"
        Write-Info "  • Run tests: uv run pytest"
        Write-Info "  • Format code: uv run ruff format ."
        Write-Info "  • Check code: uv run ruff check ."
        Write-Info "  • Type check: uv run mypy create_project/"
        Write-Host ""
        Write-Info "For more information, see the README.md file."
        Write-Info "Happy coding! 🎉"
    }
    catch {
        Write-Error "Setup failed: $_"
        exit 1
    }
}

# Run main function
Start-Setup