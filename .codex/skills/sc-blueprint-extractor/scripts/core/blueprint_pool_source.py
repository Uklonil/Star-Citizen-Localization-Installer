from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from runtime_support import REPO_ROOT

REPO_SCRIPTS = REPO_ROOT / "scripts"
if str(REPO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REPO_SCRIPTS))

from localization_tools import Entry, GlobalIniData, read_global_ini

POOL_TOKEN_RE = re.compile(r"@((?:BP_MISSIONREWARD|BP_REWARDS|OVERLAY_)[A-Za-z0-9_]+(?:__\d+)?)@")
GENERIC_BLUEPRINT_BLOCK_PREFIX = "\\n\\n\\n\\n<EM4>##potential_blueprints##</EM4>\\n"
TITLE_BP_BLOCK_RE = re.compile(r"<EM4>\[BP\]</EM4>")

TIER_LABEL_TO_TOKEN = {
    "neutral": "awarded_in_neutral_rank_variants",
    "master": "awarded_in_master_rank_variants",
    "jr. contractor": "awarded_in_junior_contractor_rank_variants",
    "junior contractor": "awarded_in_junior_contractor_rank_variants",
    "senior contractor": "awarded_in_senior_contractor_rank_variants",
    "sr. contractor": "awarded_in_senior_contractor_rank_variants",
    "contractor": "awarded_in_contractor_rank_variants",
    "head contractor": "awarded_in_lead_contractor_rank_variants",
    "lead contractor": "awarded_in_lead_contractor_rank_variants",
    "veteran contractor": "awarded_in_veteran_contractor_rank_variants",
    "applicant": "awarded_in_applicant_rank_variants",
    "rookie": "awarded_in_rookie_rank_variants",
    "security trainee": "awarded_in_security_trainee_rank_variants",
    "probationary guild member": "awarded_in_probationary_guild_member_rank_variants",
    "jr. security contractor": "awarded_in_junior_security_contractor_rank_variants",
    "junior security contractor": "awarded_in_junior_security_contractor_rank_variants",
    "elite contractor": "awarded_in_elite_contractor_rank_variants",
    "security contractor": "awarded_in_security_contractor_rank_variants",
    "high value assassin": "awarded_in_high_value_assassin_rank_variants",
    "elite assassin": "awarded_in_elite_assassin_rank_variants",
    "low level assassin": "awarded_in_low_level_assassin_rank_variants",
    "sr. security contractor": "awarded_in_senior_security_contractor_rank_variants",
    "senior security contractor": "awarded_in_senior_security_contractor_rank_variants",
    "trainee": "awarded_in_trainee_rank_variants",
}


def default_blueprint_source_paths(repo_root: Path) -> tuple[Path, Path]:
    source_root = repo_root / "source" / "blueprints"
    return source_root / "blueprints_template.ini", source_root / "pools.json"


def default_contract_metadata_source_path(repo_root: Path) -> Path:
    return repo_root / "source" / "blueprints" / "contracts_metadata.json"


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


def load_contract_metadata_source(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(f"Fuente de metadatos de contratos invalida: {path}")

    title_meta = payload.get("title_meta")
    description_meta = payload.get("description_meta")
    if not isinstance(title_meta, dict) or not isinstance(description_meta, dict):
        raise ValueError(f"Faltan `title_meta` o `description_meta` en {path}")

    return payload


def _normalize_pool_refs(raw_value: object, *, context: str) -> list[str]:
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, list) and all(isinstance(item, str) for item in raw_value):
        return list(raw_value)
    raise ValueError(
        f"Valor invalido en {context}: se esperaba `str` o `list[str]`."
    )


def _normalize_contract_metadata_key(key: str) -> str:
    return key.split(",", 1)[0]


def _title_suffix_from_metadata(
    title_meta: dict[str, object],
    *,
    existing_value: str,
    include_rep: bool,
    include_blueprint_flag: bool,
) -> str:
    rep_ranges = [str(item) for item in title_meta.get("rep_ranges", []) if str(item)]
    blueprint_flag = bool(title_meta.get("blueprint_flag"))
    blueprint_flag_uncertain = bool(title_meta.get("blueprint_flag_uncertain"))
    parts: list[str] = []
    if include_rep:
        if rep_ranges:
            parts.append("<EM2>" + " ".join(f"[{rep} Rep]" for rep in rep_ranges) + "</EM2>")
    if include_blueprint_flag and (blueprint_flag or blueprint_flag_uncertain):
        parts.append(f"<EM4>{'[BP]*' if blueprint_flag_uncertain else '[BP]'}</EM4>")
    if not parts:
        return existing_value
    rendered = " " + " ".join(parts)

    if TITLE_BP_BLOCK_RE.search(existing_value):
        return TITLE_BP_BLOCK_RE.sub(rendered.strip(), existing_value)
    return rendered


def _description_reputation_lines(desc_meta: dict[str, object], *, existing_value: str) -> list[str]:
    lines: list[str] = []

    reputation_awarded = [str(item) for item in desc_meta.get("reputation_awarded", []) if str(item)]
    if reputation_awarded and "##reputation_awarded##" not in existing_value and "##reputation_awarded_by_difficulty##" not in existing_value:
        token = "reputation_awarded_by_difficulty" if any("/" in value for value in reputation_awarded) else "reputation_awarded"
        lines.append(f"<EM2>##{token}##:</EM2> {' / '.join(reputation_awarded)}")

    return lines


def _description_blueprint_metadata_lines(desc_meta: dict[str, object], *, existing_value: str) -> list[str]:
    lines: list[str] = []

    scenario_progress_points = [str(item) for item in desc_meta.get("scenario_progress_points", []) if str(item)]
    if scenario_progress_points and "##scenario_progress_points##" not in existing_value:
        lines.append(f"<EM4>##scenario_progress_points##:</EM4> {' / '.join(scenario_progress_points)}")

    tier_labels = [str(item).strip() for item in desc_meta.get("tier_labels", []) if str(item).strip()]
    if tier_labels and "##awarded_in_" not in existing_value:
        for tier_label in tier_labels:
            token = TIER_LABEL_TO_TOKEN.get(tier_label.lower())
            if token is None:
                continue
            lines.append(f"<EM4>##{token}##</EM4>")

    return lines


def _apply_contract_metadata(
    *,
    entry_key: str,
    value: str,
    contract_metadata: dict | None,
    include_title_rep: bool = True,
    include_title_blueprint_flag: bool = True,
    include_description_reputation: bool = True,
    include_description_blueprint_metadata: bool = True,
) -> str:
    if contract_metadata is None:
        return value

    title_meta = contract_metadata.get("title_meta", {})
    description_meta = contract_metadata.get("description_meta", {})
    normalized_key = _normalize_contract_metadata_key(entry_key)

    enriched_value = value
    title_payload = title_meta.get(entry_key) or title_meta.get(normalized_key)
    if isinstance(title_payload, dict):
        enriched_value = _title_suffix_from_metadata(
            title_payload,
            existing_value=enriched_value,
            include_rep=include_title_rep,
            include_blueprint_flag=include_title_blueprint_flag,
        )

    desc_payload = description_meta.get(entry_key) or description_meta.get(normalized_key)
    if not isinstance(desc_payload, dict):
        return enriched_value

    metadata_lines: list[str] = []
    if include_description_reputation:
        metadata_lines.extend(_description_reputation_lines(desc_payload, existing_value=enriched_value))
    if include_description_blueprint_metadata:
        metadata_lines.extend(_description_blueprint_metadata_lines(desc_payload, existing_value=enriched_value))
    if not metadata_lines:
        return enriched_value

    if "##potential_blueprints##" in enriched_value:
        insertion = "\\n\\n" + "\\n".join(metadata_lines) + "\\n\\n"
        return enriched_value.replace("<EM4>##potential_blueprints##</EM4>", insertion + "<EM4>##potential_blueprints##</EM4>", 1)

    prefix = "\\n\\n" if enriched_value else ""
    return enriched_value + prefix + "\\n".join(metadata_lines)


def generate_reputation_overlay_data(*, contract_metadata_path: Path) -> GlobalIniData:
    contract_metadata = load_contract_metadata_source(contract_metadata_path)
    metadata_keys = set(contract_metadata.get("title_meta", {})) | set(contract_metadata.get("description_meta", {}))

    generated_entries: list[Entry] = []
    for entry_key in sorted(metadata_keys):
        rendered_value = _apply_contract_metadata(
            entry_key=entry_key,
            value="",
            contract_metadata=contract_metadata,
            include_title_rep=True,
            include_title_blueprint_flag=False,
            include_description_reputation=True,
            include_description_blueprint_metadata=False,
        )
        if not rendered_value:
            continue
        generated_entries.append(Entry(key=entry_key, value=rendered_value))

    generated_mapping = {entry.key: entry.value for entry in generated_entries}
    return GlobalIniData(entries=generated_entries, mapping=generated_mapping)


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
    contract_metadata_path = default_contract_metadata_source_path(REPO_ROOT)
    contract_metadata = (
        load_contract_metadata_source(contract_metadata_path)
        if contract_metadata_path.exists()
        else None
    )

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
    generated_keys: set[str] = set()
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
        rendered_value = _apply_contract_metadata(
            entry_key=entry.key,
            value=rendered_value,
            contract_metadata=contract_metadata,
            include_title_rep=False,
            include_title_blueprint_flag=True,
            include_description_reputation=False,
            include_description_blueprint_metadata=True,
        )

        generated_entries.append(
            Entry(
                key=entry.key,
                value=rendered_value,
            )
        )
        generated_keys.add(entry.key)

    if contract_metadata is not None:
        metadata_keys = set(contract_metadata.get("title_meta", {})) | set(contract_metadata.get("description_meta", {}))
        for entry_key in sorted(metadata_keys):
            if entry_key in generated_keys:
                continue

            rendered_value = _apply_contract_metadata(
                entry_key=entry_key,
                value="",
                contract_metadata=contract_metadata,
                include_title_rep=False,
                include_title_blueprint_flag=True,
                include_description_reputation=False,
                include_description_blueprint_metadata=True,
            )
            if not rendered_value:
                continue

            generated_entries.append(
                Entry(
                    key=entry_key,
                    value=rendered_value,
                )
            )
            generated_keys.add(entry_key)

    generated_mapping = {entry.key: entry.value for entry in generated_entries}
    return GlobalIniData(entries=generated_entries, mapping=generated_mapping)


def write_ini_entries_plain(*, entries: list[Entry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for entry in entries:
            handle.write(f"{entry.key}={entry.value}\n")
