from __future__ import annotations

import argparse
import ctypes
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from scdatatools.sc import StarCitizen
from scdatatools.forge import dftypes
from scdatatools.forge.dftypes.enums import DataTypes


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SC_ROOT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE")
DEFAULT_REPORT = REPO_ROOT / "informes" / "BLUEPRINTS_TITLE_WITHOUT_DESC_REPORT.md"
DEFAULT_OUTPUT = REPO_ROOT / "informes" / "BLUEPRINTS_MISSION_REWARDS_REPORT.md"
DEFAULT_BLUEPRINTS_EN = REPO_ROOT / "source" / "shared" / "overlays" / "blueprints.ini"
DEFAULT_BLUEPRINTS_ES = REPO_ROOT / "source" / "shared" / "overlays" / "blueprints.ini"
DEFAULT_GLOBAL_EN = REPO_ROOT / "input" / "current" / "global.ini"
DEFAULT_CACHE_DIR = REPO_ROOT / ".scdt-cache"

ITEM_REF_RE = re.compile(r"@(item_[A-Za-z0-9_.,-]+)@")
REPORT_ROW_RE = re.compile(
    r"^\|\s*`(?P<title>[^`]+)`\s*\|\s*`(?P<desc>[^`]+)`\s*\|\s*`(?P<english>[^`]+)`\s*\|$"
)


@dataclass(frozen=True)
class MissionEntry:
    title_key: str
    desc_key: str
    english_title: str


@dataclass(frozen=True)
class DatacoreProbeResult:
    dcb_path: str | None
    status: str
    title_key_in_binary: bool
    desc_key_in_binary: bool
    english_title_in_binary: bool
    note: str | None = None


@dataclass(frozen=True)
class DatacoreSession:
    dcb_path: str | None
    status: str
    binary: bytes | None
    note: str | None = None


class DataCoreBinaryCompat:
    """Best-effort parser for current Game2.dcb layouts.

    Current local builds ship `Data/Game2.dcb`, whose layout leaves trailing bytes
    that make the upstream `DataCoreBinary` assert at the end of parsing.
    We keep the same parser structure but tolerate extra trailing bytes so we can
    at least inspect headers and the text block.
    """

    def __init__(self, raw_bytes: bytes):
        self.raw_data = memoryview(bytearray(raw_bytes))
        offset = 0

        def read_and_seek(data_type):
            nonlocal offset
            value = data_type.from_buffer(self.raw_data, offset)
            setattr(value, "_dcb", self)
            offset += ctypes.sizeof(value)
            return value

        self.header = read_and_seek(dftypes.DataCoreHeader)
        self.structure_definitions = read_and_seek(
            dftypes.StructureDefinition * self.header.structure_definition_count
        )
        self.property_definitions = read_and_seek(
            dftypes.PropertyDefinition * self.header.property_definition_count
        )
        self.enum_definitions = read_and_seek(dftypes.EnumDefinition * self.header.enum_definition_count)
        if self.header.version >= 5:
            self.data_mapping_definitions = read_and_seek(
                dftypes.DataMappingDefinition32 * self.header.data_mapping_definition_count
            )
        else:
            self.data_mapping_definitions = read_and_seek(
                dftypes.DataMappingDefinition16 * self.header.data_mapping_definition_count
            )
        self.records = read_and_seek(dftypes.Record * self.header.record_definition_count)
        self.values = {
            DataTypes.Int8: read_and_seek(ctypes.c_int8 * self.header.int8_count),
            DataTypes.Int16: read_and_seek(ctypes.c_int16 * self.header.int16_count),
            DataTypes.Int32: read_and_seek(ctypes.c_int32 * self.header.int32_count),
            DataTypes.Int64: read_and_seek(ctypes.c_int64 * self.header.int64_count),
            DataTypes.UInt8: read_and_seek(ctypes.c_uint8 * self.header.uint8_count),
            DataTypes.UInt16: read_and_seek(ctypes.c_uint16 * self.header.uint16_count),
            DataTypes.UInt32: read_and_seek(ctypes.c_uint32 * self.header.uint32_count),
            DataTypes.UInt64: read_and_seek(ctypes.c_uint64 * self.header.uint64_count),
            DataTypes.Boolean: read_and_seek(ctypes.c_bool * self.header.boolean_count),
            DataTypes.Float: read_and_seek(ctypes.c_float * self.header.float_count),
            DataTypes.Double: read_and_seek(ctypes.c_double * self.header.double_count),
            DataTypes.GUID: read_and_seek(dftypes.GUID * self.header.guid_count),
            DataTypes.StringRef: read_and_seek(dftypes.StringReference * self.header.string_count),
            DataTypes.Locale: read_and_seek(dftypes.LocaleReference * self.header.locale_count),
            DataTypes.EnumChoice: read_and_seek(dftypes.EnumChoice * self.header.enum_count),
            DataTypes.StrongPointer: read_and_seek(dftypes.StrongPointer * self.header.strong_value_count),
            DataTypes.WeakPointer: read_and_seek(dftypes.WeakPointer * self.header.weak_value_count),
            DataTypes.Reference: read_and_seek(dftypes.Reference * self.header.reference_count),
            DataTypes.EnumValueName: read_and_seek(
                dftypes.StringReference * self.header.enum_option_name_count
            ),
        }

        self.text_offset = offset
        offset += self.header.text_length
        self.structure_instances: dict[int, list[int | dftypes.StructureInstance]] = {}
        self.structure_instances_by_offset: dict[int, dict[int, dftypes.StructureInstance]] = {}
        for mapping in self.data_mapping_definitions:
            struct_def = self.structure_definitions[mapping.structure_index]
            struct_size = struct_def.calculated_data_size
            for _ in range(mapping.structure_count):
                self.structure_instances.setdefault(mapping.structure_index, []).append(offset)
                offset += struct_size

        self._string_cache: dict[int, str] = {}
        self.records_by_guid: dict[str, dftypes.Record] = {}
        self.record_types: set[str] = set()
        self.entities: dict[str, dftypes.Record] = {}
        for record in self.records:
            try:
                record_type = record.type
            except Exception:
                record_type = ""
            if record_type == "EntityClassDefinition":
                self.entities[record.name] = record
            self.records_by_guid[record.id.value] = record
            self.record_types.add(record_type)

        self.trailing_bytes = len(self.raw_data) - offset

    def get_structure_instance_from_offset(self, structure_index: int, offset: int):
        if offset not in self.structure_instances_by_offset.setdefault(structure_index, {}):
            struct_def = self.structure_definitions[structure_index]
            self.structure_instances_by_offset[structure_index][offset] = dftypes.StructureInstance(
                self, offset, struct_def
            )
        return self.structure_instances_by_offset[structure_index][offset]

    def get_structure_instance(self, structure_index: int, instance: int):
        current = self.structure_instances[structure_index][instance]
        if not isinstance(current, dftypes.StructureInstance):
            offset = current
            self.structure_instances[structure_index][instance] = self.get_structure_instance_from_offset(
                structure_index, offset
            )
        return self.structure_instances[structure_index][instance]

    def string_for_offset(self, offset: int, encoding: str = "UTF-8") -> str:
        if offset not in self._string_cache:
            try:
                if offset >= self.header.text_length:
                    raise IndexError(f'Text offset "{offset}" is out of range')
                end = self.raw_data.obj.index(
                    0x00,
                    self.text_offset + offset,
                    self.text_offset + self.header.text_length,
                )
                self._string_cache[offset] = bytes(self.raw_data[self.text_offset + offset : end]).decode(encoding)
            except ValueError:
                sys.stderr.write(f"Invalid string offset: {offset}")
                return ""
        return self._string_cache[offset]


def read_ini_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw_line or raw_line.startswith((";", "#")) or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        mapping[key] = value
    return mapping


def parse_report_entries(path: Path) -> list[MissionEntry]:
    entries: list[MissionEntry] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = REPORT_ROW_RE.match(raw_line.strip())
        if not match:
            continue
        title_key = match.group("title")
        if title_key in seen:
            continue
        seen.add(title_key)
        entries.append(
            MissionEntry(
                title_key=title_key,
                desc_key=match.group("desc"),
                english_title=match.group("english"),
            )
        )
    return entries


def extract_item_refs(value: str | None) -> list[str]:
    if not value:
        return []
    seen: set[str] = set()
    refs: list[str] = []
    for match in ITEM_REF_RE.finditer(value):
        item_key = match.group(1)
        if item_key in seen:
            continue
        seen.add(item_key)
        refs.append(item_key)
    return refs


def resolve_item_labels(item_keys: list[str], english_map: dict[str, str]) -> list[str]:
    labels: list[str] = []
    for item_key in item_keys:
        labels.append(english_map.get(item_key, item_key))
    return labels


def find_datacore_member(sc: StarCitizen) -> str | None:
    for candidate in ("Data/Game.dcb", "Data/Game2.dcb"):
        try:
            sc.p4k.getinfo(candidate)
            return candidate
        except KeyError:
            continue
    return None


def load_datacore_session(*, sc_root: Path, cache_dir: Path) -> DatacoreSession:
    if not sc_root.exists():
        return DatacoreSession(
            dcb_path=None,
            status="missing-install",
            binary=None,
            note=f"No existe la ruta de Star Citizen: {sc_root}",
        )

    try:
        sc = StarCitizen(sc_root, cache_dir=cache_dir)
        dcb_member = find_datacore_member(sc)
        if dcb_member is None:
            return DatacoreSession(
                dcb_path=None,
                status="missing-dcb",
                binary=None,
                note="No se encontro Data/Game.dcb ni Data/Game2.dcb en el parche instalado.",
            )

        raw_bytes = sc.p4k.getinfo(dcb_member).open("rb").read()
        compat = DataCoreBinaryCompat(raw_bytes)

        status = "ok"
        note = (
            f"version={compat.header.version}, trailing_bytes={compat.trailing_bytes}, "
            f"records={compat.header.record_definition_count}"
        )
        return DatacoreSession(
            dcb_path=dcb_member,
            status=status,
            binary=bytes(raw_bytes),
            note=note,
        )
    except Exception as exc:
        return DatacoreSession(
            dcb_path=None,
            status="error",
            binary=None,
            note=f"{type(exc).__name__}: {exc}",
        )


def probe_datacore_entry(
    *,
    session: DatacoreSession,
    title_key: str,
    desc_key: str,
    english_title: str,
) -> DatacoreProbeResult:
    binary = session.binary or b""
    return DatacoreProbeResult(
        dcb_path=session.dcb_path,
        status=session.status,
        title_key_in_binary=title_key.encode("utf-8") in binary,
        desc_key_in_binary=desc_key.encode("utf-8") in binary,
        english_title_in_binary=english_title.encode("utf-8") in binary,
        note=session.note,
    )


def build_markdown_report(
    *,
    source_report: Path,
    output_path: Path,
    entries: list[MissionEntry],
    english_map: dict[str, str],
    blueprints_en: dict[str, str],
    blueprints_es: dict[str, str],
    sc_root: Path,
    cache_dir: Path,
) -> str:
    lines: list[str] = []
    lines.append("# Informe: recompensas de blueprints por mision")
    lines.append("")
    lines.append("Origenes usados:")
    lines.append(f"- Informe base: `{source_report.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- Overlay compartido: `{DEFAULT_BLUEPRINTS_EN.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- `global.ini` ingles: `{DEFAULT_GLOBAL_EN.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- Instalacion de Star Citizen sondeada: `{sc_root}`")
    lines.append("")
    lines.append("Notas:")
    lines.append("- Las recompensas visibles se extraen del `desc` de `blueprints.ini` mediante referencias `@item_...@`.")
    lines.append("- El sondeo DataForge usa `scdatatools.sc` para abrir la instalacion local y detectar `Data/Game*.dcb`.")
    lines.append("- En la build actual, `Game2.dcb` deja bytes residuales al parsear; por ahora el sondeo del DataForge se usa como validacion binaria y no como resolucion completa de enlaces de mision.")
    lines.append("")

    datacore_session = load_datacore_session(sc_root=sc_root, cache_dir=cache_dir)
    all_ok = 0
    for entry in entries:
        desc_en = blueprints_en.get(entry.desc_key)
        desc_es = blueprints_es.get(entry.desc_key)
        item_keys = extract_item_refs(desc_en)
        item_labels = resolve_item_labels(item_keys, english_map)
        probe = probe_datacore_entry(
            session=datacore_session,
            title_key=entry.title_key,
            desc_key=entry.desc_key,
            english_title=entry.english_title,
        )
        if probe.status == "ok":
            all_ok += 1

        lines.append(f"## {entry.english_title}")
        lines.append("")
        lines.append(f"- Clave `title`: `{entry.title_key}`")
        lines.append(f"- Clave `desc` esperada: `{entry.desc_key}`")
        lines.append(f"- Desc presente en overlay compartido: `{'si' if desc_en is not None else 'no'}`")
        lines.append(f"- Refs de blueprints detectadas: {len(item_keys)}")
        lines.append(
            f"- Sonda DataForge: status=`{probe.status}`"
            + (f", dcb=`{probe.dcb_path}`" if probe.dcb_path else "")
        )
        lines.append(
            f"- Coincidencias binarias DataForge: title_key=`{'si' if probe.title_key_in_binary else 'no'}`, "
            f"desc_key=`{'si' if probe.desc_key_in_binary else 'no'}`, "
            f"english_title=`{'si' if probe.english_title_in_binary else 'no'}`"
        )
        if probe.note:
            lines.append(f"- Nota tecnica: `{probe.note}`")
        lines.append("")

        if item_keys:
            lines.append("| Ref de item | Nombre ingles resuelto |")
            lines.append("|---|---|")
            for item_key, label in zip(item_keys, item_labels):
                lines.append(f"| `{item_key}` | `{label}` |")
            lines.append("")
        else:
            lines.append("No se han detectado referencias `@item_...@` en el `desc` ingles.")
            lines.append("")

    lines.append("## Resumen")
    lines.append("")
    lines.append(f"- Misiones analizadas: {len(entries)}")
    lines.append(f"- Misiones con `desc` en overlay compartido: {sum(1 for entry in entries if entry.desc_key in blueprints_en)}")
    lines.append(f"- Misiones con refs de blueprint detectadas: {sum(1 for entry in entries if extract_item_refs(blueprints_en.get(entry.desc_key)))}")
    lines.append(f"- Sondas DataForge completadas sin excepcion: {all_ok}")
    lines.append("")

    report_text = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(report_text)
    return report_text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrae recompensas visibles de blueprints por mision y sondea el DataForge local."
    )
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--blueprints-en", default=str(DEFAULT_BLUEPRINTS_EN))
    parser.add_argument("--blueprints-es", default=str(DEFAULT_BLUEPRINTS_ES))
    parser.add_argument("--global-en", default=str(DEFAULT_GLOBAL_EN))
    parser.add_argument("--sc-root", default=str(DEFAULT_SC_ROOT))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report_path = Path(args.report).expanduser().resolve()
    blueprints_en_path = Path(args.blueprints_en).expanduser().resolve()
    blueprints_es_path = Path(args.blueprints_es).expanduser().resolve()
    global_en_path = Path(args.global_en).expanduser().resolve()
    sc_root = Path(args.sc_root).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    entries = parse_report_entries(report_path)
    english_map = read_ini_map(global_en_path)
    blueprints_en = read_ini_map(blueprints_en_path)
    blueprints_es = read_ini_map(blueprints_es_path)

    build_markdown_report(
        source_report=report_path,
        output_path=output_path,
        entries=entries,
        english_map=english_map,
        blueprints_en=blueprints_en,
        blueprints_es=blueprints_es,
        sc_root=sc_root,
        cache_dir=cache_dir,
    )

    print(f"Informe generado: {output_path}")
    print(f"Misiones analizadas: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
