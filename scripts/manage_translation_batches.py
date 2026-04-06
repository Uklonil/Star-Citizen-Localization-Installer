from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

from localization_tools import resolve_path


@dataclass(frozen=True)
class BatchWindow:
    batch_number: int
    start_index: int
    end_index: int

    @property
    def start_line(self) -> int:
        return self.start_index + 1

    @property
    def end_line(self) -> int:
        return self.end_index


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig").splitlines()


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(lines))


def count_entries(lines: list[str]) -> int:
    return sum(1 for line in lines if line and not line.startswith((";", "#")) and "=" in line)


def ensure_destination(source_lines: list[str], destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        return

    write_lines(destination, source_lines)


def build_window(total_lines: int, batch_size: int, batch_number: int) -> BatchWindow:
    if batch_number < 1:
        raise ValueError("El numero de lote debe ser >= 1.")

    start_index = (batch_number - 1) * batch_size
    if start_index >= total_lines:
        raise ValueError(f"El lote {batch_number} queda fuera del archivo de origen.")

    end_index = min(start_index + batch_size, total_lines)
    return BatchWindow(batch_number=batch_number, start_index=start_index, end_index=end_index)


def run_checks(source: Path, translated: Path) -> None:
    subprocess.run(
        [
            "python",
            ".codex/skills/translate-loc/scripts/checks.py",
            str(source),
            str(translated),
        ],
        check=True,
    )


def command_init(args: argparse.Namespace) -> int:
    source = resolve_path(args.source)
    destination = resolve_path(args.destination)
    source_lines = read_lines(source)
    ensure_destination(source_lines=source_lines, destination=destination, force=args.force)
    print(f"Destino preparado: {destination}")
    print(f"Lineas: {len(source_lines)}")
    print(f"Entradas: {count_entries(source_lines)}")
    return 0


def command_export_batch(args: argparse.Namespace) -> int:
    source = resolve_path(args.source)
    destination = resolve_path(args.destination)
    workspace = resolve_path(args.workspace)

    source_lines = read_lines(source)
    ensure_destination(source_lines=source_lines, destination=destination, force=False)
    destination_lines = read_lines(destination)
    if len(source_lines) != len(destination_lines):
        raise ValueError("El destino no tiene el mismo numero de lineas que el origen.")

    window = build_window(
        total_lines=len(source_lines),
        batch_size=args.batch_size,
        batch_number=args.batch,
    )

    batch_dir = workspace / f"batch-{window.batch_number:04d}"
    source_batch = batch_dir / "source.ini"
    current_batch = batch_dir / "current.ini"
    translated_batch = batch_dir / "translated.ini"
    metadata = batch_dir / "README.txt"

    source_slice = source_lines[window.start_index : window.end_index]
    current_slice = destination_lines[window.start_index : window.end_index]

    write_lines(source_batch, source_slice)
    write_lines(current_batch, current_slice)

    metadata_lines = [
        f"Lote: {window.batch_number}",
        f"Lineas: {window.start_line}-{window.end_line}",
        f"Tamano de lote: {args.batch_size}",
        f"Entradas origen en lote: {count_entries(source_slice)}",
        f"Origen: {source}",
        f"Destino final: {destination}",
        "",
        "Traduce source.ini a translated.ini manteniendo claves, placeholders, escapes, tags y orden.",
        "Puedes usar current.ini como referencia del estado actual del destino.",
    ]
    write_lines(metadata, metadata_lines)

    if not translated_batch.exists():
        write_lines(translated_batch, current_slice)

    print(f"Lote exportado: {batch_dir}")
    print(f"Lineas: {window.start_line}-{window.end_line}")
    print(f"Entradas: {count_entries(source_slice)}")
    return 0


def command_apply_batch(args: argparse.Namespace) -> int:
    source = resolve_path(args.source)
    destination = resolve_path(args.destination)
    workspace = resolve_path(args.workspace)

    source_lines = read_lines(source)
    ensure_destination(source_lines=source_lines, destination=destination, force=False)
    destination_lines = read_lines(destination)
    if len(source_lines) != len(destination_lines):
        raise ValueError("El destino no tiene el mismo numero de lineas que el origen.")

    window = build_window(
        total_lines=len(source_lines),
        batch_size=args.batch_size,
        batch_number=args.batch,
    )

    batch_dir = workspace / f"batch-{window.batch_number:04d}"
    source_batch = batch_dir / "source.ini"
    translated_batch = resolve_path(args.translated) if args.translated else batch_dir / "translated.ini"
    validated_batch = batch_dir / "validated.ini"

    if not source_batch.exists():
        raise FileNotFoundError(f"No existe el lote exportado: {source_batch}")
    if not translated_batch.exists():
        raise FileNotFoundError(f"No existe el archivo traducido: {translated_batch}")

    source_slice = source_lines[window.start_index : window.end_index]
    translated_slice = read_lines(translated_batch)
    if len(source_slice) != len(translated_slice):
        raise ValueError(
            "El lote traducido no tiene el mismo numero de lineas que el lote origen "
            f"({len(translated_slice)} vs {len(source_slice)})."
        )

    write_lines(validated_batch, translated_slice)
    run_checks(source_batch, validated_batch)

    merged_lines = destination_lines[:]
    merged_lines[window.start_index : window.end_index] = translated_slice
    write_lines(destination, merged_lines)
    run_checks(source, destination)

    translated_entries = sum(
        1 for source_line, target_line in zip(source_slice, translated_slice) if source_line != target_line
    )
    print(f"Lote aplicado: {window.batch_number}")
    print(f"Lineas: {window.start_line}-{window.end_line}")
    print(f"Entradas traducidas en lote: {translated_entries}")
    print(f"Destino actualizado: {destination}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    source = resolve_path(args.source)
    destination = resolve_path(args.destination)
    source_lines = read_lines(source)
    ensure_destination(source_lines=source_lines, destination=destination, force=False)
    destination_lines = read_lines(destination)

    if len(source_lines) != len(destination_lines):
        raise ValueError("El destino no tiene el mismo numero de lineas que el origen.")

    translated_entries = sum(
        1
        for source_line, destination_line in zip(source_lines, destination_lines)
        if source_line != destination_line
    )
    total_entries = count_entries(source_lines)
    total_batches = (len(source_lines) + args.batch_size - 1) // args.batch_size

    print(f"Origen: {source}")
    print(f"Destino: {destination}")
    print(f"Lineas totales: {len(source_lines)}")
    print(f"Entradas totales: {total_entries}")
    print(f"Entradas traducidas: {translated_entries}")
    print(f"Lotes de {args.batch_size}: {total_batches}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gestiona traducciones por lotes para global.ini.")
    parser.add_argument("--source", default="input/current/global.ini")
    parser.add_argument("--destination", default="source/languages/es-es/translation.ini")
    parser.add_argument("--workspace", default="input/translation-batches")
    parser.add_argument("--batch-size", type=int, default=250)

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Prepara el destino a partir del origen.")
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(func=command_init)

    export_parser = subparsers.add_parser("export-batch", help="Exporta un lote para traduccion.")
    export_parser.add_argument("--batch", type=int, required=True)
    export_parser.set_defaults(func=command_export_batch)

    apply_parser = subparsers.add_parser("apply-batch", help="Aplica y valida un lote traducido.")
    apply_parser.add_argument("--batch", type=int, required=True)
    apply_parser.add_argument("--translated")
    apply_parser.set_defaults(func=command_apply_batch)

    status_parser = subparsers.add_parser("status", help="Muestra el progreso de traduccion.")
    status_parser.set_defaults(func=command_status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
