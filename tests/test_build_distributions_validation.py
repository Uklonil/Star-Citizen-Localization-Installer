from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (
    REPO_ROOT,
    REPO_ROOT / "scripts",
    REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "core",
):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from scripts.build_distributions import extract_tokens, validate_reference_map  # noqa: E402
from scripts.localization_tools import Entry, GlobalIniData, merge_translations  # noqa: E402


class BuildDistributionsValidationTests(unittest.TestCase):
    def test_extract_tokens_normalizes_known_em_tag_typo(self) -> None:
        english_value = "Head over to <EM4>~mission(Location|Address)<EM4> now."
        translated_value = "Ve a <EM4>~mission(Location|Address)</EM4> ahora."

        self.assertEqual(extract_tokens(english_value), extract_tokens(translated_value))

    def test_validate_reference_map_allows_unknown_translation_keys_when_requested(self) -> None:
        english_map = {
            "known_key": "Hello %s",
        }
        candidate_map = {
            "known_key": "Hola %s",
            "old_patch_key": "Legacy value",
        }

        errors = validate_reference_map(
            english_map=english_map,
            candidate_map=candidate_map,
            label="Master memory es-es",
            allow_unknown_keys=True,
        )

        self.assertEqual(errors, [])

    def test_merge_translations_reports_missing_current_patch_keys(self) -> None:
        english_data = GlobalIniData(
            entries=[
                Entry(key="key_a", value="A"),
                Entry(key="key_b", value="B"),
            ],
            mapping={
                "key_a": "A",
                "key_b": "B",
            },
        )

        result = merge_translations(
            english_data=english_data,
            translation_map={
                "key_a": "Traducido A",
                "old_patch_key": "Legacy value",
            },
        )

        self.assertEqual(result.missing_count, 1)
        self.assertEqual([entry.key for entry in result.missing], ["key_b"])


if __name__ == "__main__":
    unittest.main()
