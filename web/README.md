# Localization Studio

Panel local para la traducción de `global.ini`, pools de blueprints y enlaces de
misiones. No requiere instalar dependencias adicionales.

```powershell
.\venv\Scripts\python.exe .\web\app.py
```

Abra `http://127.0.0.1:8765`. El servicio escucha únicamente en localhost.

## Propuestas de traducción con IA

Para activar el botón **Proponer con IA**, defina una clave de OpenAI antes de
iniciar el panel. La propuesta se inserta en el editor para su revisión y no se
guarda automáticamente.

```powershell
$env:OPENAI_API_KEY = "..."
# Opcional: $env:OPENAI_TRANSLATION_MODEL = "<modelo>"
.\venv\Scripts\python.exe .\web\app.py
```

El servidor valida que la propuesta conserve placeholders, escapes y marcado
antes de devolverla al navegador.

## Modelo de datos

Al iniciar, el panel reconstruye `web/localization_studio.sqlite` desde los INI
y JSON versionados. SQLite es un índice local para búsquedas, idiomas, pools y
relaciones, no una segunda fuente de verdad: todos los cambios se escriben de
vuelta a los archivos del repositorio y el índice se sincroniza después. Esto
permite migrar más adelante a una base de datos como fuente primaria sin romper
el proceso de compilación actual.

## Garantías de edición

- Las claves INI no se muestran como editables; solo se cambia el texto a la
  derecha de `=`.
- Al guardar una traducción se verifica que marcadores, variables, escapes y
  etiquetas coinciden con el original.
- Al importar un nuevo `global.ini`, se conserva el anterior como
  `input/current/global.ini.previous`.
- La exportación usa el compilador existente `scripts/build_distributions.py`.
