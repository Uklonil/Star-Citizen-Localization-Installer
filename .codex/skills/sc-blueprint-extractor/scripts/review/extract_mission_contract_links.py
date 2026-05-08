from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

CORE_SCRIPTS = Path(__file__).resolve().parents[1] / "core"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from dcb_text_support import build_title_index, load_raw_dcb, split_strings_with_offsets
from runtime_support import REPO_ROOT


DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"
DEFAULT_GLOBAL = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_TEMPLATE = REPO_ROOT / "source" / "blueprints" / "blueprints_template.ini"
DEFAULT_SHORTLIST = REPO_ROOT / "informes" / "BLUEPRINTS_NEW_MISSION_CANDIDATES_SHORTLIST.md"
DEFAULT_OUTPUT = REPO_ROOT / "informes" / "MISSION_CONTRACT_LINKS_FROM_GAME2.md"


@dataclass(frozen=True)
class MissionCandidate:
    title_key: str
    desc_key: str | None
    english_title: str
    in_template: bool


def read_ini_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw_line or raw_line.startswith((";", "#")) or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        mapping[key] = value
    return mapping


def collect_mission_candidates(global_map: dict[str, str], template_map: dict[str, str]) -> list[MissionCandidate]:
    candidates: list[MissionCandidate] = []
    seen: set[str] = set()
    for key, value in global_map.items():
        lower = key.lower()
        if "title" not in lower:
            continue
        if key in seen:
            continue
        desc_key = key.replace("Title", "Desc").replace("title", "desc")
        if desc_key == key:
            desc_key = None
        candidates.append(
            MissionCandidate(
                title_key=key,
                desc_key=desc_key if desc_key in global_map else None,
                english_title=value,
                in_template=key in template_map,
            )
        )
        seen.add(key)
    return candidates


def parse_shortlist_title_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.startswith("| `"):
            continue
        parts = [part.strip() for part in raw_line.strip("|").split("|")]
        if len(parts) != 5:
            continue
        title_key = parts[1].strip("`")
        keys.add(title_key)
    return keys


def classify_string(value: str) -> bool:
    lower = value.lower()
    return (
        value.startswith("@")
        or value.startswith("ContractGenerator.")
        or value.startswith("BlueprintPoolRecord.")
        or "contractgenerator/" in lower
        or "missiondata/" in lower
    )


def find_context(
    strings: list[tuple[int, str]],
    title_index: dict[str, int],
    *,
    title_key: str,
    window: int = 12000,
) -> tuple[int, list[str]]:
    offset = title_index.get(title_key, -1)
    if offset == -1:
        return -1, []
    start = offset - window
    end = offset + window
    context = [text for pos, text in strings if start <= pos <= end and classify_string(text)]
    return offset, context


def build_report(
    *,
    global_map: dict[str, str],
    template_map: dict[str, str],
    strings: list[tuple[int, str]],
    title_keys_filter: set[str] | None,
    output_path: Path,
) -> str:
    candidates = collect_mission_candidates(global_map, template_map)
    if title_keys_filter:
        candidates = [candidate for candidate in candidates if candidate.title_key in title_keys_filter]
    title_index = build_title_index(strings)
    rows: list[tuple[MissionCandidate, int, list[str]]] = []
    for candidate in candidates:
        offset, context = find_context(strings, title_index, title_key=candidate.title_key)
        if offset == -1:
            continue
        if any(
            token.startswith("ContractGenerator.")
            or "contractgenerator/" in token.lower()
            or "missiondata/" in token.lower()
            for token in context
        ):
            rows.append((candidate, offset, context))

    lines: list[str] = []
    lines.append("# Mission links from Game2.dcb")
    lines.append("")
    lines.append("Objetivo:")
    lines.append("- Extraer desde `Game2.dcb` el contexto textual local de cada mision con `title`.")
    lines.append("- Identificar enlaces visibles a `ContractGenerator.*`, rutas `contractgenerator/*.xml` y `missiondata/*.xml`.")
    lines.append("- No asigna pools: deja la traza cruda del juego para enlazar `mision -> contrato -> pool`.")
    lines.append("")
    lines.append("Resumen:")
    lines.append(f"- Misiones con `title` detectadas en `global.ini`: {len(candidates)}")
    lines.append(f"- Misiones con contexto de contrato detectable en `Game2.dcb`: {len(rows)}")
    lines.append(f"- Misiones ya presentes en `blueprints_template.ini`: {sum(1 for candidate, _, _ in rows if candidate.in_template)}")
    lines.append(f"- Misiones fuera del template actual: {sum(1 for candidate, _, _ in rows if not candidate.in_template)}")
    lines.append("")

    for candidate, offset, context in rows:
        lines.append(f"## {candidate.english_title}")
        lines.append("")
        lines.append(f"- `title`: `{candidate.title_key}`")
        lines.append(f"- `desc`: `{candidate.desc_key}`" if candidate.desc_key else "- `desc`: `n/d`")
        lines.append(f"- En template actual: `{'si' if candidate.in_template else 'no'}`")
        lines.append(f"- Offset texto `Game2.dcb`: `{offset}`")
        lines.append("")
        lines.append("```text")
        for token in context[:80]:
            lines.append(token)
        lines.append("```")
        lines.append("")

    report = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrae enlaces de mision a contrato visibles en Game2.dcb.")
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--global-ini", default=str(DEFAULT_GLOBAL))
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    sc_root = Path(args.sc_root).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    global_ini = Path(args.global_ini).expanduser().resolve()
    template = Path(args.template).expanduser().resolve()
    shortlist = Path(args.shortlist).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    global_map = read_ini_map(global_ini)
    template_map = read_ini_map(template)
    title_keys_filter = parse_shortlist_title_keys(shortlist) if shortlist.is_file() else None
    _dcb_member, raw = load_raw_dcb(sc_root=sc_root, cache_dir=cache_dir)
    strings = split_strings_with_offsets(raw)
    build_report(
        global_map=global_map,
        template_map=template_map,
        strings=strings,
        title_keys_filter=title_keys_filter,
        output_path=output,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
