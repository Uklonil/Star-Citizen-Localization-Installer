from __future__ import annotations

import argparse
from pathlib import Path
import sys

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from runtime_support import REPO_ROOT
from blueprint_pool_source import (
    default_blueprint_source_paths,
    generate_blueprints_overlay_data,
    write_ini_entries_plain,
)


DEFAULT_OUTPUT = REPO_ROOT / "source" / "shared" / "overlays" / "blueprints.ini"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera source/shared/overlays/blueprints.ini a partir de la fuente estructurada de pools."
    )
    parser.add_argument("--template")
    parser.add_argument("--pool-source")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    default_template, default_pool_source = default_blueprint_source_paths(REPO_ROOT)
    template_path = Path(args.template).expanduser().resolve() if args.template else default_template.resolve()
    pool_source_path = (
        Path(args.pool_source).expanduser().resolve() if args.pool_source else default_pool_source.resolve()
    )
    output_path = Path(args.output).expanduser().resolve()

    generated = generate_blueprints_overlay_data(
        template_path=template_path,
        pool_source_path=pool_source_path,
    )
    write_ini_entries_plain(entries=generated.entries, output_path=output_path)

    print(f"Overlay generado: {output_path}")
    print(f"Entradas: {len(generated.entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
