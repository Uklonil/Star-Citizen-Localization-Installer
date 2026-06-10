from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "core"
SCRIPTS_DIR = REPO_ROOT / "scripts"

for candidate in (CORE_DIR, SCRIPTS_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from blueprint_pool_source import (  # noqa: E402
    GENERIC_BLUEPRINT_BLOCK_PREFIX,
    _apply_contract_metadata,
    default_contract_metadata_source_path,
    default_blueprint_source_paths,
    generate_blueprints_overlay_data,
    load_contract_metadata_source,
    resolve_pool_tokens,
)
from dcb_text_support import build_title_index, split_strings_with_offsets  # noqa: E402
from extract_blueprints import (  # noqa: E402
    DEFAULT_P4K,
    build_extraction_paths,
    find_extracted_game2,
    resolve_p4k_path,
    resolve_starbreaker_path,
    run_scan,
)
from runtime_support import REPO_ROOT as MODULE_REPO_ROOT, find_datacore_member  # noqa: E402


class _FakeP4K:
    def __init__(self, available_members: set[str]) -> None:
        self.available_members = available_members

    def getinfo(self, member: str) -> dict[str, str]:
        if member not in self.available_members:
            raise KeyError(member)
        return {"member": member}


class _FakeStarCitizen:
    def __init__(self, available_members: set[str]) -> None:
        self.p4k = _FakeP4K(available_members)


class BlueprintExtractorCoreTests(unittest.TestCase):
    def test_runtime_support_repo_root_matches_repository(self) -> None:
        self.assertEqual(MODULE_REPO_ROOT, REPO_ROOT)

    def test_find_datacore_member_prefers_game_dcb(self) -> None:
        sc = _FakeStarCitizen({"Data/Game.dcb", "Data/Game2.dcb"})
        self.assertEqual(find_datacore_member(sc), "Data/Game.dcb")

    def test_find_datacore_member_falls_back_to_game2(self) -> None:
        sc = _FakeStarCitizen({"Data/Game2.dcb"})
        self.assertEqual(find_datacore_member(sc), "Data/Game2.dcb")

    def test_find_datacore_member_returns_none_when_missing(self) -> None:
        sc = _FakeStarCitizen(set())
        self.assertIsNone(find_datacore_member(sc))

    def test_default_blueprint_source_paths(self) -> None:
        template_path, pools_path = default_blueprint_source_paths(REPO_ROOT)
        self.assertEqual(template_path, REPO_ROOT / "source" / "blueprints" / "blueprints_template.ini")
        self.assertEqual(pools_path, REPO_ROOT / "source" / "blueprints" / "pools.json")

    def test_default_contract_metadata_source_path(self) -> None:
        self.assertEqual(
            default_contract_metadata_source_path(REPO_ROOT),
            REPO_ROOT / "source" / "blueprints" / "contracts_metadata.json",
        )

    def test_resolve_starbreaker_path_accepts_nested_repo_binary(self) -> None:
        resolved = resolve_starbreaker_path("tools/starbreaker.exe")
        self.assertEqual(resolved, (REPO_ROOT / "tools" / "starbreaker" / "starbreaker.exe").resolve())

    def test_resolve_p4k_path_uses_requested_or_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            p4k = Path(temp_dir) / "Data.p4k"
            p4k.write_bytes(b"stub")
            self.assertEqual(resolve_p4k_path(p4k), p4k.resolve())

        with self.assertRaisesRegex(FileNotFoundError, "Data.p4k not found"):
            resolve_p4k_path(REPO_ROOT / "missing" / "Data.p4k")

    def test_build_extraction_paths(self) -> None:
        paths = build_extraction_paths("C:/data/starcitizen")
        self.assertEqual(paths.raw_root, Path("C:/data/starcitizen") / "extracts" / "current" / "game2" / "raw")
        self.assertEqual(paths.export_root, Path("C:/data/starcitizen") / "extracts" / "current" / "game2" / "exported")
        self.assertEqual(paths.reports_root, Path("C:/data/starcitizen") / "reports" / "blueprints")
        self.assertEqual(paths.normalized_game2, Path("C:/data/starcitizen") / "extracts" / "current" / "game2" / "Game2.dcb")

    def test_find_extracted_game2(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_root = Path(temp_dir)
            nested = raw_root / "foo" / "bar"
            nested.mkdir(parents=True)
            game2 = nested / "Game2.dcb"
            game2.write_bytes(b"stub")
            self.assertEqual(find_extracted_game2(raw_root), game2)

    def test_run_scan_builds_expected_command(self) -> None:
        normalized_game2 = REPO_ROOT / "tmp" / "Game2.dcb"
        starbreaker = REPO_ROOT / "tools" / "starbreaker" / "starbreaker.exe"
        p4k = DEFAULT_P4K
        reports_root = REPO_ROOT / "tmp" / "reports"

        with mock.patch("extract_blueprints.run_command") as run_command:
            run_command.return_value.returncode = 0
            code = run_scan(
                normalized_game2=normalized_game2,
                starbreaker=starbreaker,
                p4k=p4k,
                reports_root=reports_root,
            )

        self.assertEqual(code, 0)
        called_args = [str(value) for value in run_command.call_args.args[0]]
        self.assertEqual(called_args[0], sys.executable)
        self.assertIn(str(REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "core" / "scan_game2_text.py"), called_args)
        self.assertIn("--game2", called_args)
        self.assertIn(str(normalized_game2), called_args)

    def test_split_strings_with_offsets_and_title_index(self) -> None:
        raw = b"ignore\x00@mission_alpha_title\x00ContractGenerator.Test\x00"

        strings = split_strings_with_offsets(raw)
        title_index = build_title_index(strings)

        self.assertEqual(strings[0], (0, "ignore"))
        self.assertEqual(strings[1], (7, "@mission_alpha_title"))
        self.assertEqual(title_index["mission_alpha_title"], 7)

    def test_resolve_pool_tokens_renders_item_refs(self) -> None:
        pool_map = {
            "BP_MISSIONREWARD_TEST": {
                "item_refs": ["ITEM_ALPHA", "ITEM_BETA"],
            }
        }

        rendered = resolve_pool_tokens("Loot:\\n@BP_MISSIONREWARD_TEST@", pool_map=pool_map)

        self.assertEqual(rendered, "Loot:\\n- @ITEM_ALPHA@\\n- @ITEM_BETA@")

    def test_generate_blueprints_overlay_data_supports_single_and_multi_pool_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / "blueprints_template.ini"
            pools_path = temp_root / "pools.json"

            template_path.write_text(
                "\n".join(
                    [
                        "mission_single=Loot:\\n@BP_MISSIONREWARD_SINGLE@",
                        "mission_multi=Original text",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            pools_path.write_text(
                json.dumps(
                    {
                        "pools": {
                            "BP_MISSIONREWARD_SINGLE": {
                                "item_refs": ["ITEM_ALPHA", "ITEM_BETA"],
                            },
                            "BP_MISSIONREWARD_MULTI_A": {
                                "lines": ["<EM4>##pool_a##</EM4>", "- @ITEM_ONE@"],
                            },
                            "BP_MISSIONREWARD_MULTI_B": {
                                "item_refs": ["ITEM_TWO"],
                            },
                        },
                        "mission_pool_map": {
                            "mission_single": "BP_MISSIONREWARD_SINGLE",
                            "mission_multi": [
                                "BP_MISSIONREWARD_MULTI_A",
                                "BP_MISSIONREWARD_MULTI_B",
                            ],
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            generated = generate_blueprints_overlay_data(
                template_path=template_path,
                pool_source_path=pools_path,
            )

        self.assertEqual(
            generated.mapping["mission_single"],
            "Loot:\\n- @ITEM_ALPHA@\\n- @ITEM_BETA@",
        )
        self.assertEqual(
            generated.mapping["mission_multi"],
            (
                f"{GENERIC_BLUEPRINT_BLOCK_PREFIX}"
                "<EM4>##pool_a##</EM4>\\n- @ITEM_ONE@\\n\\n- @ITEM_TWO@"
            ),
        )

    def test_generate_blueprints_overlay_data_rejects_unknown_pools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / "blueprints_template.ini"
            pools_path = temp_root / "pools.json"

            template_path.write_text("mission_single=@BP_MISSIONREWARD_SINGLE@\n", encoding="utf-8")
            pools_path.write_text(
                json.dumps(
                    {
                        "pools": {},
                        "mission_pool_map": {
                            "mission_single": "BP_MISSIONREWARD_MISSING",
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "pools inexistentes"):
                generate_blueprints_overlay_data(
                    template_path=template_path,
                    pool_source_path=pools_path,
                )

    def test_apply_contract_metadata_injects_description_lines_before_blueprints(self) -> None:
        contract_metadata = {
            "title_meta": {},
            "description_meta": {
                "mission_desc": {
                    "reputation_awarded": ["100"],
                    "scenario_progress_points": ["50"],
                    "tier_labels": ["Jr. Contractor"],
                }
            },
        }

        rendered = _apply_contract_metadata(
            entry_key="mission_desc",
            value="\\n\\n<EM4>##potential_blueprints##</EM4>\\n@BP_POOL@",
            contract_metadata=contract_metadata,
        )

        self.assertIn("<EM4>##reputation_awarded##:</EM4> 100", rendered)
        self.assertIn("<EM4>##scenario_progress_points##:</EM4> 50", rendered)
        self.assertIn("<EM4>##awarded_in_junior_contractor_rank_variants##</EM4>", rendered)
        self.assertLess(rendered.index("##scenario_progress_points##"), rendered.index("##potential_blueprints##"))

    def test_apply_contract_metadata_rewrites_bp_title_suffix_with_rep_prefix(self) -> None:
        contract_metadata = {
            "title_meta": {
                "mission_title": {
                    "rep_ranges": ["100"],
                    "blueprint_flag_uncertain": True,
                }
            },
            "description_meta": {},
        }

        rendered = _apply_contract_metadata(
            entry_key="mission_title",
            value=" <EM4>[BP]</EM4>",
            contract_metadata=contract_metadata,
        )

        self.assertEqual(rendered, " <EM4>[100 Rep] [BP]*</EM4>")

    def test_apply_contract_metadata_appends_metadata_without_blueprint_block(self) -> None:
        contract_metadata = {
            "title_meta": {},
            "description_meta": {
                "mission_desc": {
                    "reputation_awarded": ["75"],
                    "scenario_progress_points": ["20"],
                    "tier_labels": [],
                }
            },
        }

        rendered = _apply_contract_metadata(
            entry_key="mission_desc",
            value="",
            contract_metadata=contract_metadata,
        )

        self.assertIn("<EM4>##reputation_awarded##:</EM4> 75", rendered)
        self.assertIn("<EM4>##scenario_progress_points##:</EM4> 20", rendered)
        self.assertNotIn("##potential_blueprints##", rendered)

    def test_apply_contract_metadata_adds_rep_only_title_without_bp_flag(self) -> None:
        contract_metadata = {
            "title_meta": {
                "mission_title": {
                    "blueprint_flag": False,
                    "blueprint_flag_uncertain": False,
                    "rep_ranges": ["150"],
                }
            },
            "description_meta": {},
        }

        rendered = _apply_contract_metadata(
            entry_key="mission_title",
            value="",
            contract_metadata=contract_metadata,
        )

        self.assertEqual(rendered, " <EM4>[150 Rep]</EM4>")

    def test_load_contract_metadata_source_reads_expected_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "contracts_metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "title_meta": {
                            "mission_title": {
                                "blueprint_flag": True,
                                "blueprint_flag_uncertain": False,
                                "rep_ranges": ["100"],
                            }
                        },
                        "description_meta": {
                            "mission_desc": {
                                "classification": "new-tier-label-only",
                                "tier_labels": ["Jr. Contractor"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            payload = load_contract_metadata_source(metadata_path)

        self.assertIn("title_meta", payload)
        self.assertIn("description_meta", payload)

    def test_generate_blueprints_overlay_data_adds_metadata_only_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "blueprints_template.ini"
            pools_path = Path(temp_dir) / "pools.json"
            metadata_path = Path(temp_dir) / "contracts_metadata.json"
            template_path.write_text("mission_with_pool=\\n\\n<EM4>##potential_blueprints##</EM4>\\n@BP_POOL@\n", encoding="utf-8")
            pools_path.write_text(
                json.dumps(
                    {
                        "pools": {
                            "BP_POOL_SIMPLE": {
                                "item_refs": ["item_test"],
                            }
                        },
                        "mission_pool_map": {
                            "mission_with_pool": "BP_POOL_SIMPLE",
                        },
                    }
                ),
                encoding="utf-8",
            )
            metadata_path.write_text(
                json.dumps(
                    {
                        "title_meta": {
                            "mission_title_only": {
                                "blueprint_flag": False,
                                "blueprint_flag_uncertain": False,
                                "rep_ranges": ["200"],
                            }
                        },
                        "description_meta": {
                            "mission_desc_only": {
                                "classification": "new-metadata-only",
                                "reputation_awarded": ["80"],
                                "scenario_progress_points": ["40"],
                                "tier_labels": [],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch("blueprint_pool_source.default_contract_metadata_source_path", return_value=metadata_path):
                generated = generate_blueprints_overlay_data(
                    template_path=template_path,
                    pool_source_path=pools_path,
                )

        self.assertEqual(generated.mapping["mission_title_only"], " <EM4>[200 Rep]</EM4>")
        self.assertIn("<EM4>##reputation_awarded##:</EM4> 80", generated.mapping["mission_desc_only"])
        self.assertIn("<EM4>##scenario_progress_points##:</EM4> 40", generated.mapping["mission_desc_only"])

    def test_load_contract_metadata_source_rejects_missing_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "contracts_metadata.json"
            metadata_path.write_text(json.dumps({"title_meta": {}}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "title_meta` o `description_meta"):
                load_contract_metadata_source(metadata_path)


if __name__ == "__main__":
    unittest.main()
