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

from blueprint_mission_review import CandidateMission, collect_candidates, shortlist_rows  # noqa: E402
from blueprint_reward_pool_review import build_pool_matches, choose_candidate_pool, collect_overlay_missions  # noqa: E402


class BlueprintExtractorReviewTests(unittest.TestCase):
    def test_collect_candidates_ignores_template_entries_and_requires_pool_overlap(self) -> None:
        global_map = {
            "mission_alpha_title": "Alpha Mission",
            "mission_alpha_desc": "Alpha description",
            "mission_beta_title": "Beta Mission",
            "mission_beta_desc": "Beta description",
        }
        template_map = {
            "mission_beta_title": "Already tracked",
        }
        pools = [
            "BP_MISSIONREWARD_ALPHA_COMBAT",
            "BP_MISSIONREWARD_GAMMA_MINING",
        ]

        candidates = collect_candidates(global_map=global_map, template_map=template_map, pools=pools)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title_key, "mission_alpha_title")
        self.assertEqual(candidates[0].desc_key, "mission_alpha_desc")
        self.assertEqual(candidates[0].candidate_pools, ["BP_MISSIONREWARD_ALPHA_COMBAT"])

    def test_shortlist_rows_filters_missing_desc_and_journal_entries(self) -> None:
        candidates = [
            CandidateMission(
                family="mission_alpha",
                title_key="mission_alpha_title",
                desc_key="mission_alpha_desc",
                title_text="Alpha Mission",
                candidate_pools=["BP_MISSIONREWARD_ALPHA_COMBAT"],
            ),
            CandidateMission(
                family="mission_journal",
                title_key="mission_journal_title",
                desc_key="mission_journal_desc",
                title_text="Journal Mission",
                candidate_pools=["BP_MISSIONREWARD_JOURNAL"],
            ),
            CandidateMission(
                family="mission_missing",
                title_key="mission_missing_title",
                desc_key=None,
                title_text="Missing Desc",
                candidate_pools=["BP_MISSIONREWARD_MISSING"],
            ),
        ]

        rows = shortlist_rows(candidates)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "`mission_alpha_title`")

    def test_collect_overlay_missions_links_desc_when_present(self) -> None:
        overlay_path = REPO_ROOT / "tests" / "_tmp_blueprints_overlay.ini"
        try:
            overlay_path.write_text(
                "\n".join(
                    [
                        "mission_alpha_title=Alpha",
                        "mission_alpha_desc=- @item_alpha@",
                        "mission_beta_title=Beta",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            missions = collect_overlay_missions(overlay_path)
        finally:
            overlay_path.unlink(missing_ok=True)

        self.assertEqual(
            [(mission.title_key, mission.desc_key) for mission in missions],
            [
                ("mission_alpha_title", "mission_alpha_desc"),
                ("mission_beta_title", None),
            ],
        )

    def test_build_pool_matches_and_choose_candidate_pool_use_token_overlap(self) -> None:
        missions = collect_overlay_missions_from_pairs(
            [
                ("mission_salvage_title", "mission_salvage_desc"),
                ("mission_mining_title", "mission_mining_desc"),
            ]
        )
        pools = [
            "BP_MISSIONREWARD_SALVAGE_RARE",
            "BP_MISSIONREWARD_MINING_COMMON",
        ]

        matches = build_pool_matches(pools, missions)

        self.assertEqual(matches["BP_MISSIONREWARD_SALVAGE_RARE"][0].title_key, "mission_salvage_title")
        pool_name, score = choose_candidate_pool("mission_mining_title", pools)
        self.assertEqual(pool_name, "BP_MISSIONREWARD_MINING_COMMON")
        self.assertGreater(score, 0)


def collect_overlay_missions_from_pairs(pairs: list[tuple[str, str | None]]):
    from blueprint_reward_pool_review import OverlayMission

    return [OverlayMission(title_key=title_key, desc_key=desc_key) for title_key, desc_key in pairs]


if __name__ == "__main__":
    unittest.main()
