$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host ""
Write-Host "============================================================"
Write-Host " NBA DECISIONING LAB - REGRESSION VALIDATION"
Write-Host "============================================================"
Write-Host ""

Write-Host "Project root : $projectRoot"

$pythonCommand = Get-Command python -ErrorAction Stop
$pythonExe = $pythonCommand.Source

Write-Host "Python       : $pythonExe"

$pythonVersion = python --version
Write-Host "Version      : $pythonVersion"

if (-not (Test-Path ".\pyproject.toml")) {
    Write-Host ""
    Write-Host "VALIDATION: FAIL"
    Write-Host "pyproject.toml was not found."
    exit 2
}

$reportDirectory = ".\reports\ci"
$junitReport = Join-Path $reportDirectory "pytest-junit.xml"

New-Item `
    -ItemType Directory `
    -Path $reportDirectory `
    -Force | Out-Null

Write-Host ""
Write-Host "Running full regression suite..."
Write-Host "JUnit report : $junitReport"
Write-Host ""

python -m pytest `
    -q `
    --junitxml="$junitReport"

$pytestExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "============================================================"

if ($pytestExitCode -eq 0) {
    Write-Host " REGRESSION RESULT: PASS"
}
else {
    Write-Host " REGRESSION RESULT: FAIL"
}

Write-Host " Pytest exit code : $pytestExitCode"
Write-Host " JUnit report     : $junitReport"
Write-Host "============================================================"
Write-Host ""

exit $pytestExitCode