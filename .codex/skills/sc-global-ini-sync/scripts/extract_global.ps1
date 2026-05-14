param(
    [string]$StarBreaker = "tools/starbreaker.exe",
    [string]$P4K = $env:SC_DATA_P4K,
    [string]$DataRoot = "/data/starcitizen",
    [string]$Output = "input/current/global.ini"
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

$globalRoot = Join-Path $DataRoot "extracts/current/global"
$rawRoot = Join-Path $globalRoot "raw"
$outputPath = (Resolve-Path -LiteralPath ".").Path
$normalizedOutput = Join-Path $outputPath $Output

New-Item -ItemType Directory -Force -Path $rawRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $normalizedOutput) | Out-Null

Write-Host "== StarBreaker =="
Write-Host $resolvedStarBreaker

Write-Host "== Data.p4k =="
Write-Host $P4K

Write-Host "== Extracting global.ini =="

& $resolvedStarBreaker p4k extract `
    --p4k $P4K `
    --filter "**/Localization/english/global.ini" `
    --output $rawRoot

if ($LASTEXITCODE -ne 0) {
    throw "StarBreaker p4k extraction failed with exit code $LASTEXITCODE"
}

$extracted = Get-ChildItem $rawRoot -Recurse -Filter "global.ini" | Where-Object {
    $_.FullName -match '[\\/]Localization[\\/]english[\\/]global\.ini$'
} | Select-Object -First 1

if (-not $extracted) {
    throw "global.ini was not found after extraction"
}

Copy-Item -LiteralPath $extracted.FullName -Destination $normalizedOutput -Force

Write-Host "Normalized global.ini:"
Write-Host $normalizedOutput
