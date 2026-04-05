from __future__ import annotations

from pathlib import Path
import re
import sys


PLACEHOLDER_RE = re.compile(
    r"(%(?:\d+\$)?[sdif])"          # printf-like placeholders
    r"|(\{[^{}\n]+\})"              # brace placeholders
    r"|(\\n|\\t|\\r|\\\")"          # escaped sequences
    r"|(\[\[.*?\]\])"               # game-style wrappers
    r"|(</?[A-Za-z][^>\n]*>)"       # tags
)


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(code)


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace").splitlines()


def split_key_value(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not line or stripped.startswith("#") or stripped.startswith(";"):
        return None
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    return key, value


def main() -> None:
    if len(sys.argv) != 3:
        fail("Usage: python checks.py <source_file> <translated_file>")

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    if not src.exists():
        fail(f"Source file not found: {src}")
    if not dst.exists():
        fail(f"Translated file not found: {dst}")

    src_lines = read_lines(src)
    dst_lines = read_lines(dst)

    if len(src_lines) != len(dst_lines):
        fail(f"Line count differs: source={len(src_lines)} translated={len(dst_lines)}")

    translated_entries = 0

    for i, (src_line, dst_line) in enumerate(zip(src_lines, dst_lines), start=1):
        src_pair = split_key_value(src_line)
        dst_pair = split_key_value(dst_line)

        if src_pair is None and dst_pair is None:
            continue
        if (src_pair is None) != (dst_pair is None):
            fail(f"Line {i}: structure changed")

        assert src_pair is not None and dst_pair is not None
        src_key, src_value = src_pair
        dst_key, dst_value = dst_pair

        if src_key != dst_key:
            fail(f"Line {i}: key changed from {src_key!r} to {dst_key!r}")

        src_tokens = PLACEHOLDER_RE.findall(src_value)
        dst_tokens = PLACEHOLDER_RE.findall(dst_value)

        src_flat = [token for group in src_tokens for token in group if token]
        dst_flat = [token for group in dst_tokens for token in group if token]

        if src_flat != dst_flat:
            fail(
                f"Line {i}: placeholders/markup changed.\n"
                f"  source tokens: {src_flat}\n"
                f"  target tokens: {dst_flat}"
            )

        if src_value != dst_value:
            translated_entries += 1

    print("OK")
    print(f"Source lines: {len(src_lines)}")
    print(f"Translated entries: {translated_entries}")


if __name__ == "__main__":
    main()
