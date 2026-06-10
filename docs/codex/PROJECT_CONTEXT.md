# Project Context

Repositorio para mantener, validar, empaquetar y distribuir localizaciones de Star Citizen, con foco actual en espanol de Espana, y generar un instalador Windows para aplicar esas localizaciones sobre una instalacion existente del juego.

El mantenimiento de blueprints se hace desde una fuente estructurada:

- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`
- `source/blueprints/contracts_metadata.json`

El overlay `source/shared/overlays/blueprints.ini` es un artefacto generado para compatibilidad e inspeccion, no la fuente editable principal.

Para claves visibles detectadas in-game que no existan todavia en `input/current/global.ini`, el sitio correcto es `source/languages/<code>/overlays/modified_global.ini`.
No deben anadirse a `translation.ini`, que debe seguir alineado con la extraccion base actual.

El instalador y los artefactos de release comparten una frontera de codificacion importante:

- `global.ini` del juego debe mantenerse en UTF-8 con BOM;
- los metadatos del instalador deben leerse con tolerancia a BOM, incluido `dist/<version>/staging/<language>/_metadata/language.json`.

Modelo actual de distribucion:

- `dist/<version>/release-packages/` contiene el ZIP publico final por idioma, con todos los overlays soportados ya aplicados.
- `dist/<version>/staging/` y `dist/<version>/installer-bundle/` existen para el instalador y su flujo de actualizacion remota.
- Las combinaciones de overlays personalizadas deben resolverse en el instalador, no multiplicando los artefactos publicos de la release.
