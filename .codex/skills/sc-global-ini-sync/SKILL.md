---
name: sc-global-ini-sync
description: Extract and sync the latest Star Citizen global.ini against the Spanish translation memory, adding only missing keys and delegating translation to translate-loc.
---

# Purpose

Use this skill after a new Star Citizen patch to update the English source localization and synchronize missing keys into the Spanish translation memory.

# StarBreaker location

The repository-local StarBreaker executable is:

`tools/starbreaker.exe`

Always prefer this executable over any globally installed `starbreaker`.

Use repository-relative paths whenever possible.

# Critical extraction rule

This skill must always refresh `input/current/global.ini` from the current Star Citizen patch before comparing keys.

Do not trust an existing `input/current/global.ini` unless the user explicitly asks to skip extraction.

Extraction must use StarBreaker against the current `Data.p4k`.

# Data policy

`input/current/global.ini` is a versioned repository file and must be refreshed from the current patch.

Keep the final normalized English localization source here:

`input/current/global.ini`

Large or temporary extraction artifacts must stay outside the repository under:

`/data/starcitizen/`

This includes:

- temporary StarBreaker extraction folders
- raw extracted P4K contents
- `Game2.dcb`
- exported DCB JSON/XML
- blueprint discovery dumps
- cache files
- patch comparison workspaces

Do not commit or generate heavy extraction artifacts inside the repository.

# Extraction output rules

StarBreaker may extract temporary files to:

`/data/starcitizen/extracts/current/global/`

After extraction, copy or normalize the final `global.ini` into:

`input/current/global.ini`

Only `input/current/global.ini` should remain in the repository as the canonical current English source.

# Inputs

- `tools/starbreaker.exe`
- Star Citizen `Data.p4k`
- `input/current/global.ini`
- `source/languages/es-es/translation.ini`
- `.codex/skills/translate-loc/`

# Outputs

- Updated `input/current/global.ini`
- Updated `source/languages/es-es/translation.ini`
- `informes/global-ini-sync-report.md`

# Main workflow

1. Locate `tools/starbreaker.exe`.
   If the repository stores the binary under `tools/starbreaker/starbreaker.exe`, resolve that path automatically.
2. Locate Star Citizen `Data.p4k`.
3. Extract the latest `global.ini` using StarBreaker.
   Preferred helper script:

` .codex/skills/sc-global-ini-sync/scripts/extract_global.ps1 `
4. Normalize the extracted file to:

`input/current/global.ini`

5. Compare keys from:

`input/current/global.ini`

against:

`source/languages/es-es/translation.ini`

6. Do not compare only by key count. Key count is diagnostic only.

7. Missing keys are:

```text
keys(input/current/global.ini) - keys(source/languages/es-es/translation.ini)
```

8. Append only missing keys to the end of `translation.ini`.

9. Preserve existing translations exactly.

10. Do not reorder, delete, or overwrite existing keys.

11. Newly added keys must initially keep the English value.

12. Mark the appended block with a generated comment.

13. If new keys were added, invoke `translate-loc` only on the newly added entries or on a generated batch containing those entries.

14. Run validation after translation.

15. Generate:

```text
informes/global-ini-sync-report.md
```

# Comparison rules

- Ignore empty lines.
- Ignore comment lines starting with `#` or `;`.
- Treat everything before the first `=` as the key.
- Treat everything after the first `=` as the value.
- Preserve key casing.
- Compare keys exactly.
- If duplicate keys exist:
  - first occurrence is canonical
  - report duplicates
  - do not add another duplicate

# Translation delegation

Use `translate-loc` for translation.

Do not implement translation logic in this skill.

If `translate-loc` fails:
- keep the new keys with English values
- report the failure
- do not rollback the key sync

# Safety rules

Never:
- modify `Data.p4k`
- write into the Star Citizen installation folder
- overwrite existing Spanish values
- delete keys from `translation.ini`
- reorder existing entries
- modify generated files in `dist/`

# Report contents

The report must include:

- source file path
- translation file path
- total keys in `global.ini`
- total keys in `translation.ini` before sync
- total keys in `translation.ini` after sync
- number of missing keys added
- list of added keys
- duplicate source keys
- duplicate translation keys
- whether translation was attempted
- whether validation passed
