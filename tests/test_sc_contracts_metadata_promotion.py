from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAINTENANCE_DIR = REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "maintenance"
CORE_DIR = REPO_ROOT / ".codex" / "skills" / "sc-blueprint-extractor" / "scripts" / "core"

for candidate in (MAINTENANCE_DIR, CORE_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from promote_contract_metadata import build_promoted_payload  # noqa: E402


class ContractsMetadataPromotionTests(unittest.TestCase):
    def test_build_promoted_payload_filters_complex_pool_shapes(self) -> None:
        discovery = {
            "titles": {
                "Mission_Title": {
                    "blueprint_flag": True,
                    "blueprint_flag_uncertain": False,
                    "rep_ranges": ["100"],
                }
            },
            "descriptions": {
                "Mission_Desc": {
                    "reputation_awarded": ["100"],
                    "scenario_progress_points": ["50"],
                    "blueprint_variant_tiers": ["Jr. Contractor"],
                    "pool_headers": [],
                    "has_potential_blueprints_block": True,
                    "has_multiple_blueprint_pools": False,
                },
                "Complex_Desc": {
                    "reputation_awarded": [],
                    "scenario_progress_points": [],
                    "blueprint_variant_tiers": [],
                    "pool_headers": ["Pool 1", "Pool 2"],
                    "has_potential_blueprints_block": False,
                    "has_multiple_blueprint_pools": True,
                },
            },
            "blueprint_context": {
                "Mission_Desc": {
                    "classification": "new-tier-label-only",
                    "local_pool_ids": ["BP_POOL_SIMPLE"],
                },
                "Complex_Desc": {
                    "classification": "candidate-new-pool-shape",
                    "local_pool_ids": ["BP_POOL_A", "BP_POOL_B"],
                },
            },
        }

        payload, counts = build_promoted_payload(
            discovery_payload=discovery,
            source_path=REPO_ROOT / "data" / "starcitizen" / "reports" / "blueprints" / "contracts_metadata_candidates.json",
            allowed_classifications={"new-tier-label-only", "new-metadata-only", "already-covered"},
        )

        self.assertIn("Mission_Title", payload["title_meta"])
        self.assertIn("Mission_Desc", payload["description_meta"])
        self.assertNotIn("Complex_Desc", payload["description_meta"])
        self.assertEqual(payload["description_meta"]["Mission_Desc"]["tier_labels"], ["Jr. Contractor"])
        self.assertEqual(counts["descriptions_promoted"], 1)
        self.assertEqual(counts["descriptions_skipped"], 1)


if __name__ == "__main__":
    unittest.main()
