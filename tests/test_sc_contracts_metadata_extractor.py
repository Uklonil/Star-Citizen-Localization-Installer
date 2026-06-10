from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "review"
CORE_DIR = REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "core"
SCRIPTS_DIR = REPO_ROOT / "scripts"

for candidate in (REVIEW_DIR, CORE_DIR, SCRIPTS_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from extract_contract_metadata_candidates import (  # noqa: E402
    build_payload,
    classify_blueprint_context,
    normalize_key,
    parse_description_metadata,
    parse_title_metadata,
)


class ContractsMetadataExtractorTests(unittest.TestCase):
    def test_parse_title_metadata_extracts_bp_and_rep_ranges(self) -> None:
        value = "Urgent Refuel <EM4>[150 Rep] [BP]*</EM4>"

        meta = parse_title_metadata(value)

        self.assertIsNotNone(meta)
        assert meta is not None
        self.assertTrue(meta["blueprint_flag"])
        self.assertTrue(meta["blueprint_flag_uncertain"])
        self.assertEqual(meta["rep_ranges"], ["150"])

    def test_parse_description_metadata_extracts_tiers_points_and_pool_headers(self) -> None:
        value = (
            "Hello\\n\\n"
            "<EM4>Scenario Progress Points 45</EM4>\\n"
            "<EM4>Reputation Awarded (by difficulty):</EM4> 50 / 200\\n\\n"
            "<EM4>Multiple Blueprint Pools (Yormandi Eye Only)</EM4>\\n"
            "<EM4>Awarded from Sr. Contractor level variants</EM4>\\n"
            "<EM4>Pool 1</EM4>\\n"
            "- Item Alpha\\n"
            "<EM4>Pool 2</EM4>\\n"
            "- Item Beta\\n"
        )

        meta = parse_description_metadata(value)

        self.assertIsNotNone(meta)
        assert meta is not None
        self.assertEqual(meta["scenario_progress_points"], ["45"])
        self.assertEqual(meta["reputation_awarded"], ["50 / 200"])
        self.assertEqual(meta["blueprint_variant_tiers"], ["Sr. Contractor"])
        self.assertEqual(meta["pool_headers"], ["Pool 1", "Pool 2"])
        self.assertTrue(meta["has_multiple_blueprint_pools"])
        self.assertIn("- Item Alpha", meta["raw_block_lines"])

    def test_classify_blueprint_context_detects_new_tier_only_and_new_metadata(self) -> None:
        tier_meta = {
            "blueprint_variant_tiers": ["Master"],
            "pool_headers": [],
            "has_potential_blueprints_block": True,
            "has_multiple_blueprint_pools": False,
            "raw_block_lines": ["- Item"],
        }
        metadata_only = {
            "blueprint_variant_tiers": [],
            "pool_headers": [],
            "has_potential_blueprints_block": False,
            "has_multiple_blueprint_pools": False,
            "raw_block_lines": [],
        }

        tier_context = classify_blueprint_context(
            normalized_key="mission_desc",
            desc_meta=tier_meta,
            normalized_pool_map={"mission_desc": "BP_POOL"},
        )
        metadata_context = classify_blueprint_context(
            normalized_key="mission_desc",
            desc_meta=metadata_only,
            normalized_pool_map={},
        )

        self.assertEqual(tier_context["classification"], "new-tier-label-only")
        self.assertEqual(metadata_context["classification"], "new-metadata-only")

    def test_build_payload_normalizes_keys_against_local_global(self) -> None:
        contracts_map = {
            "Mission_Title,P": "Title <EM4>[50 Rep]</EM4>",
            "Mission_Desc,P": (
                "Body\\n<EM4>Reputation Awarded:</EM4> 100\\n"
                "<EM4>Potential Blueprints</EM4>\\n"
                "- Item One\\n"
            ),
        }
        global_map = {
            "Mission_Title": "Title",
            "Mission_Desc": "Desc",
        }

        payload = build_payload(
            contracts_map=contracts_map,
            global_map=global_map,
            normalized_pool_map={"Mission_Desc": "BP_POOL"},
        )

        self.assertIn("Mission_Title,P", payload["titles"])
        self.assertIn("Mission_Desc,P", payload["descriptions"])
        self.assertTrue(payload["descriptions"]["Mission_Desc,P"]["present_in_local_global"])
        self.assertEqual(payload["blueprint_context"]["Mission_Desc,P"]["classification"], "already-covered")

    def test_normalize_key_removes_suffix_and_bom(self) -> None:
        self.assertEqual(normalize_key("\ufeffMission_Desc,P"), "Mission_Desc")


if __name__ == "__main__":
    unittest.main()
