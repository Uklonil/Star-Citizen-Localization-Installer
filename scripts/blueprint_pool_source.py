from __future__ import annotations

import json
import re
from pathlib import Path

from localization_tools import Entry, GlobalIniData, read_global_ini

POOL_TOKEN_RE = re.compile(r"@((?:BP_MISSIONREWARD|OVERLAY_)[A-Za-z0-9_]+(?:__\d+)?)@")


def default_blueprint_source_paths(repo_root: Path) -> tuple[Path, Path]:
    source_root = repo_root / "source" / "blueprints"
    return source_root / "blueprints_template.ini", source_root / "pools.json"


def _load_pool_source(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(f"Fuente de pools invalida: {path}")

    pools = payload.get("pools")
    mission_pool_map = payload.get("mission_pool_map")
    if not isinstance(pools, dict) or not isinstance(mission_pool_map, dict):
        raise ValueError(f"Faltan `pools` o `mission_pool_map` en {path}")

    return payload


def render_pool_item_block(item_refs: list[str]) -> str:
    return "\\n".join(f"- @{item_ref}@" for item_ref in item_refs)


def render_pool_lines(lines: list[str]) -> str:
    return "\\n".join(str(line) for line in lines)


def render_pool_variants(variants: list[dict]) -> str:
    rendered_variants: list[str] = []

    for index, variant in enumerate(variants):
        if not isinstance(variant, dict):
            raise ValueError(f"Variante invalida en posicion {index}: se esperaba un objeto")

        header_token = variant.get("header_token")
        header_value = variant.get("header_value")
        lines = variant.get("lines")
        item_refs = variant.get("item_refs")

        rendered_lines: list[str] = []
        if isinstance(header_token, str) and isinstance(header_value, str):
            rendered_lines.append(f"<EM4>##{header_token}## {header_value}</EM4>")
        elif header_token is not None or header_value is not None:
            raise ValueError(
                f"Variante invalida en posicion {index}: `header_token` y `header_value` deben aparecer juntos"
            )

        if isinstance(lines, list):
            rendered_lines.extend(str(line) for line in lines)
        elif isinstance(item_refs, list):
            rendered_lines.extend(f"- @{item_ref}@" for item_ref in item_refs)
        else:
            raise ValueError(
                f"Variante invalida en posicion {index}: falta `lines` o `item_refs`"
            )

        rendered_variants.append("\\n".join(rendered_lines))

    return "\\n\\n".join(rendered_variants)


def resolve_pool_tokens(value: str, *, pool_map: dict[str, dict]) -> str:
    def replace(match: re.Match[str]) -> str:
        pool_id = match.group(1)
        pool_definition = pool_map.get(pool_id)
        if pool_definition is None:
            return match.group(0)

        variants = pool_definition.get("variants")
        if isinstance(variants, list):
            return render_pool_variants(variants)

        lines = pool_definition.get("lines")
        if isinstance(lines, list):
            return render_pool_lines(lines)

        item_refs = pool_definition.get("item_refs")
        if isinstance(item_refs, list):
            return render_pool_item_block([str(item_ref) for item_ref in item_refs])

        raise ValueError(f"Pool invalida `{pool_id}`: falta `item_refs`, `lines` o `variants`")

    return POOL_TOKEN_RE.sub(replace, value)


def generate_blueprints_overlay_data(*, template_path: Path, pool_source_path: Path) -> GlobalIniData:
    template = read_global_ini(template_path)
    pool_source = _load_pool_source(pool_source_path)
    pools = pool_source["pools"]
    mission_pool_map = pool_source["mission_pool_map"]

    unknown_pools = sorted(
        {pool_id for pool_id in mission_pool_map.values() if pool_id not in pools}
    )
    if unknown_pools:
        sample = ", ".join(unknown_pools[:10])
        raise ValueError(
            f"El mapa de misiones referencia pools inexistentes en {pool_source_path}. Ejemplos: {sample}"
        )

    generated_entries: list[Entry] = []
    for entry in template.entries:
        pool_id = mission_pool_map.get(entry.key)
        if pool_id is not None:
            pool_definition = pools[pool_id]
            if not isinstance(pool_definition, dict):
                raise ValueError(f"Definicion de pool invalida para `{pool_id}` en {pool_source_path}")

        generated_entries.append(
            Entry(
                key=entry.key,
                value=resolve_pool_tokens(entry.value, pool_map=pools),
            )
        )

    generated_mapping = {entry.key: entry.value for entry in generated_entries}
    return GlobalIniData(entries=generated_entries, mapping=generated_mapping)


def write_ini_entries_plain(*, entries: list[Entry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for entry in entries:
            handle.write(f"{entry.key}={entry.value}\n")
