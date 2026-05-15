# Patch Workflow

## Standard Patch Update

1. Extract latest English localization.
2. Sync missing localization keys.
3. Translate only newly added keys.
4. Extract and inspect blueprint/mission data.
5. Audit blueprint pools.
6. Regenerate generated overlays.
7. Build distributions.
8. Review build reports.
9. Optionally build installer, keeping the encoding boundary clear: `global.ini` remains UTF-8 with BOM for Star Citizen, installer metadata must remain parseable as installer JSON/text inputs.
10. Update local project memory.
