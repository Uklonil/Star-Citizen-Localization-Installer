# sc-patch-update

Main command:

```powershell
.codex/skills/sc-patch-update/scripts/run_patch_update.ps1
```

Explicit P4K:

```powershell
.codex/skills/sc-patch-update/scripts/run_patch_update.ps1 `
  -P4K "C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k"
```

Force everything:

```powershell
.codex/skills/sc-patch-update/scripts/run_patch_update.ps1 -ForceFull
```

Force build only:

```powershell
.codex/skills/sc-patch-update/scripts/run_patch_update.ps1 -ForceBuild
```

Use explicit version/build label:

```powershell
.codex/skills/sc-patch-update/scripts/run_patch_update.ps1 -Version 4.7.2-live.11674325
```

Skip parts:

```powershell
.codex/skills/sc-patch-update/scripts/run_patch_update.ps1 -SkipBlueprints
.codex/skills/sc-patch-update/scripts/run_patch_update.ps1 -SkipBuild
```

Reports:

- `informes/version-sync-report.md`
- `informes/PATCH_UPDATE_REPORT.md`
- `informes/project_memory.local.md`
