param(
    [string]$Version = "",
    [string]$P4K = $env:SC_DATA_P4K,
    [string]$StarBreaker = "tools/starbreaker.exe",
    [string]$DataRoot = "/data/starcitizen",
    [switch]$ForceFull,
    [switch]$ForceBuild,
    [switch]$SkipTranslation,
    [switch]$SkipBlueprints,
    [switch]$SkipBuild,
    [switch]$BestEffort
)

$ErrorActionPreference = "Stop"

$workflowVersion = "sc-patch-update/v2"
$started = Get-Date
$reportPath = "informes/PATCH_UPDATE_REPORT.md"
$memoryPath = "informes/project_memory.local.md"
$statePath = Join-Path $DataRoot "state/last_patch.json"

New-Item -ItemType Directory -Force -Path "informes" | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DataRoot "state") | Out-Null

$warnings = New-Object System.Collections.Generic.List[string]
$errors = New-Object System.Collections.Generic.List[string]
$stepsRun = New-Object System.Collections.Generic.List[string]
$stepsSkipped = New-Object System.Collections.Generic.List[string]

$detectedVersion = ""
$patchChanged = $false
$globalIniChanged = $false
$game2Changed = $false
$runGlobalSync = $false
$runBlueprints = $false
$runBuild = $false
$addedKeys = -1
$buildStatus = "not-run"

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

function Add-WarningMessage {
    param([string]$Message)
    $warnings.Add($Message) | Out-Null
    Write-Host "WARNING: $Message"
}

function Add-ErrorMessage {
    param([string]$Message)
    $errors.Add($Message) | Out-Null
    Write-Host "ERROR: $Message"
}

function Add-StepRun {
    param([string]$Name)
    $stepsRun.Add($Name) | Out-Null
}

function Add-StepSkipped {
    param([string]$Name)
    $stepsSkipped.Add($Name) | Out-Null
}

function Get-JsonBool {
    param(
        [object]$Object,
        [string]$Name
    )

    if ($null -eq $Object) {
        return $false
    }

    if ($Object.PSObject.Properties.Name -contains $Name) {
        return [bool]$Object.$Name
    }

    return $false
}

function Write-PatchReport {
    param(
        [string]$Status,
        [string]$BuildStatus = "not-run"
    )

    $finished = Get-Date

    $lines = @()
    $lines += "# Patch Update Report"
    $lines += ""
    $lines += "- Timestamp start: ``$($started.ToString("s"))``"
    $lines += "- Timestamp end: ``$($finished.ToString("s"))``"
    $lines += "- Workflow version: ``$workflowVersion``"
    $lines += "- Status: ``$Status``"
    $lines += "- Requested version/build label: ``$Version``"
    $lines += "- Detected version: ``$detectedVersion``"
    $lines += "- StarBreaker: ``$StarBreaker``"
    $lines += "- Data.p4k: ``$P4K``"
    $lines += "- Data root: ``$DataRoot``"
    $lines += "- Patch changed: ``$patchChanged``"
    $lines += "- global.ini changed: ``$globalIniChanged``"
    $lines += "- Game2.dcb changed: ``$game2Changed``"
    $lines += "- Run global sync: ``$runGlobalSync``"
    $lines += "- Run blueprints: ``$runBlueprints``"
    $lines += "- Run build: ``$runBuild``"
    $lines += "- New localization keys: ``$addedKeys``"
    $lines += "- Build status: ``$BuildStatus``"
    $lines += ""
    $lines += "## Steps run"
    $lines += ""

    if ($stepsRun.Count -eq 0) {
        $lines += "No steps were run."
    } else {
        foreach ($step in $stepsRun) {
            $lines += "- $step"
        }
    }

    $lines += ""
    $lines += "## Steps skipped"
    $lines += ""

    if ($stepsSkipped.Count -eq 0) {
        $lines += "No steps were skipped."
    } else {
        foreach ($step in $stepsSkipped) {
            $lines += "- $step"
        }
    }

    $lines += ""
    $lines += "## Generated reports"
    $lines += ""
    $lines += "- Version sync: ``informes/version-sync-report.md``"
    $lines += "- Global sync: ``informes/global-ini-sync-report.md``"
    $lines += "- Blueprint extraction: ``informes/BLUEPRINTS_EXTRACTION_REPORT.md``"
    $lines += ""
    $lines += "## Warnings"
    $lines += ""

    if ($warnings.Count -eq 0) {
        $lines += "No warnings."
    } else {
        foreach ($warning in $warnings) {
            $lines += "- $warning"
        }
    }

    $lines += ""
    $lines += "## Errors"
    $lines += ""

    if ($errors.Count -eq 0) {
        $lines += "No errors."
    } else {
        foreach ($err in $errors) {
            $lines += "- $err"
        }
    }

    $lines += ""
    $lines += "## Recommended next actions"
    $lines += ""

    if ($Status -eq "success") {
        $lines += "1. Review generated reports under ``informes/``."
        if ($BuildStatus -eq "success") {
            $lines += "2. Review ``dist/$Version/reports/``."
        }
        $lines += "3. Commit source changes if the reports look correct."
    } elseif ($Status -eq "nothing-to-do") {
        $lines += "No relevant patch changes detected. Run with ``-ForceFull`` or ``-ForceBuild`` if you want to force work."
    } else {
        $lines += "1. Fix the errors listed above."
        $lines += "2. Re-run the workflow with the same version label."
    }

    Set-Content -Path $reportPath -Value ($lines -join "`n") -Encoding UTF8
}

function Update-ProjectMemory {
    param(
        [string]$Status,
        [string]$BuildStatus
    )

    $lines = @()
    $lines += "# Local Project Memory"
    $lines += ""
    $lines += "## Last Patch Workflow"
    $lines += ""
    $lines += "- Timestamp: ``$((Get-Date).ToString("s"))``"
    $lines += "- Workflow version: ``$workflowVersion``"
    $lines += "- Status: ``$Status``"
    $lines += "- Requested version/build label: ``$Version``"
    $lines += "- Detected version: ``$detectedVersion``"
    $lines += "- StarBreaker: ``$StarBreaker``"
    $lines += "- Data.p4k: ``$P4K``"
    $lines += "- Data root: ``$DataRoot``"
    $lines += "- Patch changed: ``$patchChanged``"
    $lines += "- global.ini changed: ``$globalIniChanged``"
    $lines += "- Game2.dcb changed: ``$game2Changed``"
    $lines += "- Global sync run: ``$runGlobalSync``"
    $lines += "- Blueprint extraction run: ``$runBlueprints``"
    $lines += "- New localization keys: ``$addedKeys``"
    $lines += "- Build status: ``$BuildStatus``"
    $lines += "- Patch report: ``$reportPath``"
    $lines += "- Version sync report: ``informes/version-sync-report.md``"
    $lines += "- Global sync report: ``informes/global-ini-sync-report.md``"
    $lines += "- Blueprint report: ``informes/BLUEPRINTS_EXTRACTION_REPORT.md``"
    $lines += ""
    $lines += "## Next Recommended Action"
    $lines += ""

    if ($Status -eq "success") {
        $lines += "Review reports and commit source changes if valid."
    } elseif ($Status -eq "nothing-to-do") {
        $lines += "No relevant change detected. Force build or full workflow only if needed."
    } else {
        $lines += "Resolve workflow errors and rerun patch update."
    }

    Set-Content -Path $memoryPath -Value ($lines -join "`n") -Encoding UTF8
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "== $Name =="

    try {
        & $Action
        Add-StepRun $Name
    }
    catch {
        Add-ErrorMessage "$Name failed: $_"

        if (-not $BestEffort) {
            Write-PatchReport -Status "failed" -BuildStatus $buildStatus
            Update-ProjectMemory -Status "failed" -BuildStatus $buildStatus
            throw
        }
    }
}

try {
    $StarBreaker = Resolve-StarBreakerPath -RequestedPath $StarBreaker
}
catch {
    Add-ErrorMessage "$_"
    Write-PatchReport -Status "failed" -BuildStatus "not-run"
    Update-ProjectMemory -Status "failed" -BuildStatus "not-run"
    throw
}

if (-not $P4K) {
    $P4K = "C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k"
}

if (-not (Test-Path $P4K)) {
    Add-ErrorMessage "Data.p4k not found: $P4K"
    Write-PatchReport -Status "failed" -BuildStatus "not-run"
    Update-ProjectMemory -Status "failed" -BuildStatus "not-run"
    throw "Data.p4k not found"
}

Invoke-Step "Version sync" {
    $versionScript = ".codex/skills/sc-version-sync/scripts/sync_version.py"

    if (-not (Test-Path $versionScript)) {
        throw "Missing version sync script: $versionScript"
    }

    python $versionScript --p4k $P4K --state $statePath --version-file "VERSION" --report "informes/version-sync-report.md"

    if ($LASTEXITCODE -ne 0) {
        throw "sync_version.py returned exit code $LASTEXITCODE"
    }

    if (Test-Path $statePath) {
        $state = Get-Content $statePath -Raw | ConvertFrom-Json
        $script:detectedVersion = $state.current_version
    }

    $versionReport = "informes/version-sync-report.md"
    if (Test-Path $versionReport) {
        $content = Get-Content $versionReport -Raw

        $script:patchChanged = $content -match "Patch changed:\s*``?True``?"
        $script:globalIniChanged = $content -match "global\.ini changed:\s*``?True``?"
        $script:game2Changed = $content -match "Game2\.dcb changed:\s*``?True``?"
    }

    if (-not $Version -and $detectedVersion) {
        $script:Version = $detectedVersion
    }

    if (-not $Version) {
        $script:Version = "patch-update-local"
    }
}

if ($ForceFull) {
    $patchChanged = $true
    $globalIniChanged = $true
    $game2Changed = $true
    Add-WarningMessage "ForceFull enabled: all expensive workflow steps will run."
}

$runGlobalSync = $patchChanged -or $globalIniChanged
$runBlueprints = ($patchChanged -or $game2Changed) -and (-not $SkipBlueprints)
$runBuild = $ForceBuild -or $patchChanged -or $globalIniChanged -or $game2Changed

if ($SkipBuild) {
    $runBuild = $false
}

if ($runGlobalSync) {
    Invoke-Step "Global INI sync" {
        $syncScript = ".codex/skills/sc-global-ini-sync/scripts/sync_missing_keys.py"
        $extractScript = ".codex/skills/sc-global-ini-sync/scripts/extract_global.ps1"

        if (-not (Test-Path $syncScript)) {
            throw "Missing sync script: $syncScript"
        }

        if (Test-Path $extractScript) {
            & $extractScript -StarBreaker $StarBreaker -P4K $P4K -DataRoot $DataRoot

            if ($LASTEXITCODE -ne 0) {
                throw "extract_global.ps1 returned exit code $LASTEXITCODE"
            }
        } else {
            Add-WarningMessage "No extract_global.ps1 found in sc-global-ini-sync; assuming input/current/global.ini is refreshed by the skill or manually."
        }

        python $syncScript --block-label $Version

        if ($LASTEXITCODE -ne 0) {
            throw "sync_missing_keys.py returned exit code $LASTEXITCODE"
        }

        $globalReport = "informes/global-ini-sync-report.md"
        if (Test-Path $globalReport) {
            $content = Get-Content $globalReport -Raw
            $match = [regex]::Match($content, "Missing keys added:\s*`?([0-9]+)`?")
            if ($match.Success) {
                $script:addedKeys = [int]$match.Groups[1].Value
            }
        }
    }
} else {
    Add-StepSkipped "Global INI sync"
}

if (-not $SkipTranslation) {
    if ($addedKeys -gt 0) {
        Invoke-Step "Translate newly added keys" {
            Add-WarningMessage "Automatic narrow translation is not implemented in this orchestrator yet. Use translate-loc on the appended block or generated batch."
        }
    } else {
        Add-StepSkipped "Translate newly added keys"
    }
} else {
    Add-StepSkipped "Translate newly added keys"
    Add-WarningMessage "Translation step skipped by flag."
}

if ($runBlueprints) {
    Invoke-Step "Blueprint extraction" {
        $blueprintScript = ".codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.ps1"

        if (-not (Test-Path $blueprintScript)) {
            throw "Missing blueprint extractor script: $blueprintScript"
        }

        & $blueprintScript -StarBreaker $StarBreaker -P4K $P4K -DataRoot $DataRoot

        if ($LASTEXITCODE -ne 0) {
            throw "extract_blueprints.ps1 returned exit code $LASTEXITCODE"
        }
    }
} else {
    Add-StepSkipped "Blueprint extraction"
}

if ($runBuild) {
    Invoke-Step "Build distributions" {
        $buildScript = "scripts/build_distributions.py"

        if (-not (Test-Path $buildScript)) {
            throw "Missing build script: $buildScript"
        }

        $venvPython = "venv\Scripts\python.exe"

        if (Test-Path $venvPython) {
            & $venvPython $buildScript --version $Version
        } else {
            Add-WarningMessage "venv Python not found; falling back to python from PATH."
            python $buildScript --version $Version
        }

        if ($LASTEXITCODE -ne 0) {
            $script:buildStatus = "failed"
            throw "build_distributions.py returned exit code $LASTEXITCODE"
        }

        $script:buildStatus = "success"
    }
} else {
    $buildStatus = "skipped"
    Add-StepSkipped "Build distributions"
}

$status = if ($errors.Count -gt 0) {
    "completed-with-errors"
} elseif (-not $runGlobalSync -and -not $runBlueprints -and -not $runBuild) {
    "nothing-to-do"
} else {
    "success"
}

Write-PatchReport -Status $status -BuildStatus $buildStatus
Update-ProjectMemory -Status $status -BuildStatus $buildStatus

Write-Host ""
Write-Host "OK"
Write-Host "Status: $status"
Write-Host "Patch report: $reportPath"
Write-Host "Project memory: $memoryPath"
