param(
    [string]$StarBreaker = "tools/starbreaker.exe",
    [string]$P4K = $env:SC_DATA_P4K,
    [string]$DataRoot = "/data/starcitizen",
    [switch]$SkipDcbExport,
    [Alias("?")]
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help -or $args -contains "--help" -or $args -contains "-h") {
    Write-Host "Usage: extract_blueprints.ps1 [-StarBreaker <path>] [-P4K <path>] [-DataRoot <path>] [-SkipDcbExport] [-Help]"
    Write-Host ""
    Write-Host "Runs the Python core workflow:"
    Write-Host "  .codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.py"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.ps1"
    Write-Host "  .codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.ps1 -P4K C:\Path\To\Data.p4k"
    exit 0
}

$arguments = @(
    ".codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.py",
    "--starbreaker", $StarBreaker,
    "--data-root", $DataRoot
)

if ($P4K) {
    $arguments += @("--p4k", $P4K)
}

if ($SkipDcbExport) {
    $arguments += "--skip-dcb-export"
}

& python @arguments

if ($LASTEXITCODE -ne 0) {
    throw "Blueprint extraction workflow failed with exit code $LASTEXITCODE"
}
