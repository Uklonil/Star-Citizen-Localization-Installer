---
name: sc-patch-update
description: Orchestrate the full Star Citizen localization patch update workflow using sc-version-sync routing, global.ini sync, new-key translation, blueprint extraction, build validation and reporting.
---

# Purpose

Use this skill after a new Star Citizen patch to run the complete repository update pipeline.

This is an orchestration skill.

It should call existing atomic skills and project scripts instead of duplicating their logic.

# Workflow version

Current workflow version:

`sc-patch-update/v2`

## v2 changes

- runs `sc-version-sync` first
- reads `/data/starcitizen/state/last_patch.json`
- reads `informes/version-sync-report.md`
- routes the workflow based on detected changes
- avoids expensive extraction steps when no relevant changes are detected

# Pipeline

Default workflow:

1. `sc-version-sync`
2. `sc-global-ini-sync`, only if needed
3. `translate-loc` for newly added localization keys, only if needed
4. `sc-blueprint-extractor`, only if needed
5. distribution build validation, only if needed or requested
6. final patch report
7. local project memory update

# Repository-local tools

Use repository-relative paths whenever possible.

Known local tools:

- `tools/starbreaker.exe`
- `.codex/skills/sc-version-sync/`
- `.codex/skills/sc-global-ini-sync/`
- `.codex/skills/translate-loc/`
- `.codex/skills/sc-blueprint-extractor/`

Do not assume globally installed tools exist in PATH.

# Data policy

The canonical extracted English localization source remains versioned in the repo:

`input/current/global.ini`

Heavy or temporary extraction artifacts must remain outside the repo:

`/data/starcitizen/`

This includes:

- raw StarBreaker extraction folders
- `Game2.dcb`
- DCB exports
- blueprint discovery caches
- large machine-readable reports
- patch comparison workspaces
- workflow state files

Small human-readable reports may be stored under:

`informes/`

# Inputs

- Star Citizen `Data.p4k`
- `tools/starbreaker.exe`
- `.codex/skills/sc-version-sync/`
- `.codex/skills/sc-global-ini-sync/`
- `.codex/skills/translate-loc/`
- `.codex/skills/sc-blueprint-extractor/`
- `scripts/build_distributions.py`
- `source/languages/es-es/translation.ini`
- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`

# Outputs

- updated `VERSION`
- updated `/data/starcitizen/state/last_patch.json`
- refreshed `input/current/global.ini`
- updated `source/languages/es-es/translation.ini`
- blueprint extraction reports
- distribution build outputs under `dist/<version>/`
- `informes/PATCH_UPDATE_REPORT.md`
- updated `informes/project_memory.local.md`

# Routing logic

The workflow starts by running `sc-version-sync`.

Then it decides:

## If patch changed

Run:

1. `sc-global-ini-sync`
2. `translate-loc` if new localization keys exist
3. `sc-blueprint-extractor`
4. build distributions

## If patch did not change but global.ini changed

Run:

1. localization validation/build
2. optionally translation review

## If patch did not change but Game2.dcb changed

Run:

1. `sc-blueprint-extractor`
2. build distributions

## If no relevant changes are detected

Skip expensive extraction steps.

Run build only if explicitly requested.

# Main workflow

## Step 1 - Version sync

Run:

```powershell
python .codex/skills/sc-version-sync/scripts/sync_version.py --p4k <Data.p4k>
```

Expected results:

- `VERSION` updated
- `/data/starcitizen/state/last_patch.json` updated
- `informes/version-sync-report.md` generated

## Step 2 - Global localization sync

Run `sc-global-ini-sync` if routing says localization sync is needed.

Expected results:

- StarBreaker extracts the latest `global.ini`
- `input/current/global.ini` is refreshed
- missing keys are appended to `source/languages/es-es/translation.ini`
- `informes/global-ini-sync-report.md` is generated

## Step 3 - Translate newly added keys

Run `translate-loc` only if new keys were added.

Scope:

- translate only newly added entries
- do not retranslate the full file unless explicitly requested
- preserve all keys, placeholders, escapes, markup and ordering

If translation fails:

- do not rollback synced keys
- keep English fallback values
- report the failure in `informes/PATCH_UPDATE_REPORT.md`

## Step 4 - Blueprint extraction

Run `sc-blueprint-extractor` if routing says blueprint extraction is needed.

Expected results:

- `Game2.dcb` extracted from current `Data.p4k`
- heavy artifacts stored under `/data/starcitizen/`
- review reports generated under `informes/`

This step is discovery/reporting only.

Do not automatically edit:

- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`

unless explicitly instructed.

## Step 5 - Build validation

Run the distribution build if:

- patch changed
- localization changed
- blueprint extraction ran
- user explicitly requested build

Default command pattern:

```powershell
venv\Scripts\python.exe scripts\build_distributions.py --version <version>
```

Fallback command:

```powershell
python scripts\build_distributions.py --version <version>
```

The build step must fail the workflow if:

- the command returns a non-zero exit code
- malformed INI files are detected
- placeholder/markup validation fails
- required language resources are missing
- unresolved overlay references break the build

## Step 6 - Final report

Generate:

`informes/PATCH_UPDATE_REPORT.md`

The report must include:

- timestamp
- workflow version
- requested patch/build label
- detected VERSION
- Data.p4k path
- StarBreaker path
- version-sync result
- routing decision
- global.ini sync result
- number of new localization keys
- whether translation was attempted
- blueprint extraction result
- distribution build result
- generated paths
- warnings
- errors
- recommended next actions

## Step 7 - Project memory

Update:

`informes/project_memory.local.md`

with:

- last patch workflow timestamp
- patch/build label
- detected VERSION
- Data.p4k path used
- route decisions
- global sync result
- new localization key count
- blueprint extraction summary
- build status
- generated report paths
- known blockers
- next recommended action

# Safety rules

Never:

- modify `Data.p4k`
- write into the Star Citizen installation folder
- delete keys from `translation.ini`
- overwrite existing Spanish translations
- reorder existing translation memory
- place large extraction artifacts in the repo
- auto-apply blueprint pool candidates without explicit instruction

# Failure behavior

If one step fails:

1. stop the workflow unless the user explicitly requested best-effort mode
2. keep generated reports produced so far
3. write the failure into `informes/PATCH_UPDATE_REPORT.md`
4. provide the next actionable fix

# Best-effort mode

If explicitly requested, continue after non-critical failures.

Critical failures that should still stop the workflow:

- missing `tools/starbreaker.exe`
- missing `Data.p4k`
- missing `sc-version-sync`
- failed `global.ini` extraction when localization sync is required
- missing `source/languages/es-es/translation.ini`
- failed distribution build
