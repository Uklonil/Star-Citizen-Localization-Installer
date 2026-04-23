# Star-Citizen-Localization-Spanish

## English

Repository to maintain, validate, and distribute Star Citizen localizations.

This project covers three tasks:

- maintain master translation memories per language in `source/languages/<language>/`;
- generate ready-to-copy packages for `LIVE`, with variants and overlays;
- build a Windows installer to apply the localization over an existing installation.

### Credits and source material

Component, blueprint, and illegal goods overlays come from:

- [ExoAE/ScCompLangPack](https://github.com/ExoAE/ScCompLangPack)

### Languages and variants

Each language lives in its own folder:

- `source/languages/es-es/`
- `source/languages/en/`

Expected structure per language:

- `language.json`
- `translation.ini`
- `overlays/modified_global.ini`
- `overlays/components.ini`
- `overlays/blueprints.ini`
- optional `user.cfg`

`blueprints.ini` can be language-specific or shared. If a language-specific file
is missing, the build falls back to:

- `source/shared/overlays/blueprints.ini`

Priority order:

1. `source/languages/<language>/overlays/blueprints.ini`
2. `source/shared/overlays/blueprints.ini`

When both files exist, the build merges them by key:

- shared keys act as the base;
- language-specific keys override only the keys they redefine;
- missing keys in the language-specific file automatically fall back to the shared file.

`language.json` defines:

- `code`
- `label`
- `game_language`
- relative paths for translation memory and overlays
- whether the language should start directly from `input/current/global.ini`

English is prepared as a base language using the original `global.ini` plus its own overlays.

### What this repository generates

The pipeline generates four variants:

- `base`
- `componentes`
- `blueprints`
- `componentes-blueprints`

Each variant is packaged as a ZIP and also prepared in a `staging` directory for the installer.

### Project structure

- `source/languages/<language>/`
  Source content per language.
- `input/current/global.ini`
  Original English `global.ini` from the current patch.
- `input/translation-batches/`
  Workspace for batch-based translation.
- `scripts/`
  Extraction, validation, normalization, and build scripts.
- `installer/`
  Windows installer app built with `Flet`.
- `installer/ui_texts/`
  Localized installer UI texts with English fallback.
- `dist/`
  Output packages, staging folders, and versioned reports.
- `dist-installer/`
  Output executable for the installer.

### Requirements

The main workflow uses Python. Relevant dependencies:

- `scdatatools` to extract the English `global.ini` from `Data.p4k` or the game folder;
- `Flet` and `PyInstaller` to build the installer;
- the rest of the installer dependencies are listed in `installer/requirements-build.txt`.

Minimum installation to extract the English file:

```bash
python -m pip install scdatatools
```

Installation for building the installer:

```bash
python -m venv .installer-venv
.\.installer-venv\Scripts\python.exe -m pip install -r .\installer\requirements-build.txt
```

Keeping the installer environment separate is recommended because `PyInstaller` and `scdatatools` do not work well with the same `packaging` version in this repository.

### Recommended workflow per patch

#### 1. Extract the English `global.ini`

From the game folder:

```bash
python .\scripts\extract_english_localization.py "D:\RSI\StarCitizen\LIVE"
```

It also accepts a direct path to `Data.p4k`.

Default output:

```text
input/current/global.ini
```

#### 2. Maintain the master translation memory

```text
source/languages/<language>/translation.ini
```

The build compares each translation memory against the current English `global.ini`. If a language starts from English, `translation.ini` can stay empty and `use_english_source_as_base` can be enabled in its `language.json`.

#### 3. Translate in batches when the patch is large

The repository includes `scripts/manage_translation_batches.py` to work in line windows without breaking the final file.

Prepare the initial destination:

```bash
python .\scripts\manage_translation_batches.py init
```

Export one batch:

```bash
python .\scripts\manage_translation_batches.py export-batch --batch 1 --batch-size 250
```

Apply and validate a translated batch:

```bash
python .\scripts\manage_translation_batches.py apply-batch --batch 1 --batch-size 250
```

Check progress:

```bash
python .\scripts\manage_translation_batches.py status --batch-size 250
```

Each exported batch creates `source.ini`, `current.ini`, `translated.ini`, and a context `README.txt` in `input/translation-batches/batch-XXXX/`.

#### 4. Adjust overlays

Build application order:

1. `translation.ini` provides the language base translation.
2. `modified_global.ini` fully replaces a key value.
3. `components.ini` appends its suffix on top of the base.
4. `blueprints.ini` appends its suffix on top of the base or the already-extended variant.

For compatibility, if an old overlay still stores the full text instead of only the suffix, the pipeline automatically trims the base prefix before appending it.

`components.ini` and `blueprints.ini` support `@KEY@` references that are resolved against the effective language base.

`blueprints.ini` also supports language-local auxiliary tokens written as `##token##`.
These tokens are resolved from:

- `source/languages/<language>/auxiliary_keys.ini`

Example:

```ini
potential_blueprints=Potential Blueprints
regional_variants=Regional variants
```

Then inside `blueprints.ini`:

```ini
SomeMission_desc_001=\n\n\n\n<EM4>##potential_blueprints##</EM4>\n- @item_Nameexample@
```

This enables a lower-maintenance workflow for blueprints:

- keep a common `source/shared/overlays/blueprints.ini` for content shared by every language;
- add `source/languages/<language>/overlays/blueprints.ini` only when that language needs an override;
- if both exist, the language-specific file wins.

Blueprint rewards can also be maintained from a structured source:

- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`

`pools.json` stores reusable visible reward pools and a `mission_pool_map` that links each
`*_desc*` key to one pool. When both files exist, `build_distributions.py` generates the
effective shared `blueprints.ini` in memory before packaging, so GitHub workflows do not
depend on a materialized `source/shared/overlays/blueprints.ini`.

Utility scripts:

- `python .\scripts\bootstrap_blueprint_pools.py`
  Creates the initial structured source from the current shared overlay.
- `python .\scripts\generate_blueprints_overlay.py`
  Regenerates `source/shared/overlays/blueprints.ini` from the structured source.
  This file is now a generated artifact for inspection and compatibility, not a required build input.

The installer UI also loads its texts from external files:

- `installer/ui_texts/en.json`
- `installer/ui_texts/es-es.json`

If a key is missing in the selected language, the installer automatically falls back to the value in `en.json`.

#### 5. Generate distributions

```bash
python .\scripts\build_distributions.py --version 4.1.0
```

By default it builds all configured languages. To build only one:

```bash
python .\scripts\build_distributions.py --version 4.1.0 --language es-es
```

If needed, you can force a build without a valid base translation memory:

```bash
python .\scripts\build_distributions.py --version 4.1.0 --allow-empty-translation-memory
```

### Build output

The build creates:

- `dist/<version>/packages/star-citizen-<language>-<version>-base.zip`
- `dist/<version>/packages/star-citizen-<language>-<version>-componentes.zip`
- `dist/<version>/packages/star-citizen-<language>-<version>-blueprints.zip`
- `dist/<version>/packages/star-citizen-<language>-<version>-componentes-blueprints.zip`
- `dist/<version>/staging/<language>/<variant>/`
- `dist/<version>/reports/missing-keys-<language>.ini`
- `dist/<version>/reports/summary.txt`

Each ZIP package contains:

- `user.cfg`
- `data/Localization/<game_language>/global.ini`

### Included validations

`scripts/build_distributions.py` validates before packaging:

- no unknown keys in translation memory or overlays;
- placeholders, escapes, and markup remain intact where required;
- overlay `@KEY@` references can be resolved;
- output order and keys still match the English `global.ini`.

The repository also includes helper utilities:

- `scripts/check_placeholder_integrity.py`
  Detects keys in a `translation.ini` whose placeholders, escapes, or markup were altered.
- `scripts/classify_placeholder_mismatches.py`
  Groups placeholder failures by type.
- `scripts/classify_newline_mismatches.py`
  Classifies newline-related issues.
- `scripts/inspect_mismatch_keys.py`
  Helps inspect specific keys with issues.
- `scripts/normalize_blueprints_overlay.py`
  Replaces literal object names inside `blueprints.ini` with `@KEY@` references to improve consistency.

Example integrity check:

```bash
python .\scripts\check_placeholder_integrity.py
```

### Executable installer

The repository includes a Windows GUI app to install the localization directly over Star Citizen.

Components:

- `installer/app.py`
  `Flet` interface.
- `installer/installer_core.py`
  Path detection, variant discovery, and file copy logic.
- `scripts/build_installer.py`
  `.exe` packaging with `PyInstaller`.
- `installer/ui_texts/*.json`
  Installer UI texts per language.

The app:

- tries to detect `LIVE`, `EPTU`, or `PTU` paths;
- accepts either the channel folder or the `StarCitizen` root;
- detects available languages in `staging`;
- allows selecting the language before the variant;
- allows choosing `base`, `componentes`, `blueprints`, or `componentes-blueprints`;
- copies `user.cfg` and `data/Localization/<game_language>/global.ini`;
- warns when the target path requires administrator privileges.

Before building the installer, first generate a version in `dist/<version>/staging` with `build_distributions.py`.

Build the executable:

```bash
.\.installer-venv\Scripts\python.exe .\scripts\build_installer.py --version 4.1.0
```

If `--version` is omitted, the script uses the most recent folder inside `dist/`.

Expected output:

```text
dist-installer/StarCitizenLocalizationInstaller.exe
```

You can also open the app directly in script mode:

```bash
.\venv\Scripts\python.exe .\installer\app.py
```

### Quick usage

1. Extract the English `global.ini` for the current patch.
2. Update `source/languages/<language>/translation.ini`.
3. Adjust `source/languages/<language>/overlays/*.ini` if needed.
4. Run `build_distributions.py`.
5. Distribute the ZIPs or generate the installer with `build_installer.py`.

### Automated GitHub release workflow

- The repository root contains a `VERSION` file used as the default release version.
- `.github/workflows/release-build.yml` runs automatically when a pull request from `develop` is merged into `main`.
- The workflow can still be run manually with `workflow_dispatch`; in that case the optional `version` input overrides `VERSION`.
- Recommended release flow:
  1. Update `VERSION` in `develop`.
  2. Commit the extracted `input/current/global.ini` and the localization changes for that patch.
  3. Merge `develop` into `main`.
  4. Let the workflow build packages, the installer, the manifest, and the GitHub release from that merge commit.

### Support and additional info

If you want to support this project, you can use my referral code when buying Star Citizen:

```text
STAR-9999-C6LK
```

You can also support me directly on Ko-fi:

- [☕ Ko-Fi](https://ko-fi.com/uklonil)

Thanks for using this language distribution and/or the installer.

---

## Español

Repositorio para mantener, validar y distribuir localizaciones de Star Citizen.

El proyecto cubre tres tareas:

- mantener memorias maestras de traduccion por idioma en `source/languages/<idioma>/`;
- generar paquetes listos para copiar en `LIVE`, con variantes y overlays;
- construir un instalador de Windows para aplicar la traduccion sobre una instalacion existente.

### Creditos y origen del contenido

La base de la traduccion se ha tomado de:

- [Doncasta1996/Star-Citizen-Spanish](https://github.com/Doncasta1996/Star-Citizen-Spanish)

Los overlays de componentes, blueprints y productos ilegales se han tomado de:

- [ExoAE/ScCompLangPack](https://github.com/ExoAE/ScCompLangPack)

### Idiomas y variantes

Cada idioma vive en su propia carpeta:

- `source/languages/es-es/`
- `source/languages/en/`

La estructura esperada por idioma es:

- `language.json`
- `translation.ini`
- `overlays/modified_global.ini`
- `overlays/components.ini`
- `overlays/blueprints.ini`
- `user.cfg` opcional

`blueprints.ini` puede ser especifico del idioma o compartido. Si falta el
fichero del idioma, el build usa como fallback:

- `source/shared/overlays/blueprints.ini`

Orden de prioridad:

1. `source/languages/<idioma>/overlays/blueprints.ini`
2. `source/shared/overlays/blueprints.ini`

Si existen ambos ficheros, el build los fusiona por clave:

- las claves del compartido actuan como base;
- el fichero especifico del idioma solo sobreescribe las claves que redefine;
- las claves ausentes en el fichero del idioma caen automaticamente al compartido.

`language.json` define:

- `code`
- `label`
- `game_language`
- rutas relativas de memoria y overlays
- si el idioma debe partir directamente del `input/current/global.ini`

El ingles queda preparado como idioma base usando el `global.ini` original y sus propios overlays.

### Que genera este repo

El pipeline genera cuatro variantes:

- `base`
- `componentes`
- `blueprints`
- `componentes-blueprints`

Cada variante termina empaquetada como ZIP y, ademas, se deja preparada en un directorio `staging` para el instalador.

### Estructura del proyecto

- `source/languages/<idioma>/`
  Contenido fuente por idioma.
- `input/current/global.ini`
  `global.ini` original en ingles del parche actual.
- `input/translation-batches/`
  Espacio de trabajo para traducir por lotes.
- `scripts/`
  Scripts de extraccion, validacion, normalizacion y build.
- `installer/`
  App de instalacion en Windows basada en `Flet`.
- `installer/ui_texts/`
  Textos localizados de la interfaz del instalador, con fallback a ingles.
- `dist/`
  Salida de paquetes, staging y reportes por version.
- `dist-installer/`
  Salida del ejecutable del instalador.

### Requisitos

El flujo principal usa Python. Dependencias relevantes:

- `scdatatools` para extraer el `global.ini` ingles desde `Data.p4k` o desde la carpeta del juego;
- `Flet` y `PyInstaller` para construir el instalador;
- el resto de dependencias del instalador estan en `installer/requirements-build.txt`.

Instalacion minima para extraer el archivo ingles:

```bash
python -m pip install scdatatools
```

Instalacion para construir el instalador:

```bash
python -m venv .installer-venv
.\.installer-venv\Scripts\python.exe -m pip install -r .\installer\requirements-build.txt
```

Se recomienda separar el entorno del instalador porque `PyInstaller` y `scdatatools` no conviven bien con la misma version de `packaging` dentro de este repo.

### Flujo recomendado por parche

#### 1. Extraer el `global.ini` ingles

Desde la carpeta del juego:

```bash
python .\scripts\extract_english_localization.py "D:\RSI\StarCitizen\LIVE"
```

Tambien acepta una ruta directa al archivo `Data.p4k`.

La salida por defecto es:

```text
input/current/global.ini
```

#### 2. Mantener la memoria maestra de traduccion

```text
source/languages/<idioma>/translation.ini
```

El build cruza cada memoria con el `global.ini` ingles actual. Si un idioma parte del ingles, puede dejar `translation.ini` vacio y usar `use_english_source_as_base` en su `language.json`.

#### 3. Traducir por lotes cuando el parche es grande

El repo incluye `scripts/manage_translation_batches.py` para trabajar por ventanas de lineas sin romper el archivo final.

Preparar el destino inicial:

```bash
python .\scripts\manage_translation_batches.py init
```

Exportar un lote:

```bash
python .\scripts\manage_translation_batches.py export-batch --batch 1 --batch-size 250
```

Aplicar un lote traducido y validarlo:

```bash
python .\scripts\manage_translation_batches.py apply-batch --batch 1 --batch-size 250
```

Consultar progreso:

```bash
python .\scripts\manage_translation_batches.py status --batch-size 250
```

Cada lote exportado crea `source.ini`, `current.ini`, `translated.ini` y un `README.txt` de contexto en `input/translation-batches/batch-XXXX/`.

#### 4. Ajustar overlays

El orden de aplicacion durante el build es:

1. `translation.ini` aporta la traduccion base del idioma.
2. `modified_global.ini` reemplaza por completo el valor de una clave.
3. `components.ini` concatena su sufijo sobre la base.
4. `blueprints.ini` concatena su sufijo sobre la base o sobre la variante ya extendida.

Por compatibilidad, si un overlay antiguo todavia guarda el texto completo en vez del sufijo, el pipeline recorta automaticamente el prefijo base antes de anexarlo.

Los overlays `components.ini` y `blueprints.ini` admiten referencias `@KEY@` que se resuelven contra la base efectiva del idioma.

`blueprints.ini` tambien admite tokens auxiliares por idioma escritos como `##token##`.
Estos tokens se resuelven desde:

- `source/languages/<idioma>/auxiliary_keys.ini`

Ejemplo:

```ini
potential_blueprints=Planos potenciales
regional_variants=Variantes regionales
```

Y dentro de `blueprints.ini`:

```ini
SomeMission_desc_001=\n\n\n\n<EM4>##potential_blueprints##</EM4>\n- @item_Nameexample@
```

Esto permite un flujo de mantenimiento mas simple para blueprints:

- mantener un `source/shared/overlays/blueprints.ini` comun para contenido compartido por todos los idiomas;
- anadir `source/languages/<idioma>/overlays/blueprints.ini` solo cuando ese idioma necesite un override;
- si existen ambos, el fichero especifico del idioma tiene prioridad.

Las recompensas de blueprints tambien pueden mantenerse desde una fuente estructurada:

- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`

`pools.json` guarda pools reutilizables de recompensas visibles y un `mission_pool_map` que
enlaza cada clave `*_desc*` con una pool. Si ambos ficheros existen, `build_distributions.py`
genera en memoria el `blueprints.ini` compartido efectivo antes de empaquetar.

Scripts utiles:

- `python .\scripts\bootstrap_blueprint_pools.py`
  Genera la fuente estructurada inicial a partir del overlay compartido actual.
- `python .\scripts\generate_blueprints_overlay.py`
  Regenera `source/shared/overlays/blueprints.ini` desde la fuente estructurada.

La interfaz del instalador tambien carga sus textos desde archivos externos:

- `installer/ui_texts/en.json`
- `installer/ui_texts/es-es.json`

Si falta una clave en el idioma seleccionado, el instalador usa automaticamente el valor de `en.json`.

#### 5. Generar distribuciones

```bash
python .\scripts\build_distributions.py --version 4.1.0
```

Por defecto compila todos los idiomas configurados. Para compilar solo uno:

```bash
python .\scripts\build_distributions.py --version 4.1.0 --language es-es
```

Si hiciera falta forzar una compilacion sin traduccion base valida:

```bash
python .\scripts\build_distributions.py --version 4.1.0 --allow-empty-translation-memory
```

### Salida del build

El build crea:

- `dist/<version>/packages/star-citizen-<idioma>-<version>-base.zip`
- `dist/<version>/packages/star-citizen-<idioma>-<version>-componentes.zip`
- `dist/<version>/packages/star-citizen-<idioma>-<version>-blueprints.zip`
- `dist/<version>/packages/star-citizen-<idioma>-<version>-componentes-blueprints.zip`
- `dist/<version>/staging/<idioma>/<variant>/`
- `dist/<version>/reports/missing-keys-<idioma>.ini`
- `dist/<version>/reports/summary.txt`

Cada paquete ZIP contiene:

- `user.cfg`
- `data/Localization/<game_language>/global.ini`

### Validaciones incluidas

`scripts/build_distributions.py` valida antes de empaquetar:

- que no existan claves desconocidas en la memoria ni en los overlays;
- que los placeholders, escapes y markup no se rompan donde corresponde;
- que las referencias `@KEY@` de overlays se puedan resolver;
- que el orden y las claves de salida sigan el `global.ini` ingles.

Ademas, el repo incluye utilidades auxiliares:

- `scripts/check_placeholder_integrity.py`
  Detecta claves de una `translation.ini` con placeholders, escapes o markup alterados.
- `scripts/classify_placeholder_mismatches.py`
  Agrupa los fallos de placeholders por tipo.
- `scripts/classify_newline_mismatches.py`
  Clasifica problemas relacionados con saltos de linea.
- `scripts/inspect_mismatch_keys.py`
  Ayuda a inspeccionar claves concretas con incidencias.
- `scripts/normalize_blueprints_overlay.py`
  Sustituye nombres literales dentro de `blueprints.ini` por referencias `@KEY@` para mantener mejor la consistencia.

Ejemplo de chequeo de integridad:

```bash
python .\scripts\check_placeholder_integrity.py
```

### Instalador ejecutable

El repo incluye una app grafica de Windows para instalar la traduccion directamente sobre Star Citizen.

Componentes:

- `installer/app.py`
  Interfaz `Flet`.
- `installer/installer_core.py`
  Deteccion de rutas, descubrimiento de variantes y copia de archivos.
- `scripts/build_installer.py`
  Empaquetado a `.exe` con `PyInstaller`.
- `installer/ui_texts/*.json`
  Textos de la interfaz del instalador por idioma.

La app:

- intenta detectar rutas `LIVE`, `EPTU` o `PTU`;
- acepta la carpeta de canal o la raiz de `StarCitizen`;
- detecta los idiomas disponibles en el `staging`;
- permite elegir idioma antes de la variante;
- permite elegir `base`, `componentes`, `blueprints` o `componentes-blueprints`;
- copia `user.cfg` y `data/Localization/<game_language>/global.ini`;
- avisa cuando la ruta requiere permisos de administrador.

Antes de construir el instalador, genera primero una version en `dist/<version>/staging` con `build_distributions.py`.

Construccion del ejecutable:

```bash
.\.installer-venv\Scripts\python.exe .\scripts\build_installer.py --version 4.1.0
```

Si omites `--version`, el script usa la carpeta mas reciente dentro de `dist/`.

Salida esperada:

```text
dist-installer/StarCitizenLocalizationInstaller.exe
```

Tambien puedes abrir la app directamente en modo script:

```bash
.\venv\Scripts\python.exe .\installer\app.py
```

### Uso rapido

1. Extrae el `global.ini` ingles del parche actual.
2. Actualiza `source/languages/<idioma>/translation.ini`.
3. Ajusta `source/languages/<idioma>/overlays/*.ini` si hace falta.
4. Ejecuta `build_distributions.py`.
5. Distribuye los ZIP o genera el instalador con `build_installer.py`.

### Flujo automatizado de release en GitHub

- La raiz del repositorio incluye un fichero `VERSION` que se usa como version por defecto de la release.
- `.github/workflows/release-build.yml` se ejecuta automaticamente cuando se fusiona en `main` un pull request procedente de `develop`.
- El workflow se puede seguir lanzando manualmente con `workflow_dispatch`; en ese caso, la entrada opcional `version` tiene prioridad sobre `VERSION`.
- Flujo recomendado de release:
  1. Actualiza `VERSION` en `develop`.
  2. Sube `input/current/global.ini` extraido y los cambios de localizacion del parche.
  3. Fusiona `develop` en `main`.
  4. Deja que el workflow construya paquetes, instalador, manifiesto y release de GitHub a partir de ese merge commit.

### Soporte e informacion adicional

Si quieres apoyar este proyecto, puedes usar mi codigo de referencia al comprar Star Citizen:

```text
STAR-9999-C6LK
```

Tambien puedes apoyarme directamente en Ko-fi:

- [☕ Ko-Fi](https://ko-fi.com/uklonil)

Gracias por usar esta distribucion de idioma y/o el instalador.
