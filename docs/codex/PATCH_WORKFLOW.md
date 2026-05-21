# Patch Workflow

## Standard Patch Update

1. Extract latest English localization.
2. Sync missing localization keys.
3. Translate only newly added keys.
4. Extract and inspect blueprint/mission data.
5. Audit blueprint pools from review reports, contract links, and missiondata evidence.
6. Apply only strict or explicitly reviewed blueprint mappings to `source/blueprints/blueprints_template.ini` and `source/blueprints/pools.json`.
7. Regenerate generated overlays when needed.
8. Build distributions.
9. Review build reports.
10. Optionally build installer, keeping the encoding boundary clear: `global.ini` remains UTF-8 with BOM for Star Citizen, installer metadata must remain parseable as installer JSON/text inputs, including staged `_metadata/language.json`.
11. Update local project memory.
