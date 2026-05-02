from __future__ import annotations

import json
import re
from pathlib import Path

from localization_tools import Entry, GlobalIniData, read_global_ini

POOL_TOKEN_RE = re.compile(r"@((?:BP_MISSIONREWARD|OVERLAY_)[A-Za-z0-9_]+(?:__\d+)?)@")
GENERIC_BLUEPRINT_BLOCK_PREFIX = "\\n\\n\\n\\n<EM4>##potential_blueprints##</EM4>\\n"


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


def _normalize_pool_refs(raw_value: object, *, context: str) -> list[str]:
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, list) and all(isinstance(item, str) for item in raw_value):
        return list(raw_value)
    raise ValueError(
        f"Valor invalido en {context}: se esperaba `str` o `list[str]`."
    )


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


def render_pool_sequence(pool_ids: list[str], *, pool_map: dict[str, dict]) -> str:
    rendered_blocks: list[str] = []
    for pool_id in pool_ids:
        pool_definition = pool_map.get(pool_id)
        if pool_definition is None:
            raise ValueError(f"Pool inexistente `{pool_id}`")

        variants = pool_definition.get("variants")
        if isinstance(variants, list):
            rendered_blocks.append(render_pool_variants(variants))
            continue

        lines = pool_definition.get("lines")
        if isinstance(lines, list):
            rendered_blocks.append(render_pool_lines(lines))
            continue

        item_refs = pool_definition.get("item_refs")
        if isinstance(item_refs, list):
            rendered_blocks.append(render_pool_item_block([str(item_ref) for item_ref in item_refs]))
            continue

        raise ValueError(f"Pool invalida `{pool_id}`: falta `item_refs`, `lines` o `variants`")

    return "\\n\\n".join(rendered_blocks)


def generate_blueprints_overlay_data(*, template_path: Path, pool_source_path: Path) -> GlobalIniData:
    template = read_global_ini(template_path)
    pool_source = _load_pool_source(pool_source_path)
    pools = pool_source["pools"]
    mission_pool_map = pool_source["mission_pool_map"]

    referenced_pool_ids = {
        pool_id
        for key, raw_value in mission_pool_map.items()
        for pool_id in _normalize_pool_refs(raw_value, context=f"`mission_pool_map[{key}]`")
    }
    unknown_pools = sorted(pool_id for pool_id in referenced_pool_ids if pool_id not in pools)
    if unknown_pools:
        sample = ", ".join(unknown_pools[:10])
        raise ValueError(
            f"El mapa de misiones referencia pools inexistentes en {pool_source_path}. Ejemplos: {sample}"
        )

    generated_entries: list[Entry] = []
    for entry in template.entries:
        raw_pool_refs = mission_pool_map.get(entry.key)
        pool_refs = (
            _normalize_pool_refs(raw_pool_refs, context=f"`mission_pool_map[{entry.key}]`")
            if raw_pool_refs is not None
            else []
        )
        for pool_id in pool_refs:
            pool_definition = pools[pool_id]
            if not isinstance(pool_definition, dict):
                raise ValueError(f"Definicion de pool invalida para `{pool_id}` en {pool_source_path}")

        rendered_value = resolve_pool_tokens(entry.value, pool_map=pools)
        if len(pool_refs) > 1:
            pool_token_count = len(POOL_TOKEN_RE.findall(entry.value))
            if pool_token_count <= 1:
                rendered_value = f"{GENERIC_BLUEPRINT_BLOCK_PREFIX}{render_pool_sequence(pool_refs, pool_map=pools)}"

        generated_entries.append(
            Entry(
                key=entry.key,
                value=rendered_value,
            )
        )

    generated_mapping = {entry.key: entry.value for entry in generated_entries}
    return GlobalIniData(entries=generated_entries, mapping=generated_mapping)


def write_ini_entries_plain(*, entries: list[Entry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for entry in entries:
            handle.write(f"{entry.key}={entry.value}\n")
