param(
    [string]$StarBreaker = "tools/starbreaker.exe",
    [string]$P4K = $env:SC_DATA_P4K,
    [string]$DataRoot = "/data/starcitizen",
    [switch]$SkipDcbExport
)

$ErrorActionPreference = "Stop"

function Resolve-StarBreakerPath {
    param([string]$RequestedPath)

    $candidates = @(
        $RequestedPath,
        "tools/starbreaker/starbreaker.exe"
    ) | Where-Object { $_ } | Select-Object -Unique

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $item = Get-Item $candidate

            if ($item.PSIsContainer) {
                $nestedExe = Join-Path $item.FullName "starbreaker.exe"
                if (Test-Path $nestedExe) {
                    return $nestedExe
                }
            } else {
                return $item.FullName
            }
        }
    }

    throw "StarBreaker not found. Checked: $($candidates -join ', ')"
}

$resolvedStarBreaker = Resolve-StarBreakerPath -RequestedPath $StarBreaker

if (-not $P4K) {
    $P4K = "C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k"
}

if (-not (Test-Path $P4K)) {
    throw "Data.p4k not found: $P4K"
}

$game2Root = Join-Path $DataRoot "extracts/current/game2"
$rawRoot = Join-Path $game2Root "raw"
$exportRoot = Join-Path $game2Root "exported"
$reportsRoot = Join-Path $DataRoot "reports/blueprints"

New-Item -ItemType Directory -Force -Path $rawRoot | Out-Null
New-Item -ItemType Directory -Force -Path $exportRoot | Out-Null
New-Item -ItemType Directory -Force -Path $reportsRoot | Out-Null
New-Item -ItemType Directory -Force -Path "informes" | Out-Null

Write-Host "== StarBreaker =="
Write-Host $resolvedStarBreaker

Write-Host "== Data.p4k =="
Write-Host $P4K

Write-Host "== Extracting Game2.dcb =="

# StarBreaker CLI variants may differ between versions.
# If this command fails, adjust the command here and record the working command in informes/project_memory.local.md.
& $resolvedStarBreaker p4k extract `
    --p4k $P4K `
    --filter "**/Game2.dcb" `
    --output $rawRoot

if ($LASTEXITCODE -ne 0) {
    throw "StarBreaker p4k extraction failed with exit code $LASTEXITCODE"
}

$game2 = Get-ChildItem $rawRoot -Recurse -Filter "Game2.dcb" | Select-Object -First 1

if (-not $game2) {
    throw "Game2.dcb was not found after extraction"
}

$normalizedGame2 = Join-Path $game2Root "Game2.dcb"
Copy-Item $game2.FullName $normalizedGame2 -Force

Write-Host "Normalized Game2.dcb:"
Write-Host $normalizedGame2

if (-not $SkipDcbExport) {
    Write-Host "== Attempting DCB export =="

    try {
        & $resolvedStarBreaker dcb extract `
            --dcb $normalizedGame2 `
            --format json `
            --output $exportRoot

        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: DCB export failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Host "WARNING: DCB export failed: $_"
    }
}

Write-Host "== Scanning Game2.dcb text windows =="

python ".codex/skills/sc-blueprint-extractor/scripts/core/scan_game2_text.py" `
    --game2 $normalizedGame2 `
    --global-ini "input/current/global.ini" `
    --template "source/blueprints/blueprints_template.ini" `
    --pools "source/blueprints/pools.json" `
    --data-report "$reportsRoot/game2-text-scan.json" `
    --md-report "informes/BLUEPRINTS_EXTRACTION_REPORT.md" `
    --starbreaker $resolvedStarBreaker `
    --p4k $P4K

Write-Host "OK"
