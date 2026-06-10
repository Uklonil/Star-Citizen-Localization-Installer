# Contracts Metadata Extraction Proposal

## Objetivo

Aprovechar `contracts.ini` de StarStrings como fuente secundaria de metadatos manuales sobre contratos ya existentes en `global.ini`, sin convertirlo en fuente primaria de traduccion ni de overlays de build.

El extractor debe centrarse en tres capas utiles:

- marcas visibles en `title`
- bloques informativos en `desc`
- contexto ampliado de blueprints

## No objetivos

- no importar ni sustituir textos base de contratos
- no escribir directamente en `source/blueprints/pools.json`
- no modificar automaticamente `source/shared/overlays/blueprints.ini`
- no depender de GitHub en la build

## Hallazgos

`contracts.ini` remoto aporta metadatos que ya no estan estructurados en el repo:

- `title` con marcas como `[BP]`, `[BP]*`, `[50 Rep]`, `[50/200 Rep]`
- `desc` con bloques `Reputation Awarded`
- `desc` con `Scenario Progress Points`
- `desc` con `Potential Blueprints`
- `desc` con etiquetas de variantes como `Awarded from Neutral/Jr./Sr./Master level variants`
- casos especiales con `Multiple Blueprint Pools`

Las claves ya existen en `distribucion/global.ini`. El valor del remoto no esta en las claves, sino en esas anotaciones.

## Enfoque recomendado

Implementar un extractor de discovery, no de build, con esta ruta:

- script:
  `.codex/skills/sc-blueprint-extractor/scripts/review/extract_contract_metadata_candidates.py`
- salida machine-readable:
  `/data/starcitizen/reports/blueprints/contracts_metadata_candidates.json`
- salida humana:
  `informes/CONTRACTS_METADATA_EXTRACTION_REPORT.md`

## Entradas

- `contracts.ini` remoto descargado bajo demanda o una copia local temporal
- `distribucion/global.ini`
- `source/blueprints/pools.json`
- `source/shared/overlays/blueprints.ini`

## Salida JSON propuesta

```json
{
  "source": "contracts.ini",
  "generated_at": "2026-06-10T12:00:00+02:00",
  "titles": {
    "UWC_Refueling_high_title_001": {
      "blueprint_flag": true,
      "blueprint_flag_uncertain": true,
      "rep_ranges": ["200"],
      "raw_suffix": "<EM4>[200 Rep] [BP]*</EM4>"
    }
  },
  "descriptions": {
    "UWC_Refueling_high_desc_001": {
      "reputation_awarded": ["200"],
      "scenario_progress_points": [],
      "blueprint_variant_tiers": [],
      "pool_headers": [],
      "has_potential_blueprints_block": true
    }
  },
  "blueprint_context": {
    "UWC_Refueling_high_desc_001": {
      "variant_label_tokens": [],
      "pool_count": 1,
      "raw_block_lines": [
        "- bp_craft_nozzle_fuelgiver_grin_nozzlefast (Fuel Nozzle)"
      ]
    }
  }
}
```

## Reglas de extraccion

### 1. Metadatos de `title`

Parsear el sufijo final `<EM4>...</EM4>` y extraer:

- `blueprint_flag`
- `blueprint_flag_uncertain` para `*`
- `rep_ranges` como lista de strings para no perder formato `50/200/8000`
- `raw_suffix` para auditoria

Esto sirve para un futuro overlay opcional de titulos, pero por ahora solo como reporte.

### 2. Metadatos de `desc`

Detectar:

- `Reputation Awarded:`
- `Reputation Awarded (by difficulty):`
- `Scenario Progress Points`
- `Potential Blueprints`
- `Multiple Blueprint Pools`
- `Awarded from <tier> level variants`

La normalizacion debe preservar el texto bruto y, ademas, generar campos estructurados simples.

### 3. Contexto de blueprints

Si el bloque contiene items:

- guardar las lineas tal cual para auditoria
- detectar si ya existe una pool equivalente en `pools.json`
- clasificar el caso:
  - `already-covered`
  - `new-tier-label-only`
  - `new-metadata-only`
  - `candidate-new-pool-shape`

## Integracion por fases

### Fase 1

Solo discovery y reporte.

Entrega:

- script de parseo
- JSON estructurado
- informe markdown con resumen por categoria

### Fase 2

Promocion manual de metadatos utiles a fuente versionada, solo si compensa.

Opciones:

- ampliar `pools.json` con claves opcionales no usadas por la build
- crear `source/blueprints/contracts_metadata.json` como fuente separada

Recomendacion:

usar archivo separado. `pools.json` ahora mismo esta bien acotado a recompensas visibles y no conviene mezclarle reputacion ni puntos de escenario.

### Fase 3

Si se aprueba una UI/build para esas marcas:

- overlay opcional de titulos con `[Rep]` y `[BP]`
- bloque opcional de `Scenario Progress Points` en descripciones
- tokens auxiliares localizables para etiquetas de tier

## Fuente versionada recomendada si se promociona

`source/blueprints/contracts_metadata.json`

Estructura minima:

```json
{
  "version": 1,
  "notes": [
    "Metadatos manuales derivados de contracts.ini de StarStrings.",
    "No participa en la build hasta integracion explicita."
  ],
  "title_meta": {},
  "description_meta": {}
}
```

## Criterio de utilidad real

Merece la pena extraer si se persigue al menos uno de estos resultados:

- reducir revision manual de contratos con blueprints
- detectar tiers de reputacion visibles sin inspeccion manual
- inventariar `Scenario Progress Points`
- encontrar pools con mas contexto que el overlay actual

No merece la pena si el objetivo es solo copiar texto, porque ese valor ya vive en `global.ini`.

## Siguiente paso recomendado

Implementar la Fase 1 con un parser local y un reporte de resumen con estas tablas:

- `titles` con `[BP]` y `[Rep]`
- `desc` con `Reputation Awarded`
- `desc` con `Scenario Progress Points`
- `desc` con `Awarded from ... variants`
- casos `Multiple Blueprint Pools`

Ese paso deja claro, con datos, si luego conviene crear `contracts_metadata.json`.
