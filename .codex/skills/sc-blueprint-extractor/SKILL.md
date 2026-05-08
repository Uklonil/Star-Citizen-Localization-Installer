---
name: sc-blueprint-extractor
description: Extract Star Citizen blueprint and mission reward data from Data.p4k/Game2.dcb using StarBreaker, then generate candidate reports for blueprint pool maintenance.
---

# Purpose

Use this skill after a new Star Citizen patch to inspect game data related to blueprints, mission rewards, crafting pools, mission descriptions and contract links.

This skill is focused on discovery and reporting.

It must not directly rewrite `source/blueprints/blueprints_template.ini` or `source/blueprints/pools.json` unless explicitly instructed.

# StarBreaker location

The repository-local StarBreaker executable is:

`tools/starbreaker.exe`

Always prefer this executable over any globally installed `starbreaker`.

Do not assume `starbreaker` exists in PATH.

# Data policy

Large and temporary extraction artifacts must stay outside the repository under:

`/data/starcitizen/`

This includes:

- temporary StarBreaker extraction folders
- raw extracted P4K contents
- `Game2.dcb`
- exported DCB JSON/XML
- blueprint discovery dumps
- cache files
- patch comparison workspaces

Small human-readable reports may be copied into:

`informes/`

Do not generate large extracted files inside the repository.

# Inputs

- `tools/starbreaker.exe`
- Star Citizen `Data.p4k`
- `input/current/global.ini`
- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`
- Script layout:
  - Core:
    - `.codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.ps1`
    - `.codex/skills/sc-blueprint-extractor/scripts/core/scan_game2_text.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/core/runtime_support.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/core/blueprint_pool_source.py`
  - Review:
    - `.codex/skills/sc-blueprint-extractor/scripts/review/discover_new_blueprint_mission_candidates.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/review/build_blueprint_shortlist.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/review/extract_mission_contract_links.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/review/infer_blueprint_pools_from_contracts.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/review/discover_blueprint_reward_pools.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/review/build_blueprint_pool_draft.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/review/extract_blueprint_mission_rewards.py`
  - Maintenance:
    - `.codex/skills/sc-blueprint-extractor/scripts/maintenance/normalize_blueprints_overlay.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/maintenance/generate_blueprints_overlay.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/maintenance/bootstrap_blueprint_pools.py`
    - `.codex/skills/sc-blueprint-extractor/scripts/maintenance/split_blueprint_pool_source.py`

# Outputs

Primary runtime outputs:

- `/data/starcitizen/extracts/current/game2/Game2.dcb`
- `/data/starcitizen/extracts/current/game2/exported/`
- `/data/starcitizen/reports/blueprints/`

Repository reports:

- `informes/BLUEPRINTS_EXTRACTION_REPORT.md`
- `informes/BLUEPRINTS_NEW_MISSION_CANDIDATES.md`
- `informes/MISSION_CONTRACT_LINKS_FROM_GAME2.md`
- `informes/MISSION_CONTRACT_LINKS_SUMMARY.md`
- `informes/BLUEPRINTS_CONTRACT_TO_POOL_INFERENCE.md`

# Critical rules

- Never modify `Data.p4k`.
- Never write into the Star Citizen installation folder.
- Never place large extraction artifacts inside the repository.
- Never assume DCB structured parsing is reliable.
- Prefer text-window discovery from `Game2.dcb` if structured record parsing fails.
- Do not automatically apply candidate pools to `blueprints_template.ini`.
- Do not automatically modify `pools.json`.
- Treat inferred pools as candidates unless evidence is strict and explicitly reviewed.
- Keep `source/shared/overlays/blueprints.ini` as a generated artifact, not the source of truth.

# Source of truth

The project source of truth for blueprint overlays is:

- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`

The generated shared overlay is:

- `source/shared/overlays/blueprints.ini`

This generated overlay is for inspection/build compatibility and should not be treated as the canonical editable source.

# Main workflow

## Step 1 - Locate tools and paths

Verify:

- `tools/starbreaker.exe` exists
- Star Citizen `Data.p4k` exists
- `input/current/global.ini` exists
- `source/blueprints/blueprints_template.ini` exists
- `source/blueprints/pools.json` exists

Preferred `Data.p4k` resolution order:

1. explicit CLI argument or user-provided path
2. `SC_DATA_P4K` environment variable
3. common LIVE path:
   `C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k`

## Step 2 - Extract Game2.dcb

Extract `Game2.dcb` from the current patch using StarBreaker.

Temporary extraction root:

`/data/starcitizen/extracts/current/game2/raw/`

Final normalized DCB path:

`/data/starcitizen/extracts/current/game2/Game2.dcb`

Do not copy `Game2.dcb` into the repository.

## Step 3 - Export or inspect DCB

Attempt StarBreaker DCB export to:

`/data/starcitizen/extracts/current/game2/exported/`

If structured export is incomplete, corrupt, or unreliable, fall back to binary/text-window scanning of `Game2.dcb`.

Known useful discovery targets:

- localization keys ending in `_title`
- localization keys ending in `_desc`
- `ContractGenerator.*`
- `contractgenerator/*.xml`
- `missiondata/*.xml`
- `BP_MISSIONREWARD_*`
- `item_*`
- reward pool references

## Step 4 - Candidate discovery

Use `input/current/global.ini` as the localization surface.

Find mission descriptions and titles that may expose blueprint rewards.

Compare against:

- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`

Generate candidate reports for:

- mission keys present in `global.ini` but absent from blueprint template
- descriptions likely containing blueprint rewards
- contract links found near mission title/desc keys
- missiondata links found near mission title/desc keys
- possible pool inference by contract and missiondata
- unknown or ambiguous pools

## Step 5 - Pool inference

If helper scripts exist, prefer them over reinventing logic:

1. `.codex/skills/sc-blueprint-extractor/scripts/review/discover_new_blueprint_mission_candidates.py`
2. `.codex/skills/sc-blueprint-extractor/scripts/review/extract_mission_contract_links.py`
3. `.codex/skills/sc-blueprint-extractor/scripts/review/infer_blueprint_pools_from_contracts.py`

Inference confidence levels:

- `strict`: exact contractgenerator + exact missiondata + known template mapping
- `contract-only`: exact contractgenerator match but no missiondata confirmation
- `family-rule`: explicit known family resolver
- `heuristic`: text or faction similarity only
- `unknown`: no useful evidence

Only `strict` candidates should be proposed as ready for review.

Never auto-apply `contract-only`, `family-rule`, `heuristic`, or `unknown` candidates without explicit instruction.

## Step 6 - Reports

Generate a primary report:

`informes/BLUEPRINTS_EXTRACTION_REPORT.md`

The report must include:

- timestamp
- Data.p4k path used
- StarBreaker path used
- extracted Game2.dcb path
- whether DCB export succeeded
- whether fallback text scanning was used
- total candidate mission keys
- total contract links found
- total missiondata links found
- total inferred strict candidates
- total ambiguous candidates
- total unknown candidates
- generated report paths
- recommended next actions

# Report naming

Large machine-readable reports should go under:

`/data/starcitizen/reports/blueprints/`

Small review reports should go under:

`informes/`

# Patch comparison

If previous extraction data exists under:

`/data/starcitizen/extracts/previous/`

the skill may compare current vs previous and report:

- new mission keys
- removed mission keys
- changed descriptions
- new contractgenerator paths
- new missiondata paths
- new pool IDs

Do not delete previous extraction data unless explicitly requested.

# Project memory

After a successful run, update:

`informes/project_memory.local.md`

with:

- last blueprint extraction timestamp
- Data.p4k path used
- Game2.dcb extracted path
- candidate counts
- strict inference count
- ambiguous/unknown count
- generated reports
- next recommended action
