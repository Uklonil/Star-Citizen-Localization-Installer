from __future__ import annotations

from pathlib import Path
import argparse
import re
import sys


PLACEHOLDER_RE = re.compile(
    r"(%(?:\d+\$)?[sdif])"                         # printf-like placeholders
    r"|(\{[^{}\n]+\})"                             # brace placeholders
    r"|(\\n|\\t|\\r|\\\")"                         # escaped sequences
    r"|(\[\[.*?\]\])"                              # game-style wrappers
    r"|(@[A-Za-z0-9_.:-]+@)"                       # overlay references
    r"|(\#\#[A-Za-z0-9_.:-]+\#\#)"                 # blueprint auxiliary tokens
    r"|(</?[A-Za-z][^>\n]*>)"                      # HTML/XML-like tags
    r"|(&[A-Za-z]+;|&#\d+;|&#x[0-9A-Fa-f]+;)"      # escaped HTML entities
)

INTERNAL_ID_RE = re.compile(
    r"\b("
    r"BP_MISSIONREWARD_[A-Za-z0-9_]+"
    r"|OVERLAY_[A-Za-z0-9_]+"
    r"|LOC_[A-Za-z0-9_]+"
    r"|item_[A-Za-z0-9_]+"
    r"|vehicle_[A-Za-z0-9_]+"
    r"|ContractGenerator\.[A-Za-z0-9_.-]+"
    r"|contractgenerator/[^\s]+\.xml"
    r"|missiondata/[^\s]+\.xml"
    r")\b",
    re.IGNORECASE,
)


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(code)


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        fail(f"Cannot read file {path}: {exc}")
        raise


def decode_text(raw: bytes, path: Path) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        print(f"WARNING: {path} contains invalid UTF-8 bytes; decoding with replacement characters")
        return raw.decode("utf-8-sig", errors="replace")


def read_lines(path: Path) -> list[str]:
    return decode_text(read_bytes(path), path).splitlines()


def has_bom(raw: bytes) -> bool:
    return raw.startswith(b"\xef\xbb\xbf")


def has_final_newline(raw: bytes) -> bool:
    return raw.endswith(b"\n") or raw.endswith(b"\r\n")


def uses_crlf_only(raw: bytes) -> bool:
    normalized = raw.replace(b"\r\n", b"")
    return b"\n" not in normalized and b"\r" not in normalized


def split_key_value(line: str) -> tuple[str, str] | None:
    stripped = line.strip()

    if line == "" or stripped.startswith("#") or stripped.startswith(";"):
        return None

    if "=" not in line:
        return None

    key, value = line.split("=", 1)
    return key, value


def flatten_tokens(matches: list[tuple[str, ...]]) -> list[str]:
    return [token for group in matches for token in group if token]


def extract_tokens(value: str) -> list[str]:
    return flatten_tokens(PLACEHOLDER_RE.findall(value))


def extract_internal_ids(value: str) -> list[str]:
    return INTERNAL_ID_RE.findall(value)


def write_report(
    report_path: Path,
    source: Path,
    translated: Path,
    source_lines: int,
    translated_entries: int,
    token_protected_entries: int,
    warnings: list[str],
    strict_format: bool,
) -> None:
    lines = [
        "# translate-loc validation report",
        "",
        f"- Source: `{source}`",
        f"- Translated: `{translated}`",
        f"- Source lines: `{source_lines}`",
        f"- Translated entries: `{translated_entries}`",
        f"- Token-protected entries: `{token_protected_entries}`",
        f"- Warnings: `{len(warnings)}`",
        f"- Strict format: `{strict_format}`",
        "",
    ]

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def validate_strict_format(src_raw: bytes, dst_raw: bytes) -> list[str]:
    errors = []

    if has_bom(src_raw) and not has_bom(dst_raw):
        errors.append("translated file is missing UTF-8 BOM")

    if has_final_newline(src_raw) and not has_final_newline(dst_raw):
        errors.append("translated file is missing final newline")

    if uses_crlf_only(src_raw) and not uses_crlf_only(dst_raw):
        errors.append("translated file does not preserve CRLF line endings")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate translated localization files without altering keys, placeholders, markup or structure."
    )
    parser.add_argument("source_file")
    parser.add_argument("translated_file")
    parser.add_argument(
        "--strict-format",
        action="store_true",
        help="Validate BOM, CRLF line endings and final newline when present in source.",
    )
    parser.add_argument(
        "--report",
        help="Optional Markdown report path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    src = Path(args.source_file)
    dst = Path(args.translated_file)

    if not src.exists():
        fail(f"Source file not found: {src}")

    if not dst.exists():
        fail(f"Translated file not found: {dst}")

    src_raw = read_bytes(src)
    dst_raw = read_bytes(dst)

    if args.strict_format:
        format_errors = validate_strict_format(src_raw, dst_raw)
        if format_errors:
            fail("Strict format validation failed:\n  - " + "\n  - ".join(format_errors))

    src_lines = decode_text(src_raw, src).splitlines()
    dst_lines = decode_text(dst_raw, dst).splitlines()

    if len(src_lines) != len(dst_lines):
        fail(f"Line count differs: source={len(src_lines)} translated={len(dst_lines)}")

    translated_entries = 0
    token_protected_entries = 0
    warnings: list[str] = []

    for i, (src_line, dst_line) in enumerate(zip(src_lines, dst_lines), start=1):
        src_pair = split_key_value(src_line)
        dst_pair = split_key_value(dst_line)

        if src_pair is None and dst_pair is None:
            if src_line != dst_line:
                warnings.append(f"Line {i}: non key-value line changed")
            continue

        if (src_pair is None) != (dst_pair is None):
            fail(f"Line {i}: structure changed")

        assert src_pair is not None and dst_pair is not None

        src_key, src_value = src_pair
        dst_key, dst_value = dst_pair

        if src_key != dst_key:
            fail(f"Line {i}: key changed from {src_key!r} to {dst_key!r}")

        src_tokens = extract_tokens(src_value)
        dst_tokens = extract_tokens(dst_value)

        if src_tokens:
            token_protected_entries += 1

        if src_tokens != dst_tokens:
            fail(
                f"Line {i}: placeholders/markup changed.\n"
                f"  source tokens: {src_tokens}\n"
                f"  target tokens: {dst_tokens}"
            )

        src_internal_ids = extract_internal_ids(src_value)
        dst_internal_ids = extract_internal_ids(dst_value)

        if src_internal_ids != dst_internal_ids:
            warnings.append(
                f"Line {i}: internal identifiers differ. "
                f"source={src_internal_ids} target={dst_internal_ids}"
            )

        if src_value != dst_value:
            translated_entries += 1

    if args.report:
        write_report(
            Path(args.report),
            src,
            dst,
            len(src_lines),
            translated_entries,
            token_protected_entries,
            warnings,
            args.strict_format,
        )

    print("OK")
    print(f"Source lines: {len(src_lines)}")
    print(f"Translated entries: {translated_entries}")
    print(f"Token-protected entries: {token_protected_entries}")
    print(f"Warnings: {len(warnings)}")

    for warning in warnings:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    main()