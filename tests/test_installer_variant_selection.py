from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from installer import installer_core


class InstallerVariantSelectionTests(unittest.TestCase):
    def test_variant_name_from_overlay_selection_covers_all_combinations(self) -> None:
        self.assertEqual(
            installer_core.variant_name_from_overlay_selection(
                components_enabled=False,
                blueprints_enabled=False,
            ),
            "base",
        )
        self.assertEqual(
            installer_core.variant_name_from_overlay_selection(
                components_enabled=True,
                blueprints_enabled=False,
            ),
            "componentes",
        )
        self.assertEqual(
            installer_core.variant_name_from_overlay_selection(
                components_enabled=False,
                blueprints_enabled=True,
            ),
            "blueprints",
        )
        self.assertEqual(
            installer_core.variant_name_from_overlay_selection(
                components_enabled=True,
                blueprints_enabled=True,
            ),
            "componentes-blueprints",
        )

    def test_overlay_selection_from_variant_name_round_trips(self) -> None:
        self.assertEqual(installer_core.overlay_selection_from_variant_name("base"), (False, False))
        self.assertEqual(installer_core.overlay_selection_from_variant_name("componentes"), (True, False))
        self.assertEqual(installer_core.overlay_selection_from_variant_name("blueprints"), (False, True))
        self.assertEqual(installer_core.overlay_selection_from_variant_name("componentes-blueprints"), (True, True))

    def test_resolve_variant_name_returns_none_when_combination_missing(self) -> None:
        self.assertIsNone(
            installer_core.resolve_variant_name(
                available_variants={"base", "componentes"},
                components_enabled=False,
                blueprints_enabled=True,
            )
        )

    def test_default_overlay_selection_falls_back_to_first_available_variant(self) -> None:
        self.assertEqual(
            installer_core.default_overlay_selection(
                available_variants={"blueprints"},
            ),
            (False, True),
        )

    def test_variant_supports_overlay_matches_expected_capabilities(self) -> None:
        self.assertTrue(installer_core.variant_supports_overlay("componentes-blueprints", "componentes"))
        self.assertTrue(installer_core.variant_supports_overlay("componentes-blueprints", "blueprints"))
        self.assertFalse(installer_core.variant_supports_overlay("base", "componentes"))
        self.assertFalse(installer_core.variant_supports_overlay("base", "blueprints"))

    def test_bundle_from_manifest_supports_schema_v2_variant_lists(self) -> None:
        with TemporaryDirectory() as temp_dir:
            extracted_root = Path(temp_dir)
            (extracted_root / "es-es" / "blueprints").mkdir(parents=True)
            (extracted_root / "es-es" / "componentes-blueprints").mkdir(parents=True)
            manifest = {
                "version": "9.9.9",
                "installer_bundle": {
                    "filename": "bundle.zip",
                    "url": "https://example.invalid/bundle.zip",
                },
                "languages": {
                    "es-es": {
                        "label": "Espanol (Espana)",
                        "game_language": "spanish_(spain)",
                        "variants": ["blueprints", "componentes-blueprints"],
                    }
                },
            }

            bundle = installer_core._bundle_from_manifest(
                manifest=manifest,
                release_url=None,
                extracted_root=extracted_root,
            )

            self.assertEqual(bundle.version, "9.9.9")
            self.assertEqual(bundle.root, extracted_root)
            self.assertEqual(
                sorted(bundle.languages["es-es"].variants),
                ["blueprints", "componentes-blueprints"],
            )
            self.assertEqual(
                bundle.languages["es-es"].variants["blueprints"].source_dir,
                extracted_root / "es-es" / "blueprints",
            )


if __name__ == "__main__":
    unittest.main()
