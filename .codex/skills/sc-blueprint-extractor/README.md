# sc-blueprint-extractor

Main command:

```powershell
python .codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.py
```

Optional:

```powershell
python .codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.py --p4k "C:\Path\To\Data.p4k"
```

PowerShell compatibility wrapper:

```powershell
.codex/skills/sc-blueprint-extractor/scripts/core/extract_blueprints.ps1 -P4K "C:\Path\To\Data.p4k"
```

Runtime data goes to:

`/data/starcitizen/`

Review reports go to:

`informes/`

Preferred review commands:

```powershell
python .codex/skills/sc-blueprint-extractor/scripts/review/run_review_suite.py
```

Manual split, if needed:

```powershell
python .codex/skills/sc-blueprint-extractor/scripts/review/blueprint_mission_review.py --mode both
python .codex/skills/sc-blueprint-extractor/scripts/review/blueprint_reward_pool_review.py --mode both
```
