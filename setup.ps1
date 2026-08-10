<#
.SYNOPSIS
    AI Lead Scraper CRM - Automated Setup Script for Windows
.DESCRIPTION
    This script automates the complete setup of the AI Lead Scraper CRM on a fresh Windows PC.
    It checks prerequisites, creates virtual environment, installs dependencies, and initializes the database.
.NOTES
    Run from the repository root directory.
    Requires: PowerShell 5.1+ (built into Windows 10/11)
#>

param(
    [switch]$SkipPrereqCheck,
    [switch]$SkipDocker,
    [switch]$SkipOllama,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$venvPath = Join-Path $repoRoot "venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"
$pipPath = Join-Path $venvPath "Scripts\pip.exe"

# Colors for output
$green = [ConsoleColor]::Green
$yellow = [ConsoleColor]::Yellow
$red = [ConsoleColor]::Red
$cyan = [ConsoleColor]::Cyan
$gray = [ConsoleColor]::DarkGray

function Write-Header {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor $cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✅ $Message" -ForegroundColor $green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  ⚠️  $Message" -ForegroundColor $yellow
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "  ❌ $Message" -ForegroundColor $red
}

function Write-Info {
    param([string]$Message)
    Write-Host "  ℹ️  $Message" -ForegroundColor $gray
}

function Check-Command {
    param([string]$Command, [string]$VersionFlag = "--version", [string]$Name = "")
    $displayName = if ($Name) { $Name } else { $Command }
    try {
        $output = & $Command $VersionFlag 2>&1 | Select-Object -First 1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$displayName found: $output"
            return $true
        }
    } catch {
        # Command not found
    }
    Write-ErrorMsg "$displayName not found or failed"
    return $false
}

function Check-Prerequisites {
    Write-Header "Checking Prerequisites"

    $allOk = $true

    # Python
    if (Check-Command "python" "--version" "Python") {
        $version = python --version 2>&1
        if ($version -notmatch "3\.(1[1-9]|[2-9]\d)") {
            Write-Warning "Python 3.11+ recommended, found: $version"
        }
    } else {
        $allOk = $false
    }

    # Node.js
    if (Check-Command "node" "--version" "Node.js") {
        $version = node --version 2>&1
        if ($version -notmatch "v(2[0-9]|[3-9]\d)") {
            Write-Warning "Node.js 20+ recommended, found: $version"
        }
    } else {
        $allOk = $false
    }

    # npm
    if (Check-Command "npm" "--version" "npm") { } else { $allOk = $false }

    # Docker
    if (-not $SkipDocker) {
        if (Check-Command "docker" "--version" "Docker") { } else { $allOk = $false }
    } else {
        Write-Warning "Skipping Docker check (--SkipDocker)"
    }

    # Ollama
    if (-not $SkipOllama) {
        if (Check-Command "ollama" "--version" "Ollama") { } else { $allOk = $false }
    } else {
        Write-Warning "Skipping Ollama check (--SkipOllama)"
    }

    # Git
    if (Check-Command "git" "--version" "Git") { } else { $allOk = $false }

    return $allOk
}

function Setup-VirtualEnvironment {
    Write-Header "Setting Up Python Virtual Environment"

    if (Test-Path $venvPath) {
        if ($Force) {
            Write-Warning "Removing existing venv..."
            Remove-Item $venvPath -Recurse -Force
        } else {
            Write-Info "Virtual environment already exists at $venvPath"
            return $true
        }
    }

    Write-Info "Creating virtual environment..."
    python -m venv $venvPath
    if (-not $?) { Write-ErrorMsg "Failed to create venv"; return $false }

    Write-Success "Virtual environment created"
    return $true
}

function Install-PythonDependencies {
    Write-Header "Installing Python Dependencies"

    $reqFile = Join-Path $repoRoot "requirements.txt"
    if (-not (Test-Path $reqFile)) {
        Write-ErrorMsg "requirements.txt not found at $reqFile"
        return $false
    }

    Write-Info "Upgrading pip..."
    & $pythonPath -m pip install --upgrade pip -q
    if (-not $?) { Write-Warning "pip upgrade had issues (continuing)" }

    Write-Info "Installing from requirements.txt..."
    & $pipPath install -r $reqFile
    if (-not $?) { Write-ErrorMsg "Failed to install Python dependencies"; return $false }

    Write-Info "Installing Playwright Chromium..."
    & $pythonPath -m playwright install chromium
    if (-not $?) { Write-Warning "Playwright install had issues (may need admin)" }

    Write-Success "Python dependencies installed"
    return $true
}

function Setup-Frontend {
    Write-Header "Setting Up Frontend"

    $frontendDir = Join-Path $repoRoot "frontend"
    if (-not (Test-Path $frontendDir)) {
        Write-ErrorMsg "frontend directory not found"
        return $false
    }

    Push-Location $frontendDir
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Info "Running npm install..."
            npm install
            if (-not $?) { Write-ErrorMsg "npm install failed"; return $false }
        } else {
            Write-Info "node_modules already exists, skipping npm install"
        }
        Write-Success "Frontend dependencies installed"
    } finally {
        Pop-Location
    }
    return $true
}

function Setup-Environment {
    Write-Header "Setting Up Environment Variables"

    $envExample = Join-Path $repoRoot ".env.example"
    $envFile = Join-Path $repoRoot ".env"

    if (Test-Path $envFile) {
        Write-Info ".env already exists, skipping copy"
        return $true
    }

    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile -Force
        Write-Success "Created .env from .env.example"
        Write-Warning "IMPORTANT: Edit .env with your configuration (especially OLLAMA_BASE_URL, SCRAPEGRAPH_MODEL)"
    } else {
        Write-ErrorMsg ".env.example not found"
        return $false
    }
    return $true
}

function Initialize-Database {
    Write-Header "Initializing Database"

    $dataDir = Join-Path $repoRoot "data"
    if (-not (Test-Path $dataDir)) {
        New-Item -ItemType Directory -Path $dataDir | Out-Null
        Write-Info "Created data/ directory"
    }

    Write-Info "Running database initialization..."
    & $pythonPath -c "from scraper.database import initialize_database; initialize_database(); print('Database initialized successfully')"
    if (-not $?) { Write-ErrorMsg "Database initialization failed"; return $false }

    Write-Success "Database initialized"
    return $true
}

function Verify-Setup {
    Write-Header "Verifying Setup"

    $checks = @()

    # Check venv
    $checks += @{ Name = "Virtual Environment"; Path = $venvPath; Test = { Test-Path $venvPath } }

    # Check .env
    $checks += @{ Name = "Environment File"; Path = (Join-Path $repoRoot ".env"); Test = { Test-Path (Join-Path $repoRoot ".env") } }

    # Check database
    $checks += @{ Name = "Database File"; Path = (Join-Path $repoRoot "data\leads.db"); Test = { Test-Path (Join-Path $repoRoot "data\leads.db") } }

    # Check frontend node_modules
    $checks += @{ Name = "Frontend Dependencies"; Path = (Join-Path $repoRoot "frontend\node_modules"); Test = { Test-Path (Join-Path $repoRoot "frontend\node_modules") } }

    $allPassed = $true
    foreach ($check in $checks) {
        if (& $check.Test) {
            Write-Success "$($check.Name): OK"
        } else {
            Write-ErrorMsg "$($check.Name): MISSING"
            $allPassed = $false
        }
    }

    # Quick import test
    Write-Info "Testing Python imports..."
    & $pythonPath -c "
import flask
import scraper.database
import scraper.ai_enrichment
import scraper.scoring
import api.app
print('All core modules import successfully')
"
    if ($?) {
        Write-Success "Python imports: OK"
    } else {
        Write-ErrorMsg "Python imports: FAILED"
        $allPassed = $false
    }

    return $allPassed
}

function Print-NextSteps {
    Write-Header "Setup Complete! Next Steps"

    Write-Host "`nTo start the application, you need 4 terminal windows:" -ForegroundColor $cyan

    Write-Host "`n1. Ollama (if not running as service):" -ForegroundColor $yellow
    Write-Host "   ollama serve"

    Write-Host "`n2. Gosom Google Maps Scraper (Docker):" -ForegroundColor $yellow
    Write-Host "   docker start gosom-scraper"
    Write-Host "   # Or first time: docker run -d --name gosom-scraper -p 8080:8080 gosom/google-maps-scraper"

    Write-Host "`n3. Backend API:" -ForegroundColor $yellow
    Write-Host "   cd $repoRoot"
    Write-Host "   .\venv\Scripts\Activate.ps1"
    Write-Host "   python api\app.py"
    Write-Host "   # API runs at http://localhost:5000"

    Write-Host "`n4. Frontend:" -ForegroundColor $yellow
    Write-Host "   cd $repoRoot\frontend"
    Write-Host "   npm run dev"
    Write-Host "   # Frontend runs at http://localhost:5173"

    Write-Host "`nVerification commands:" -ForegroundColor $cyan
    Write-Host "   curl http://localhost:5000/api/health"
    Write-Host "   curl http://localhost:8080/api/v1/health"
    Write-Host "   curl http://localhost:11434/api/tags"

    Write-Host "`nDocumentation:" -ForegroundColor $cyan
    Write-Host "   README.md - Complete project overview"
    Write-Host "   docs/SETUP.md - Detailed setup guide"
    Write-Host "   docs/API.md - API reference"
    Write-Host "   docs/ARCHITECTURE.md - System architecture"
    Write-Host "   docs/TROUBLESHOOTING.md - Common issues"
    Write-Host "   docs/N8N_INTEGRATION_HANDOFF.md - n8n integration guide"
}

# ============================================================
# MAIN
# ============================================================

Write-Host "`n╔══════════════════════════════════════════════════════════════╗"
Write-Host "║     AI Lead Scraper CRM - Automated Windows Setup           ║"
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor $cyan

Write-Info "Repository: $repoRoot"
Write-Info "Virtual Env: $venvPath"

$success = $true

if (-not $SkipPrereqCheck) {
    $success = Check-Prerequisites
    if (-not $success -and -not $Force) {
        Write-ErrorMsg "Prerequisites check failed. Install missing tools or use -Force to continue anyway."
        exit 1
    }
}

$success = Setup-VirtualEnvironment
if (-not $success) { exit 1 }

$success = Install-PythonDependencies
if (-not $success) { exit 1 }

$success = Setup-Frontend
if (-not $success) { exit 1 }

$success = Setup-Environment
if (-not $success) { exit 1 }

$success = Initialize-Database
if (-not $success) { exit 1 }

$success = Verify-Setup
if (-not $success) {
    Write-Warning "Some verification checks failed. Review output above."
}

Print-NextSteps

Write-Host "`n✅ Setup script completed successfully!" -ForegroundColor $green