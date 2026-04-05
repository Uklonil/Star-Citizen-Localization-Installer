from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from localization_tools import resolve_path


def load_mismatches(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8"))


def token_counter(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def classify_mismatch(item: dict[str, object]) -> list[str]:
    english_tokens = [str(token) for token in item["english_tokens"]]
    candidate_tokens = [str(token) for token in item["candidate_tokens"]]
    english_counts = token_counter(english_tokens)
    candidate_counts = token_counter(candidate_tokens)

    categories: list[str] = []

    if english_counts["\\n"] != candidate_counts["\\n"]:
        categories.append("newlines_changed")

    english_markup = [token for token in english_tokens if token.startswith("<") or token.startswith("[[")]
    candidate_markup = [token for token in candidate_tokens if token.startswith("<") or token.startswith("[[")]
    if english_markup != candidate_markup:
        categories.append("markup_changed")

    broken_em4_tokens = [
        token
        for token in candidate_tokens
        if token.startswith("<EM4") and token not in ("<EM4>", "</EM4>")
    ]
    if any(token in ("<EM4>", "</EM4>") for token in english_tokens + candidate_tokens):
        if english_counts["<EM4>"] != candidate_counts["<EM4>"] or english_counts["</EM4>"] != candidate_counts["</EM4>"]:
            categories.append("em4_tags_changed")

    if broken_em4_tokens:
        categories.append("broken_em4_token")

    if not english_tokens and candidate_tokens:
        categories.append("tokens_added")

    if english_tokens and not candidate_tokens:
        categories.append("tokens_removed")

    if not categories:
        categories.append("other_token_mismatch")

    return categories


def write_summary_report(
    *,
    path: Path,
    grouped: dict[str, list[dict[str, object]]],
    counter: Counter[str],
) -> None:
    lines: list[str] = []
    lines.append("Resumen por categoria")
    lines.append("")
    for category, count in counter.most_common():
        lines.append(f"{category}: {count}")
    lines.append("")

    for category, items in sorted(grouped.items()):
        lines.append(f"[{category}]")
        for item in items[:50]:
            lines.append(f"- {item['key']}")
        if len(items) > 50:
            lines.append(f"... {len(items) - 50} claves mas")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write("\n".join(lines))


def write_json_groups(path: Path, grouped: dict[str, list[dict[str, object]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file_handle:
        file_handle.write(json.dumps(grouped, ensure_ascii=False, indent=2))


def write_category_key_lists(output_dir: Path, grouped: dict[str, list[dict[str, object]]]) -> None:
    keys_dir = output_dir / "groups"
    keys_dir.mkdir(parents=True, exist_ok=True)
    for category, items in grouped.items():
        keys = [str(item["key"]) for item in items]
        with (keys_dir / f"{category}.txt").open("w", encoding="utf-8", newline="\n") as file_handle:
            file_handle.write("\n".join(keys))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clasifica las claves con placeholders/markup alterados por tipo de rotura."
    )
    parser.add_argument("--input", default="dist/validation/placeholder-mismatches.json")
    parser.add_argument("--output-dir", default="dist/validation")
    args = parser.parse_args()

    input_path = resolve_path(args.input)
    output_dir = resolve_path(args.output_dir)
    mismatches = load_mismatches(input_path)

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    counter: Counter[str] = Counter()

    for item in mismatches:
        categories = classify_mismatch(item)
        enriched = dict(item)
        enriched["categories"] = categories
        for category in categories:
            grouped[category].append(enriched)
            counter[category] += 1

    write_summary_report(
        path=output_dir / "placeholder-mismatch-groups.txt",
        grouped=grouped,
        counter=counter,
    )
    write_json_groups(
        path=output_dir / "placeholder-mismatch-groups.json",
        grouped=grouped,
    )
    write_category_key_lists(output_dir, grouped)

    print("Categorias detectadas:")
    for category, count in counter.most_common():
        print(f"- {category}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
