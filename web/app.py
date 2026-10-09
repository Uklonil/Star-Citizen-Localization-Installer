"""Local control panel for the Star Citizen localization workspace.

Run from the repository root with:
    python web/app.py
Then open http://127.0.0.1:8765

The application deliberately has no third-party runtime dependencies.  It edits
only values in INI files and keeps the repository files as the source of truth.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
GLOBAL = ROOT / "input" / "current" / "global.ini"
TRANSLATION = ROOT / "source" / "languages" / "es-es" / "translation.ini"
POOLS = ROOT / "source" / "blueprints" / "pools.json"
METADATA = ROOT / "source" / "blueprints" / "contracts_metadata.json"
COMPONENTS = ROOT / "source" / "languages" / "es-es" / "overlays" / "components.ini"
VERSION = ROOT / "VERSION"
DATABASE = ROOT / "web" / "localization_studio.sqlite"
TOKEN_RE = re.compile(r"%(?:\d+\$)?[sdif]|\{(?:\d+|[A-Za-z_][A-Za-z0-9_]*)\}|\\[ntr\"]|\[\[.*?\]\]|</?EM[1-4]>")


def read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes() if path.exists() else b""
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    return raw.decode(encoding), encoding


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as file:
        file.write(content)
        temporary = Path(file.name)
    os.replace(temporary, path)


def parse_ini(path: Path) -> dict[str, str]:
    content, _ = read_text(path)
    entries: dict[str, str] = {}
    for line in content.splitlines():
        if "=" not in line or line.lstrip().startswith(("#", ";")):
            continue
        key, value = line.split("=", 1)
        entries[key] = value
    return entries


def update_ini_value(path: Path, key: str, value: str) -> None:
    content, encoding = read_text(path)
    lines = content.splitlines(keepends=True)
    for index, line in enumerate(lines):
        raw = line.rstrip("\r\n")
        if raw.startswith(key + "="):
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            lines[index] = key + "=" + value + newline
            atomic_write(path, "".join(lines), encoding)
            return
    newline = "\r\n" if "\r\n" in content else "\n"
    atomic_write(path, content + ("" if not content or content.endswith(("\n", "\r")) else newline) + key + "=" + value + newline, encoding)


def json_file(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as file:
        return json.load(file)


def save_json(path: Path, payload: dict) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def validate_tokens(source: str, candidate: str) -> None:
    if TOKEN_RE.findall(source) != TOKEN_RE.findall(candidate):
        raise ValueError("Los marcadores, variables, escapes o etiquetas deben conservarse exactamente.")


def ai_translation_proposal(source: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Configura OPENAI_API_KEY antes de solicitar una propuesta de IA.")
    prompt = (
        "Traduce al español de España una única cadena de interfaz de Star Citizen. "
        "Devuelve exclusivamente la traducción, sin comillas ni explicación. "
        "Conserva exactamente placeholders (%s, {name}), escapes (\\n), etiquetas "
        "(<EM4>, [[...]]), nombres propios, marcas y códigos internos. "
        "Usa un tono claro y conciso. Cadena: " + source
    )
    payload = json.dumps({
        "model": os.environ.get("OPENAI_TRANSLATION_MODEL", "gpt-4.1-mini"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            proposed = json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as error:
        raise RuntimeError(f"No se pudo obtener una propuesta de IA: {error}") from error
    validate_tokens(source, proposed)
    return proposed


def database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def sync_database() -> None:
    """Rebuild the local SQLite index from versioned sources.

    SQLite accelerates the UI and gives the domain a normalized shape, while INI
    and JSON continue as the editable, reviewable project source of truth.
    """
    global_entries, translations = parse_ini(GLOBAL), parse_ini(TRANSLATION)
    source = json_file(POOLS)
    metadata = json_file(METADATA)
    components = parse_ini(COMPONENTS)
    with database() as db:
        db.executescript("""
            DROP TABLE IF EXISTS entries;
            DROP TABLE IF EXISTS pools;
            DROP TABLE IF EXISTS pool_items;
            DROP TABLE IF EXISTS mission_pools;
            DROP TABLE IF EXISTS contract_metadata;
            DROP TABLE IF EXISTS component_overlays;
            CREATE TABLE entries (
              key TEXT PRIMARY KEY, source_value TEXT NOT NULL, translated_value TEXT NOT NULL
            );
            CREATE TABLE pools (name TEXT PRIMARY KEY);
            CREATE TABLE pool_items (pool_name TEXT NOT NULL, item_key TEXT NOT NULL, position INTEGER NOT NULL, PRIMARY KEY(pool_name, position));
            CREATE TABLE mission_pools (mission_key TEXT NOT NULL, pool_name TEXT NOT NULL, position INTEGER NOT NULL, PRIMARY KEY(mission_key, position));
            CREATE TABLE contract_metadata (kind TEXT NOT NULL, entry_key TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind, entry_key));
            CREATE TABLE component_overlays (key TEXT PRIMARY KEY, component_type TEXT NOT NULL);
        """)
        db.executemany("INSERT INTO entries VALUES (?, ?, ?)", ((key, value, translations.get(key, "")) for key, value in global_entries.items()))
        db.executemany("INSERT INTO pools VALUES (?)", ((name,) for name in source["pools"]))
        db.executemany("INSERT INTO pool_items VALUES (?, ?, ?)", ((pool, item, position) for pool, body in source["pools"].items() for position, item in enumerate(body.get("item_refs", []))))
        db.executemany("INSERT INTO mission_pools VALUES (?, ?, ?)", ((mission, pool, position) for mission, names in source["mission_pool_map"].items() for position, pool in enumerate(names if isinstance(names, list) else [names])))
        db.executemany("INSERT INTO contract_metadata VALUES (?, ?, ?)", ((kind, key, json.dumps(value, ensure_ascii=False)) for kind in ("title_meta", "description_meta") for key, value in metadata.get(kind, {}).items()))
        db.executemany("INSERT INTO component_overlays VALUES (?, ?)", components.items())


def item_label(item_key: str, english: dict[str, str], translations: dict[str, str]) -> dict[str, str]:
    return {"key": item_key, "label": translations.get(item_key) or english.get(item_key) or item_key, "source": english.get(item_key, "")}


def mission_title_key(description_key: str, entries: dict[str, str]) -> str | None:
    """Return the exact _Title_ sibling of a persisted _Desc_ mission key."""
    candidate = re.sub(r"_description(?=_|$)", "_Title", description_key, flags=re.IGNORECASE)
    candidate = re.sub(r"_desc(?=_|$)", "_Title", candidate, flags=re.IGNORECASE)
    exact_keys = {key.casefold(): key for key in entries}
    return exact_keys.get(candidate.casefold())


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, format: str, *args) -> None:
        print("[web] " + format % args)

    def send_json(self, body: object, status: int = 200) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            with database() as db:
                counts = db.execute("SELECT COUNT(*) AS total, SUM(translated_value = '') AS missing FROM entries").fetchone()
            self.send_json({"version": VERSION.read_text(encoding="utf-8").strip() if VERSION.exists() else "dev", "global_keys": counts["total"], "translated_keys": counts["total"] - counts["missing"], "missing_keys": counts["missing"], "storage": "SQLite index"})
            return
        if parsed.path == "/api/entries":
            query = parse_qs(parsed.query).get("q", [""])[0].casefold()
            pending_only = parse_qs(parsed.query).get("pending", ["0"])[0] == "1"
            same_only = parse_qs(parsed.query).get("same", ["0"])[0] == "1"
            with database() as db:
                filter_sql = "translated_value = '' AND trim(source_value) <> ''" if pending_only else "translated_value = source_value AND trim(source_value) <> ''" if same_only else ""
                if query:
                    pattern = f"%{query}%"
                    where = f"({filter_sql} AND " if filter_sql else "("
                    where += "lower(key) LIKE ? OR lower(source_value) LIKE ? OR lower(translated_value) LIKE ?)"
                    fetched = db.execute(f"SELECT key, source_value, translated_value FROM entries WHERE {where} ORDER BY key LIMIT 500", (pattern, pattern, pattern)).fetchall()
                    total = db.execute(f"SELECT COUNT(*) FROM entries WHERE {where}", (pattern, pattern, pattern)).fetchone()[0]
                else:
                    where = f"WHERE {filter_sql}" if filter_sql else ""
                    fetched = db.execute(f"SELECT key, source_value, translated_value FROM entries {where} ORDER BY key LIMIT 500").fetchall()
                    total = db.execute(f"SELECT COUNT(*) FROM entries {where}").fetchone()[0]
            rows = [{"key": row["key"], "source": row["source_value"], "translation": row["translated_value"]} for row in fetched]
            self.send_json({"entries": rows, "total": total})
            return
        if parsed.path == "/api/blueprints":
            english, translations = parse_ini(GLOBAL), parse_ini(TRANSLATION)
            pools = json_file(POOLS)
            friendly_pools = {
                name: [item_label(item, english, translations) for item in body.get("item_refs", [])]
                for name, body in pools["pools"].items()
            }
            friendly_missions = {}
            for mission in pools["mission_pool_map"]:
                title_key = mission_title_key(mission, english)
                title = item_label(title_key, english, translations) if title_key else None
                description = item_label(mission, english, translations)
                friendly_missions[mission] = {"title_key": title_key, "title": title["label"] if title else None, "description": description["label"], "description_source": description["source"]}
            self.send_json({"pools": pools, "metadata": json_file(METADATA), "friendly_pools": friendly_pools, "friendly_missions": friendly_missions})
            return
        if parsed.path == "/api/items":
            term = parse_qs(parsed.query).get("q", [""])[0].casefold()
            with database() as db:
                rows = db.execute("SELECT key, source_value, translated_value FROM entries WHERE key LIKE 'item_%' AND (lower(key) LIKE ? OR lower(source_value) LIKE ? OR lower(translated_value) LIKE ?) ORDER BY key LIMIT 60", (f"%{term}%", f"%{term}%", f"%{term}%")).fetchall()
            self.send_json({"items": [{"key": row["key"], "label": row["translated_value"] or row["source_value"] or row["key"], "source": row["source_value"]} for row in rows]})
            return
        if parsed.path == "/api/components":
            term = parse_qs(parsed.query).get("q", [""])[0].casefold()
            with database() as db:
                pattern = f"%{term}%"
                rows = db.execute("""SELECT e.key, e.source_value, e.translated_value, c.component_type
                    FROM entries e LEFT JOIN component_overlays c ON c.key = e.key
                    WHERE e.key LIKE 'item_%' AND (lower(e.key) LIKE ? OR lower(e.source_value) LIKE ? OR lower(e.translated_value) LIKE ?)
                    ORDER BY c.component_type IS NULL, e.key LIMIT 100""", (pattern, pattern, pattern)).fetchall()
                types = [row[0].strip() for row in db.execute("SELECT DISTINCT component_type FROM component_overlays ORDER BY component_type").fetchall()]
            self.send_json({"entries": [{"key": row["key"], "label": row["translated_value"] or row["source_value"] or row["key"], "source": row["source_value"], "component_type": row["component_type"].strip() if row["component_type"] else ""} for row in rows], "types": types})
            return
        return super().do_GET()

    def do_POST(self) -> None:
        try:
            if self.path == "/api/entries":
                payload = self.body()
                key, value = payload["key"], payload["translation"]
                source = parse_ini(GLOBAL).get(key)
                if source is None:
                    raise ValueError("La clave no existe en el global.ini actual.")
                validate_tokens(source, value)
                update_ini_value(TRANSLATION, key, value)
                sync_database()
                return self.send_json({"ok": True})
            if self.path == "/api/translate-ai":
                payload = self.body()
                key = payload["key"]
                source = parse_ini(GLOBAL).get(key)
                if source is None:
                    raise ValueError("La clave no existe en el global.ini actual.")
                return self.send_json({"translation": ai_translation_proposal(source)})
            if self.path == "/api/blueprints":
                payload = self.body()
                pools = payload.get("pools")
                metadata = payload.get("metadata")
                if not isinstance(pools, dict) or not isinstance(pools.get("pools"), dict) or not isinstance(pools.get("mission_pool_map"), dict):
                    raise ValueError("El documento de pools debe incluir pools y mission_pool_map.")
                if not isinstance(metadata, dict) or not isinstance(metadata.get("title_meta"), dict) or not isinstance(metadata.get("description_meta"), dict):
                    raise ValueError("El documento de metadatos de misiones no es válido.")
                for mission, references in pools["mission_pool_map"].items():
                    refs = references if isinstance(references, list) else [references]
                    if not isinstance(mission, str) or not all(isinstance(ref, str) and ref in pools["pools"] for ref in refs):
                        raise ValueError("Cada enlace de misión debe referenciar pools existentes.")
                save_json(POOLS, pools)
                save_json(METADATA, metadata)
                sync_database()
                return self.send_json({"ok": True})
            if self.path == "/api/components":
                payload = self.body()
                key, component_type = payload["key"], payload["component_type"].strip()
                if key not in parse_ini(GLOBAL):
                    raise ValueError("La clave no existe en el global.ini actual.")
                if not component_type or "\n" in component_type or "\r" in component_type:
                    raise ValueError("Indica un tipo de componente en una sola línea.")
                update_ini_value(COMPONENTS, key, " " + component_type)
                sync_database()
                return self.send_json({"ok": True})
            if self.path == "/api/import-global":
                length = int(self.headers.get("Content-Length", "0"))
                uploaded = self.rfile.read(length)
                decoded = uploaded.decode("utf-8-sig")
                if not any("=" in line and not line.lstrip().startswith(("#", ";")) for line in decoded.splitlines()):
                    raise ValueError("El archivo importado no parece un global.ini válido.")
                backup = GLOBAL.with_suffix(".ini.previous")
                if GLOBAL.exists():
                    shutil.copy2(GLOBAL, backup)
                atomic_write(GLOBAL, decoded, "utf-8-sig" if uploaded.startswith(b"\xef\xbb\xbf") else "utf-8")
                sync_database()
                return self.send_json({"ok": True, "backup": str(backup.relative_to(ROOT))})
            if self.path == "/api/export":
                payload = self.body()
                language = payload.get("language", "es-es")
                if language != "es-es":
                    raise ValueError("Esta primera versión publica el idioma es-es.")
                version = VERSION.read_text(encoding="utf-8").strip() if VERSION.exists() else "dev"
                command = [sys.executable, "scripts/build_distributions.py", "--language", language, "--version", version]
                result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=300)
                if result.returncode:
                    raise RuntimeError(result.stderr or result.stdout or "La compilación no ha terminado correctamente.")
                return self.send_json({"ok": True, "output": result.stdout, "directory": f"dist/{version}"})
            self.send_error(HTTPStatus.NOT_FOUND)
        except (KeyError, TypeError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            self.send_json({"ok": False, "error": str(error)}, 400)


def main() -> None:
    sync_database()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), AppHandler)
    print("Panel disponible en http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
