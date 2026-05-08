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
    default_blueprint_source_paths,
    generate_blueprints_overlay_data,
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


if __name__ == "__main__":
    unittest.main()
