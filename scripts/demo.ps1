param(
    [string]$Db = "artifacts/study/hn.db",
    [int]$Port = 8000,
    [switch]$Check,
    [switch]$Build
)
$ErrorActionPreference = "Stop"
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $demoPython = Join-Path (Get-Location) "venv/Scripts/python.exe"
    if (-not (Test-Path -LiteralPath $demoPython)) { $demoPython = "python" }
    if ($Build) {
        Push-Location frontend
        try {
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
        } finally { Pop-Location }
    }
    $demoArgs = @("-m", "scripts.demo", "--db", $Db, "--port", "$Port")
    if ($Check) { $demoArgs += "--check" }
    & $demoPython @demoArgs
    if ($LASTEXITCODE -ne 0) { throw "Local demo exited with code $LASTEXITCODE" }
} finally { Pop-Location }
