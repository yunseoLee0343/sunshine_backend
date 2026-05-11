#Requires -Version 5.1
<#
.SYNOPSIS
  Sunshine Windows one-command development bootstrap.

.DESCRIPTION
  This script prepares and runs the Sunshine backend + frontend on Windows.

  What it does:
  1. Finds or clones https://github.com/yunseoLee0343/sunshine_backend.git
  2. Starts backend dependencies and backend API through Docker Compose
  3. Runs Alembic migrations inside the backend container
  4. Loads idempotent demo seed data
  5. Restores frontend/src/api/client.ts to UTF-8 and aligns DEMO_USER_ID with the repo seed user
  6. Installs frontend npm dependencies
  7. Starts the Vite frontend dev server
  8. Opens http://localhost:5173 and http://localhost:8000/docs

.PARAMETER RepoRoot
  Existing repository path. If omitted, the script searches upward from the current directory.
  If no repo is found, it clones into .\sunshine_backend.

.PARAMETER ResetPostgres
  Stops Docker Compose and deletes volumes before starting. Use this for a clean database.

.PARAMETER PullLatest
  Runs git pull in the repository before starting.

.PARAMETER SkipNpmInstall
  Skips npm install in frontend/.

.PARAMETER ForegroundFrontend
  Runs npm run dev in the current PowerShell window instead of opening a new window.

.PARAMETER NoBrowser
  Does not open browser tabs.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\windows_dev_bootstrap.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\windows_dev_bootstrap.ps1 -ResetPostgres
#>

[CmdletBinding()]
param(
  [string]$RepoRoot = "",
  [switch]$ResetPostgres,
  [switch]$PullLatest,
  [switch]$SkipNpmInstall,
  [switch]$ForegroundFrontend,
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$RepoUrl = "https://github.com/yunseoLee0343/sunshine_backend.git"

# This value is from app/seeds/demo_seed.py via demo_id("user-001")
# and matches the checked-in frontend/src/api/client.ts in the live repository.
$SeedDemoUserId = "7923c9bd-80d8-d2d1-1937-b9e0e7e28887"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
  param([string]$Message)
  Write-Host "OK: $Message" -ForegroundColor Green
}

function Fail {
  param([string]$Message)
  throw $Message
}

function Require-Command {
  param(
    [string]$Name,
    [string]$InstallHint
  )

  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Fail "Required command '$Name' was not found. $InstallHint"
  }
}

function Invoke-Checked {
  param(
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$ErrorMessage
  )

  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    Fail "$ErrorMessage Exit code: $LASTEXITCODE"
  }
}

function Invoke-Compose {
  param([string[]]$Arguments)

  & docker compose @Arguments
  if ($LASTEXITCODE -ne 0) {
    Fail "docker compose $($Arguments -join ' ') failed. Exit code: $LASTEXITCODE"
  }
}

function Find-RepoRoot {
  param([string]$StartPath)

  $current = (Resolve-Path $StartPath).Path

  while ($true) {
    if (
      (Test-Path (Join-Path $current "docker-compose.yml")) -and
      (Test-Path (Join-Path $current "frontend\package.json"))
    ) {
      return $current
    }

    $parent = Split-Path -Parent $current
    if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
      return $null
    }

    $current = $parent
  }
}

function Resolve-Repo {
  if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
    if (-not (Test-Path $RepoRoot)) {
      Fail "RepoRoot does not exist: $RepoRoot"
    }

    $resolved = (Resolve-Path $RepoRoot).Path
    if (-not (Test-Path (Join-Path $resolved "docker-compose.yml"))) {
      Fail "RepoRoot is not the Sunshine repo root: $resolved"
    }
    return $resolved
  }

  $fromCurrent = Find-RepoRoot -StartPath (Get-Location).Path
  if ($fromCurrent) {
    return $fromCurrent
  }

  if ($PSScriptRoot) {
    $fromScript = Find-RepoRoot -StartPath $PSScriptRoot
    if ($fromScript) {
      return $fromScript
    }
  }

  $defaultClonePath = Join-Path (Get-Location).Path "sunshine_backend"

  if (Test-Path (Join-Path $defaultClonePath "docker-compose.yml")) {
    return (Resolve-Path $defaultClonePath).Path
  }

  Write-Step "Repository not found. Cloning into $defaultClonePath"
  Require-Command "git" "Install Git for Windows: https://git-scm.com/download/win"
  Invoke-Checked -FilePath "git" -Arguments @("clone", $RepoUrl, $defaultClonePath) -ErrorMessage "git clone failed."
  return (Resolve-Path $defaultClonePath).Path
}

function Set-Or-AppendEnvLine {
  param(
    [string]$Path,
    [string]$Key,
    [string]$Value
  )

  $line = "$Key=$Value"

  if (-not (Test-Path $Path)) {
    [System.IO.File]::WriteAllText($Path, "$line`n", (New-Object System.Text.UTF8Encoding($false)))
    return
  }

  $text = Read-TextBestEffort -Path $Path
  $lines = $text -split "`r?`n"
  $found = $false

  $updated = foreach ($existing in $lines) {
    if ($existing -match "^\s*$([Regex]::Escape($Key))=") {
      $found = $true
      $line
    } else {
      $existing
    }
  }

  if (-not $found) {
    $updated += $line
  }

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, (($updated -join "`n").TrimEnd() + "`n"), $utf8NoBom)
}

function Read-TextBestEffort {
  param([string]$Path)

  $bytes = [System.IO.File]::ReadAllBytes($Path)

  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    return [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
  }

  if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
    return [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
  }

  if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
    return [System.Text.Encoding]::BigEndianUnicode.GetString($bytes, 2, $bytes.Length - 2)
  }

  $strictUtf8 = New-Object System.Text.UTF8Encoding($false, $true)
  try {
    return $strictUtf8.GetString($bytes)
  } catch {
    # Windows PowerShell 5.1 Set-Content often writes UTF-16LE.
    return [System.Text.Encoding]::Unicode.GetString($bytes)
  }
}

function Write-Utf8NoBom {
  param(
    [string]$Path,
    [string]$Text
  )

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

function Wait-HttpOk {
  param(
    [string]$Url,
    [string]$Name,
    [int]$TimeoutSec = 120
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  $lastError = $null

  while ((Get-Date) -lt $deadline) {
    try {
      $res = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($res.StatusCode -ge 200 -and $res.StatusCode -lt 300) {
        Write-Ok "$Name is responding at $Url"
        return
      }
    } catch {
      $lastError = $_.Exception.Message
    }

    Start-Sleep -Seconds 2
  }

  Fail "$Name did not become ready at $Url within $TimeoutSec seconds. Last error: $lastError"
}

Write-Step "Checking prerequisites"
Require-Command "docker" "Install Docker Desktop and start it: https://www.docker.com/products/docker-desktop/"
Require-Command "npm" "Install Node.js LTS, which includes npm: https://nodejs.org/"

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
  Fail "Docker is installed but not running. Start Docker Desktop, then rerun this script."
}

& docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
  Fail "Docker Compose plugin is not available. Update Docker Desktop."
}

$root = Resolve-Repo
Write-Ok "Repository root: $root"

Push-Location $root
try {
  if ($PullLatest) {
    Write-Step "Pulling latest source"
    Require-Command "git" "Install Git for Windows: https://git-scm.com/download/win"
    Invoke-Checked -FilePath "git" -Arguments @("pull", "--ff-only") -ErrorMessage "git pull failed."
  }

  Write-Step "Preparing .env"
  if ((Test-Path ".env.example") -and -not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env" -Force
  }

  # Useful for local commands. Docker Compose backend uses its own DATABASE_URL from docker-compose.yml.
  Set-Or-AppendEnvLine -Path ".env" -Key "DATABASE_URL" -Value "postgresql+asyncpg://sunshine:change-me-local-only@localhost:5432/sunshine"
  Set-Or-AppendEnvLine -Path ".env" -Key "APP_ENV" -Value "local"
  Set-Or-AppendEnvLine -Path ".env" -Key "APP_NAME" -Value "sunshine-backend"
  Set-Or-AppendEnvLine -Path ".env" -Key "MQTT_HOST" -Value "localhost"
  Set-Or-AppendEnvLine -Path ".env" -Key "MQTT_PORT" -Value "1883"
  Write-Ok ".env ready"

  if ($ResetPostgres) {
    Write-Step "Resetting Docker Compose stack and volumes"
    Invoke-Compose -Arguments @("down", "-v", "--remove-orphans")
  }

  Write-Step "Starting backend stack with Docker Compose"
  Invoke-Compose -Arguments @("up", "--build", "-d", "postgres", "mqtt", "backend", "mqtt-ingest")

  Write-Step "Waiting for backend health endpoint"
  Wait-HttpOk -Url "http://localhost:8000/healthz" -Name "Backend health" -TimeoutSec 180

  Write-Step "Running database migrations"
  Invoke-Compose -Arguments @("exec", "-T", "backend", "alembic", "upgrade", "head")
  Write-Ok "Migrations complete"

  Write-Step "Loading idempotent demo seed data"
  Invoke-Compose -Arguments @("exec", "-T", "backend", "python", "-m", "app.seeds.demo_seed")
  Write-Ok "Seed complete"

  Write-Step "Checking backend readiness"
  Wait-HttpOk -Url "http://localhost:8000/readyz" -Name "Backend readiness" -TimeoutSec 120

  Write-Step "Repairing frontend client encoding and demo user"
  $clientPath = Join-Path $root "frontend\src\api\client.ts"
  if (-not (Test-Path $clientPath)) {
    Fail "Missing frontend client file: $clientPath"
  }

  $clientText = Read-TextBestEffort -Path $clientPath
  $clientText = [Regex]::Replace(
    $clientText,
    "const\s+DEMO_USER_ID\s*=\s*'[^']+'",
    "const DEMO_USER_ID = '$SeedDemoUserId'"
  )
  Write-Utf8NoBom -Path $clientPath -Text $clientText
  Write-Ok "frontend/src/api/client.ts saved as UTF-8 no BOM with DEMO_USER_ID=$SeedDemoUserId"

  Write-Step "Installing frontend dependencies"
  Push-Location (Join-Path $root "frontend")
  try {
    if (-not $SkipNpmInstall) {
      Invoke-Checked -FilePath "npm" -Arguments @("install") -ErrorMessage "npm install failed."
    } else {
      Write-Host "Skipping npm install because -SkipNpmInstall was provided."
    }

    if (Test-Path ".\node_modules\.vite") {
      Remove-Item -Recurse -Force ".\node_modules\.vite" -ErrorAction SilentlyContinue
    }

    if ($ForegroundFrontend) {
      Write-Step "Starting Vite frontend in the current PowerShell window"
      Write-Host "Frontend: http://localhost:5173"
      Write-Host "Backend docs: http://localhost:8000/docs"
      npm run dev
    } else {
      Write-Step "Starting Vite frontend in a new PowerShell window"
      $frontendDir = (Get-Location).Path
      $command = "cd `"$frontendDir`"; npm run dev"
      Start-Process powershell.exe -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $command
      )
      Start-Sleep -Seconds 3
    }
  } finally {
    Pop-Location
  }

  if (-not $NoBrowser) {
    Write-Step "Opening browser"
    Start-Process "http://localhost:5173"
    Start-Process "http://localhost:8000/docs"
  }

  Write-Step "Done"
  Write-Host "Frontend:     http://localhost:5173"
  Write-Host "Backend API:  http://localhost:8000"
  Write-Host "Backend docs: http://localhost:8000/docs"
  Write-Host ""
  Write-Host "Useful commands:"
  Write-Host "  docker compose ps"
  Write-Host "  docker compose logs -f backend"
  Write-Host "  docker compose down"
  Write-Host "  docker compose down -v   # delete DB volume"
} finally {
  Pop-Location
}
