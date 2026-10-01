$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host ""
Write-Host "============================================================"
Write-Host " NBA DECISIONING LAB - RELEASE VALIDATION"
Write-Host "============================================================"
Write-Host ""

$pythonCommand = Get-Command python -ErrorAction Stop
$pythonExe = $pythonCommand.Source

Write-Host "Project root : $projectRoot"
Write-Host "Python       : $pythonExe"
Write-Host "Version      : $(python --version)"

$reportDirectory = ".\reports\release"
$smokeReport = Join-Path $reportDirectory "release-smoke-junit.xml"
$regressionReport = Join-Path $reportDirectory "release-regression-junit.xml"
$summaryUpdater = ".\scripts\update_validation_summary.py"

New-Item `
    -ItemType Directory `
    -Path $reportDirectory `
    -Force | Out-Null

Write-Host ""
Write-Host "------------------------------------------------------------"
Write-Host " STAGE 1 - RELEASE READINESS SMOKE VALIDATION"
Write-Host "------------------------------------------------------------"
Write-Host ""

python -m pytest `
    .\tests\test_release_readiness.py `
    -q `
    --junitxml="$smokeReport"

$smokeExitCode = $LASTEXITCODE

if ($smokeExitCode -ne 0) {
    Write-Host ""
    Write-Host "============================================================"
    Write-Host " RELEASE RESULT: BLOCKED"
    Write-Host " Failed stage : Release readiness smoke validation"
    Write-Host " Exit code    : $smokeExitCode"
    Write-Host "============================================================"
    Write-Host ""

    exit $smokeExitCode
}

Write-Host ""
Write-Host "------------------------------------------------------------"
Write-Host " STAGE 2 - COMPLETE REGRESSION VALIDATION"
Write-Host "------------------------------------------------------------"
Write-Host ""

python -m pytest `
    -q `
    --junitxml="$regressionReport"

$regressionExitCode = $LASTEXITCODE

if ($regressionExitCode -eq 0) {
    Write-Host ""
    Write-Host "------------------------------------------------------------"
    Write-Host " UPDATE README VALIDATION SUMMARY"
    Write-Host "------------------------------------------------------------"
    Write-Host ""

    python $summaryUpdater `
        --smoke-report "$smokeReport" `
        --regression-report "$regressionReport" `
        --readme ".\README.md"

    $summaryExitCode = $LASTEXITCODE

    if ($summaryExitCode -ne 0) {
        Write-Host ""
        Write-Host "============================================================"
        Write-Host " RELEASE RESULT: BLOCKED"
        Write-Host " Failed stage : README validation summary update"
        Write-Host " Exit code    : $summaryExitCode"
        Write-Host "============================================================"
        Write-Host ""

        exit $summaryExitCode
    }
}

Write-Host ""
Write-Host "============================================================"

if ($regressionExitCode -eq 0) {
    Write-Host " RELEASE RESULT: PASS"
}
else {
    Write-Host " RELEASE RESULT: BLOCKED"
}

Write-Host " Smoke exit code      : $smokeExitCode"
Write-Host " Regression exit code : $regressionExitCode"
Write-Host " Smoke report         : $smokeReport"
Write-Host " Regression report    : $regressionReport"
Write-Host "============================================================"
Write-Host ""

exit $regressionExitCode
