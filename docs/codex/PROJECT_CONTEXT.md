# Project Context

Repositorio para mantener, validar, empaquetar y distribuir localizaciones de Star Citizen, con foco actual en español de España, y generar un instalador Windows para aplicar esas localizaciones sobre una instalación existente del juego.

El mantenimiento de blueprints se hace desde una fuente estructurada:

- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`

El overlay `source/shared/overlays/blueprints.ini` es un artefacto generado para compatibilidad e inspección, no la fuente editable principal.

El instalador y los artefactos de release comparten una frontera de codificación importante:

- `global.ini` del juego debe mantenerse en UTF-8 con BOM;
- los metadatos del instalador deben leerse con tolerancia a BOM, incluido `dist/<version>/staging/<language>/_metadata/language.json`.
