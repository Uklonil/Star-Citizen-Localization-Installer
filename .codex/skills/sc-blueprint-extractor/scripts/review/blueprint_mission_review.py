from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from review_support import (
    DEFAULT_CACHE_DIR,
    DEFAULT_SC_ROOT,
    REPO_ROOT,
    extract_pools,
    family_name_from_title_key,
    has_token,
    normalized_tokens,
    read_ini_map,
    replace_token,
)


DEFAULT_GLOBAL = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_TEMPLATE = REPO_ROOT / "source" / "blueprints" / "blueprints_template.ini"
DEFAULT_DISCOVERY_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_NEW_MISSION_CANDIDATES.md"
DEFAULT_SHORTLIST_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_NEW_MISSION_CANDIDATES_SHORTLIST.md"

MISSION_IGNORE_TOKENS = {
    "bp", "missionreward", "mission", "reward", "title", "desc", "description",
    "intro", "journal", "repui", "reputationjournal", "contract", "generic",
    "veryeasy", "easy", "medium", "hard", "veryhard", "super", "ve", "e",
    "m", "h", "vh", "s", "001", "002", "003",
}
SHORTLIST_EXCLUDED_TOKENS = (
    "Certification",
    "ReputationJournal",
    "RepUI",
    "Journal",
)


@dataclass(frozen=True)
class CandidateMission:
    family: str
    title_key: str
    desc_key: str | None
    title_text: str
    candidate_pools: list[str]


def top_pool_candidates(family: str, pools: list[str]) -> list[str]:
    family_tokens = normalized_tokens(family, ignore=MISSION_IGNORE_TOKENS)
    ranked: list[tuple[int, str]] = []
    for pool in pools:
        overlap = len(family_tokens & normalized_tokens(pool, ignore=MISSION_IGNORE_TOKENS))
        if overlap <= 0:
            continue
        ranked.append((overlap, pool))
    ranked.sort(key=lambda item: (-item[0], item[1].lower()))
    return [pool for _, pool in ranked[:5]]


def collect_candidates(*, global_map: dict[str, str], template_map: dict[str, str], pools: list[str]) -> list[CandidateMission]:
    global_lower_to_real = {key.lower(): key for key in global_map}
    template_lower = {key.lower() for key in template_map}
    candidates: list[CandidateMission] = []
    seen_titles: set[str] = set()

    for key, value in global_map.items():
        if not has_token(key, "title"):
            continue
        lower_key = key.lower()
        if lower_key in seen_titles:
            continue
        seen_titles.add(lower_key)

        desc_key_guess = replace_token(key, "title", "desc")
        desc_key = global_lower_to_real.get(desc_key_guess.lower())
        title_in_template = lower_key in template_lower
        desc_in_template = desc_key is not None and desc_key.lower() in template_lower
        if title_in_template or desc_in_template:
            continue

        family = family_name_from_title_key(key)
        candidate_pools = top_pool_candidates(family, pools)
        if not candidate_pools:
            continue

        candidates.append(
            CandidateMission(
                family=family,
                title_key=key,
                desc_key=desc_key,
                title_text=value,
                candidate_pools=candidate_pools,
            )
        )

    candidates.sort(key=lambda item: (item.family.lower(), item.title_key.lower()))
    return candidates


def build_discovery_report(
    *,
    output_path: Path,
    global_path: Path,
    template_path: Path,
    sc_root: Path,
    dcb_member: str,
    pools: list[str],
    candidates: list[CandidateMission],
) -> None:
    families = sorted({candidate.family for candidate in candidates})
    lines: list[str] = []
    lines.append("# Candidatas nuevas de blueprints por mision")
    lines.append("")
    lines.append("Objetivo:")
    lines.append("- Detectar misiones presentes en el `global.ini` actual pero ausentes del template actual de blueprints.")
    lines.append("- Proponer pools candidatas a partir de similitud de tokens con `BP_MISSIONREWARD_*` detectadas en el juego.")
    lines.append("")
    lines.append("Origenes usados:")
    lines.append(f"- `global.ini`: `{global_path.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- Template blueprints: `{template_path.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- Instalacion de Star Citizen: `{sc_root}`")
    lines.append(f"- DataForge detectado: `{dcb_member}`")
    lines.append("")
    lines.append("Notas:")
    lines.append("- Este informe parte del parche actual, no del overlay ya existente.")
    lines.append("- Las pools candidatas son heuristicas; no implican enlace autoritativo desde DataForge.")
    lines.append("- Solo se incluyen familias con alguna coincidencia por tokens contra `BP_MISSIONREWARD_*`.")
    lines.append("")
    lines.append("Resumen:")
    lines.append(f"- Pools detectadas en DataForge: {len(pools)}")
    lines.append(f"- Misiones candidatas ausentes del template actual: {len(candidates)}")
    lines.append(f"- Familias detectadas: {len(families)}")
    lines.append("")
    lines.append("## Candidatas")
    lines.append("")
    lines.append("| Familia | Clave `title` | Clave `desc` | Titulo ingles | Pools candidatas |")
    lines.append("|---|---|---|---|---|")
    for candidate in candidates:
        desc_key = f"`{candidate.desc_key}`" if candidate.desc_key is not None else "`-`"
        pools_text = "<br>".join(f"`{pool}`" for pool in candidate.candidate_pools)
        title_text = candidate.title_text.replace("|", "\\|")
        lines.append(
            f"| `{candidate.family}` | `{candidate.title_key}` | {desc_key} | {title_text} | {pools_text} |"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_candidate_rows(lines: list[str]) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for raw_line in lines:
        if not raw_line.startswith("| `"):
            continue
        parts = [part.strip() for part in raw_line.strip().strip("|").split("|")]
        if len(parts) != 5:
            continue
        rows.append(tuple(parts))  # type: ignore[arg-type]
    return rows


def shortlist_rows(candidates: list[CandidateMission]) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for candidate in candidates:
        desc_key = candidate.desc_key or "-"
        haystack = f"{candidate.title_key} {desc_key}"
        if desc_key == "-":
            continue
        if any(token.lower() in haystack.lower() for token in SHORTLIST_EXCLUDED_TOKENS):
            continue
        rows.append(
            (
                f"`{candidate.family}`",
                f"`{candidate.title_key}`",
                f"`{desc_key}`",
                candidate.title_text.replace("|", "\\|"),
                "<br>".join(f"`{pool}`" for pool in candidate.candidate_pools),
            )
        )
    return rows


def build_shortlist_report(*, output_path: Path, source_name: str, rows: list[tuple[str, str, str, str, str]]) -> None:
    families = {row[0] for row in rows}
    out_lines = [
        "# Shortlist de misiones nuevas candidatas a blueprints",
        "",
        "Criterio:",
        f"- Sale del informe `{source_name}`.",
        "- Solo incluye entradas con `desc` presente en `global.ini`.",
        "- Excluye certificaciones, reputation journals y otros textos de progresion no jugables.",
        "",
        "Resumen:",
        f"- Entradas shortlist: {len(rows)}",
        f"- Familias shortlist: {len(families)}",
        "",
        "| Familia | Clave `title` | Clave `desc` | Titulo ingles | Pools candidatas |",
        "|---|---|---|---|---|",
    ]
    out_lines.extend(f"| {' | '.join(row)} |" for row in rows)
    out_lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(out_lines), encoding="utf-8", newline="\n")


def run_discovery(
    *,
    sc_root: Path,
    cache_dir: Path,
    global_path: Path,
    template_path: Path,
    output_path: Path,
) -> list[CandidateMission]:
    global_map = read_ini_map(global_path)
    template_map = read_ini_map(template_path)
    dcb_member, pools = extract_pools(sc_root, cache_dir)
    candidates = collect_candidates(global_map=global_map, template_map=template_map, pools=pools)
    build_discovery_report(
        output_path=output_path,
        global_path=global_path,
        template_path=template_path,
        sc_root=sc_root,
        dcb_member=dcb_member,
        pools=pools,
        candidates=candidates,
    )
    print(f"Informe generado: {output_path}")
    print(f"Pools detectadas: {len(pools)}")
    print(f"Candidatas nuevas: {len(candidates)}")
    return candidates


def run_shortlist(
    *,
    input_path: Path | None,
    output_path: Path,
    candidates: list[CandidateMission] | None = None,
) -> list[tuple[str, str, str, str, str]]:
    if candidates is not None:
        rows = shortlist_rows(candidates)
        source_name = DEFAULT_DISCOVERY_OUTPUT.name if input_path is None else input_path.name
    else:
        if input_path is None:
            raise ValueError("Se requiere `input_path` cuando no se pasan candidatas en memoria.")
        lines = input_path.read_text(encoding="utf-8").splitlines()
        parsed_rows = parse_candidate_rows(lines)
        rows = []
        for row in parsed_rows:
            title_key = row[1].strip("`")
            desc_key = row[2].strip("`")
            haystack = f"{title_key} {desc_key}"
            if desc_key == "-":
                continue
            if any(token.lower() in haystack.lower() for token in SHORTLIST_EXCLUDED_TOKENS):
                continue
            rows.append(row)
        source_name = input_path.name

    build_shortlist_report(output_path=output_path, source_name=source_name, rows=rows)
    print(f"Shortlist generada: {output_path}")
    print(f"Entradas: {len(rows)}")
    print(f"Familias: {len({row[0] for row in rows})}")
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Consolida descubrimiento y shortlist de misiones nuevas candidatas a blueprints."
    )
    parser.add_argument("--mode", choices=("discover", "shortlist", "both"), default="both")
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--global-ini", default=str(DEFAULT_GLOBAL))
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--input", default=str(DEFAULT_DISCOVERY_OUTPUT))
    parser.add_argument("--output", default=str(DEFAULT_DISCOVERY_OUTPUT))
    parser.add_argument("--shortlist-output", default=str(DEFAULT_SHORTLIST_OUTPUT))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sc_root = Path(args.sc_root).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    global_path = Path(args.global_ini).expanduser().resolve()
    template_path = Path(args.template).expanduser().resolve()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    shortlist_output = Path(args.shortlist_output).expanduser().resolve()

    candidates: list[CandidateMission] | None = None
    if args.mode in {"discover", "both"}:
        candidates = run_discovery(
            sc_root=sc_root,
            cache_dir=cache_dir,
            global_path=global_path,
            template_path=template_path,
            output_path=output_path,
        )

    if args.mode in {"shortlist", "both"}:
        shortlist_input = None if candidates is not None and args.mode == "both" else input_path
        run_shortlist(
            input_path=shortlist_input,
            output_path=shortlist_output,
            candidates=candidates,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
