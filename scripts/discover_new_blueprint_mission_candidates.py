from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from scdatatools.sc import StarCitizen


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"
DEFAULT_GLOBAL = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_TEMPLATE = REPO_ROOT / "source" / "blueprints" / "blueprints_template.ini"
DEFAULT_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_NEW_MISSION_CANDIDATES.md"

POOL_RE = re.compile(rb"BP_MISSIONREWARD_[A-Za-z0-9_]+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class CandidateMission:
    title_key: str
    desc_key: str | None
    title_text: str
    family: str
    candidate_pools: list[str]


def read_ini_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw_line or raw_line.startswith((";", "#")) or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        mapping[key] = value
    return mapping


def replace_token(value: str, source_token: str, target_token: str) -> str:
    parts = value.split("_")
    replaced = False
    for index, part in enumerate(parts):
        if part.lower() == source_token.lower():
            parts[index] = target_token
            replaced = True
            break
    return "_".join(parts) if replaced else value


def has_token(value: str, token: str) -> bool:
    return any(part.lower() == token.lower() for part in value.split("_"))


def normalized_tokens(value: str) -> set[str]:
    parts = [part for part in NON_ALNUM_RE.split(value.lower()) if part]
    ignore = {
        "bp",
        "missionreward",
        "mission",
        "reward",
        "title",
        "desc",
        "description",
        "intro",
        "journal",
        "repui",
        "reputationjournal",
        "contract",
        "generic",
        "veryeasy",
        "easy",
        "medium",
        "hard",
        "veryhard",
        "super",
        "ve",
        "e",
        "m",
        "h",
        "vh",
        "s",
        "001",
        "002",
        "003",
    }
    return {part for part in parts if part not in ignore}


def family_name_from_title_key(title_key: str) -> str:
    key = replace_token(title_key, "title", "")
    key = replace_token(key, "desc", "")
    key = replace_token(key, "description", "")
    key = re.sub(r"_\d+$", "", key)
    key = re.sub(r"_0+\d+\b", "", key)
    return key.strip("_")


def extract_pools(sc_root: Path, cache_dir: Path) -> tuple[str, list[str]]:
    sc = StarCitizen(sc_root, cache_dir=cache_dir)
    for member in ("Data/Game.dcb", "Data/Game2.dcb"):
        try:
            raw = sc.p4k.getinfo(member).open("rb").read()
            pools = sorted({match.group(0).decode("ascii") for match in POOL_RE.finditer(raw)})
            return member, pools
        except KeyError:
            continue
    raise FileNotFoundError("No se encontro Data/Game.dcb ni Data/Game2.dcb en la instalacion.")


def top_pool_candidates(family: str, pools: list[str]) -> list[str]:
    family_tokens = normalized_tokens(family)
    ranked: list[tuple[int, str]] = []
    for pool in pools:
        overlap = len(family_tokens & normalized_tokens(pool))
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
                title_key=key,
                desc_key=desc_key,
                title_text=value,
                family=family,
                candidate_pools=candidate_pools,
            )
        )

    candidates.sort(key=lambda item: (item.family.lower(), item.title_key.lower()))
    return candidates


def build_report(
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
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detecta misiones candidatas a blueprints que existen en el parche pero aun no estan en el template."
    )
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--global-ini", default=str(DEFAULT_GLOBAL))
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    sc_root = Path(args.sc_root).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    global_path = Path(args.global_ini).expanduser().resolve()
    template_path = Path(args.template).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    global_map = read_ini_map(global_path)
    template_map = read_ini_map(template_path)
    dcb_member, pools = extract_pools(sc_root, cache_dir)
    candidates = collect_candidates(global_map=global_map, template_map=template_map, pools=pools)
    build_report(
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
