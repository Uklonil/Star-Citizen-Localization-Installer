from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import REPO_ROOT
from blueprint_pool_source import default_blueprint_source_paths


DEFAULT_DISCOVERY_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_POOLS_DISCOVERY.json"


def minimal_pool_definition(pool_definition: dict[str, object]) -> dict[str, object]:
    if isinstance(pool_definition.get("variants"), list):
        return {"variants": pool_definition["variants"]}
    if isinstance(pool_definition.get("lines"), list):
        return {"lines": pool_definition["lines"]}
    item_refs = pool_definition.get("item_refs")
    if isinstance(item_refs, list):
        return {"item_refs": item_refs}
    raise ValueError("Definicion de pool invalida: falta `item_refs`, `lines` o `variants`")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Separa source/blueprints/pools.json en una fuente minima de build y un artefacto de discovery."
    )
    parser.add_argument("--pool-source")
    parser.add_argument("--discovery-output", default=str(DEFAULT_DISCOVERY_OUTPUT))
    args = parser.parse_args()

    _, default_pool_source = default_blueprint_source_paths(REPO_ROOT)
    pool_source_path = Path(args.pool_source).expanduser().resolve() if args.pool_source else default_pool_source.resolve()
    discovery_output_path = Path(args.discovery_output).expanduser().resolve()

    payload = json.loads(pool_source_path.read_text(encoding="utf-8-sig"))
    pools = payload.get("pools")
    mission_pool_map = payload.get("mission_pool_map")
    if not isinstance(pools, dict) or not isinstance(mission_pool_map, dict):
        raise ValueError(f"Fuente de pools invalida: {pool_source_path}")

    minimal_payload = {
        "version": payload.get("version", 1),
        "generated_from": payload.get("generated_from", {}),
        "notes": [
            "Fuente minima para generar recompensas visibles de blueprints.",
            "Cada entrada de `mission_pool_map` enlaza una clave `desc` del overlay con una pool reutilizable.",
        ],
        "pools": {
            pool_id: minimal_pool_definition(pool_definition)
            for pool_id, pool_definition in sorted(pools.items(), key=lambda item: item[0].lower())
        },
        "mission_pool_map": dict(sorted(mission_pool_map.items(), key=lambda item: item[0].lower())),
    }

    discovery_payload = {
        "version": payload.get("version", 1),
        "generated_from": payload.get("generated_from", {}),
        "notes": [
            "Artefacto auxiliar con contexto de discovery para revisar y refactorizar pools.",
            "No lo usa la build; la fuente efectiva es source/blueprints/pools.json.",
        ],
        "pools": {pool_id: pool_definition for pool_id, pool_definition in sorted(pools.items(), key=lambda item: item[0].lower())},
        "mission_pool_map": dict(sorted(mission_pool_map.items(), key=lambda item: item[0].lower())),
    }

    pool_source_path.write_text(json.dumps(minimal_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    discovery_output_path.parent.mkdir(parents=True, exist_ok=True)
    discovery_output_path.write_text(json.dumps(discovery_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Fuente minima escrita: {pool_source_path}")
    print(f"Discovery escrita: {discovery_output_path}")
    print(f"Pools: {len(pools)}")
    print(f"Mapeos de mision->pool: {len(mission_pool_map)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
