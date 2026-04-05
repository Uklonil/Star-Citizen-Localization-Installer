# Star-Citizen-Localization-Spanish

Pipeline local para mantener y distribuir la traduccion al espanol de Star Citizen.

## Objetivo

Generar automaticamente paquetes ZIP listos para extraer dentro de la carpeta `LIVE` del juego a partir de:

- El `global.ini` original en ingles de cada parche.
- Una memoria maestra de traducciones en espanol.
- Overlays opcionales para variantes de distribucion.

El sistema genera cuatro variantes:

- `base`
- `componentes`
- `blueprints`
- `componentes-blueprints`

## Estructura

- `source/translations/base-spanish.ini`
  Memoria maestra con las traducciones en espanol por clave.
- `source/user.cfg`
  Archivo `user.cfg` que se incluye en todas las distribuciones generadas.
- `source/overlays/modified_global.ini`
  Sobrescrituras globales por reemplazo completo de clave, aplicadas a todas las distribuciones.
- `source/overlays/components.ini`
  Sobrescrituras para la variante con nombres de componentes.
- `source/overlays/blueprints.ini`
  Sobrescrituras para la variante con misiones marcadas con `[BP]`.
- `input/current/global.ini`
  `global.ini` original en ingles del parche actual.
- `dist/`
  Salida generada automaticamente.

## Entorno Python

El repositorio usa un flujo basado en `python` para todo el pipeline. Ya no es necesario usar comandos de PowerShell de forma especifica.

Instala `scdatatools` y el resto de dependencias desde tu entorno Python activo:

```bash
python -m pip install scdatatools
```

Para extraer el `global.ini` ingles directamente desde el juego:

```bash
python .\scripts\extract_english_localization.py "D:\RSI\StarCitizen\LIVE"
```

Tambien acepta una ruta directa a `Data.p4k`.

## Flujo recomendado por parche

1. Extrae el `global.ini` original en ingles del parche y guardalo en `input/current/global.ini` en la raiz del repositorio.
   Puedes hacerlo automaticamente con `extract_english_localization.py`.
2. Manten `source/translations/base-spanish.ini` como tu archivo maestro de traduccion. Debe contener claves reales del parche; si esta vacio o no coincide con el `global.ini` actual, el build fallara por defecto.
3. Añade en `source/overlays/modified_global.ini` cualquier clave que deba sustituirse por completo en todas las distribuciones.
4. Añade en `source/overlays/components.ini` solo el sufijo que quieras anexar para componentes.
5. Añade en `source/overlays/blueprints.ini` solo el sufijo que quieras anexar para `[BP]` y descripciones.
6. Genera las distribuciones:

```bash
python .\scripts\build_distributions.py --version 4.1.0
```

Orden de aplicacion durante el build:

- `base-spanish.ini` aporta la traduccion base.
- `modified_global.ini` sustituye por completo el valor de la clave en todas las distribuciones.
- `components.ini` sigue aplicandose como concatenacion de sufijos.
- `blueprints.ini` sigue aplicandose como concatenacion de sufijos.

Por compatibilidad, si un overlay concatenativo antiguo todavia contiene la cadena completa en lugar del sufijo, el build recorta automaticamente el prefijo base antes de anexarlo.

## Flujo por lotes de traduccion

Para traducir `input/current/global.ini` en bloques de 250 lineas y validar cada bloque:

1. Inicializa `source/translations/base-spanish.ini` con el contenido actual del origen:

```bash
python .\scripts\manage_translation_batches.py init
```

2. Exporta el lote que quieras traducir:

```bash
python .\scripts\manage_translation_batches.py export-batch --batch 1
```

Esto crea `source.ini`, `current.ini`, `translated.ini` y `README.txt` en `input/translation-batches/batch-0001/`.

3. Traduce `source.ini` a `translated.ini` usando la skill `translate-loc`.
4. Aplica el lote traducido y valida tanto el lote como el archivo completo:

```bash
python .\scripts\manage_translation_batches.py apply-batch --batch 1
```

5. Consulta el progreso cuando lo necesites:

```bash
python .\scripts\manage_translation_batches.py status
```

Validaciones del build:

- Falla si `base-spanish.ini` no aporta ninguna clave del parche actual, salvo que fuerces `--allow-empty-translation-memory`.
- Falla si la memoria maestra o cualquier overlay contiene claves inexistentes en el `global.ini` ingles.
- Falla si se alteran placeholders, secuencias escapadas o markup respecto al archivo origen.
- Falla si cambia el orden o el conjunto de claves en cualquiera de las variantes generadas.

## Resultado

El comando anterior crea:

- `dist/<version>/packages/star-citizen-es-<version>-base.zip`
- `dist/<version>/packages/star-citizen-es-<version>-componentes.zip`
- `dist/<version>/packages/star-citizen-es-<version>-blueprints.zip`
- `dist/<version>/packages/star-citizen-es-<version>-componentes-blueprints.zip`

Cada ZIP contiene la estructura lista para extraer dentro de `LIVE`:

- `user.cfg`
- `data/Localization/spanish_(spain)/global.ini`

## Reportes

Despues de cada build se generan:

- `dist/<version>/reports/missing-keys.ini`
  Claves nuevas del parche que aun no tienen traduccion y por tanto se quedaron en ingles.
- `dist/<version>/reports/summary.txt`
  Resumen del numero total de claves, cobertura base y pendientes.
