from __future__ import annotations

import json

from installer import installer_core
from scripts.language_support import discover_staged_languages


def test_http_get_json_accepts_utf8_bom(monkeypatch) -> None:
    payload = {"version": "1.0.0", "languages": {}}
    raw = json.dumps(payload).encode("utf-8-sig")

    monkeypatch.setattr(installer_core, "_http_get_bytes", lambda url: raw)

    assert installer_core._http_get_json("https://example.invalid/manifest.json") == payload


def test_read_cached_manifest_accepts_utf8_bom(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    payload = {"version": "1.0.0", "languages": {}}
    manifest_path.write_text(json.dumps(payload), encoding="utf-8-sig")

    assert installer_core._read_cached_manifest(manifest_path) == payload


def test_read_bundle_version_accepts_utf8_bom(tmp_path) -> None:
    metadata_dir = tmp_path / "_metadata"
    metadata_dir.mkdir()
    (metadata_dir / "version.txt").write_text("4.8.0-ptu.11768487", encoding="utf-8-sig")

    assert installer_core.read_bundle_version(tmp_path) == "4.8.0-ptu.11768487"


def test_discover_staged_languages_accepts_utf8_bom(tmp_path) -> None:
    metadata_dir = tmp_path / "es-es" / "_metadata"
    metadata_dir.mkdir(parents=True)
    payload = {
        "code": "es-es",
        "label": "Espanol (Espana)",
        "game_language": "spanish_(spain)",
    }
    (metadata_dir / "language.json").write_text(json.dumps(payload), encoding="utf-8-sig")

    languages = discover_staged_languages(tmp_path)

    assert len(languages) == 1
    assert languages[0].code == "es-es"
    assert languages[0].label == "Espanol (Espana)"
    assert languages[0].game_language == "spanish_(spain)"
