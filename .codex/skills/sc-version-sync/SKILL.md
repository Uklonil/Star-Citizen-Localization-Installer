---
name: sc-version-sync
description: Detect Star Citizen patch/version changes from Data.p4k and synchronize VERSION plus local workflow state.
---

# Purpose

Use this skill before running expensive patch workflows.

This skill determines whether the current Star Citizen patch changed compared to the last processed state.

It synchronizes:

- `VERSION`
- local workflow state
- patch metadata
- workflow routing decisions

# Repository-local tools

Use repository-relative paths whenever possible.

Known local tools:

- `tools/starbreaker.exe`

Do not assume globally installed tools exist in PATH.

# Inputs

- `tools/starbreaker.exe`
- Star Citizen `Data.p4k`
- `VERSION`
- `/data/starcitizen/state/last_patch.json`

# Outputs

- updated `VERSION`
- updated `/data/starcitizen/state/last_patch.json`
- `informes/version-sync-report.md`

# Runtime state

Persistent workflow state must live outside the repository under:

`/data/starcitizen/state/`

Recommended state file:

`/data/starcitizen/state/last_patch.json`

# Detection strategy

The skill should determine whether the patch changed using multiple signals.

Do not rely only on the VERSION file.

Primary signals:

- detected patch/build label
- Data.p4k size
- Data.p4k modified timestamp
- global.ini hash
- Game2.dcb hash if available

# Workflow routing

## If patch changed

Recommended actions:

- run `sc-global-ini-sync`
- run `translate-loc` if new keys exist
- run `sc-blueprint-extractor`
- run distribution build

## If patch did not change

Recommended actions:

- skip expensive extraction
- optionally run validation/build only

# Critical rules

- Never modify `Data.p4k`
- Never write into the Star Citizen installation folder
- Never delete previous state automatically
- Never trust VERSION alone
- Always write state updates atomically

# Main workflow

1. Locate `tools/starbreaker.exe`
2. Locate Star Citizen `Data.p4k`
3. Read previous state from:
   `/data/starcitizen/state/last_patch.json`
4. Collect current patch metadata
5. Compute hashes if possible
6. Compare current state vs previous state
7. Determine:
   - patch_changed
   - global_ini_changed
   - game2_changed
8. Update:
   - `VERSION`
   - `last_patch.json`
9. Generate:
   `informes/version-sync-report.md`

# Report contents

The report must include:

- timestamp
- VERSION before
- VERSION after
- Data.p4k path
- Data.p4k size
- Data.p4k modified time
- global.ini hash
- Game2.dcb hash
- patch changed flag
- global.ini changed flag
- Game2.dcb changed flag
- recommended workflow
