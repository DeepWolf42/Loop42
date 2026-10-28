from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ExternalPatternScoutTests(unittest.TestCase):
    def test_contract_is_bounded_and_non_authoritative(self):
        text = (ROOT / "docs/EXTERNAL_PATTERN_SCOUT.md").read_text(encoding="utf-8")
        self.assertIn("not a new source of truth", text)
        self.assertIn("candidate limit", text)
        self.assertIn("time/run budget", text)
        self.assertIn("Discovery is not adoption", text)
        self.assertIn("Direct code reuse requires", text)
        self.assertIn("Search for the **problem**", text)
        self.assertIn("adjacent disciplines", text)
        self.assertIn("A similar product is neither required nor sufficient", text)
        self.assertIn("## Perspective probe", text)
        self.assertIn("downstream lens", text)
        self.assertIn("inversion lens", text)
        self.assertIn("outside lens", text)
        self.assertIn("not a brainstorming quota", text)

    def test_consumer_truth_boundary_is_explicit(self):
        text = (ROOT / "docs/EXTERNAL_PATTERN_SCOUT.md").read_text(encoding="utf-8")
        self.assertIn("Consumer projects decide", text)
        self.assertIn("without importing another project's product semantics", text)

    def test_frozen_scenario_guards_adoption(self):
        path = ROOT / "tests/frozen_scenarios/external_pattern_scout_v1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = data["expected"]
        self.assertTrue(expected["must_not_auto_adopt"])
        self.assertTrue(expected["must_record_source_and_freshness"])
        self.assertTrue(expected["must_compare_value_to_cost"])
        self.assertTrue(expected["must_preserve_consumer_truth_boundary"])
        self.assertTrue(expected["direct_code_reuse_requires_license_review"])
        self.assertTrue(expected["must_search_adjacent_domains"])
        self.assertTrue(expected["must_not_require_similar_product"])
        self.assertTrue(expected["must_probe_downstream_effects"])
        self.assertTrue(expected["must_probe_alternate_frame"])
        self.assertTrue(expected["must_bound_perspective_probe"])
        self.assertEqual(expected["preferred_candidate"], "SmallCheckpointPattern")



    def test_gap_detection_is_bounded_and_reuse_first(self):
        text = (ROOT / "docs/EXTERNAL_PATTERN_SCOUT.md").read_text(encoding="utf-8")
        german = (ROOT / "docs/EXTERNAL_PATTERN_SCOUT.de.md").read_text(encoding="utf-8")
        self.assertIn("## Gap detection and reuse gate", text)
        self.assertIn("RECONCILE / TARGET", text)
        self.assertIn("not a new", text)
        self.assertIn("CHECKED_NO_DELTA", text)
        self.assertIn("USEFUL_CANDIDATE", text)
        self.assertIn("NOT_SEARCHED", text)
        self.assertIn("BLOCKED_UNKNOWN", text)
        self.assertIn("NOT_SEARCHED is not NO_USEFUL_DELTA", text)
        self.assertIn("REUSE_EXISTING", text)
        self.assertIn("SMALL_ADAPTER", text)
        self.assertIn("previous valid coverage", text)
        self.assertIn("Consumer-specific findings", text)
        self.assertIn("## Lückenerkennung und Wiederverwendungsprüfung", german)
        for status in ("CHECKED_NO_DELTA", "USEFUL_CANDIDATE", "NOT_SEARCHED", "BLOCKED_UNKNOWN"):
            self.assertIn(status, german)

    def test_unsearched_and_inaccessible_areas_cannot_count_as_no_delta(self):
        path = ROOT / "tests/frozen_scenarios/external_pattern_scout_v1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(data["fixture"]["coverage"]["not_searched"])
        self.assertTrue(data["fixture"]["coverage"]["blocked_unknown"])
        expected = data["expected"]
        for key in (
            "must_check_existing_capabilities_first",
            "must_distinguish_unsearched_from_no_delta",
            "must_keep_inaccessible_sources_unknown",
            "must_prioritize_bounded_blind_spots",
            "must_preserve_existing_loop_and_consumer_truth",
        ):
            self.assertTrue(expected[key], key)


    def test_matrixloop_and_gaps_reuse_the_same_probe(self):
        matrixloop = (ROOT / "docs/MATRIXLOOP.md").read_text(encoding="utf-8")
        gaps = (ROOT / "docs/TRUTH_AND_GAPS.md").read_text(encoding="utf-8")
        gaps_de = (ROOT / "docs/TRUTH_AND_GAPS.de.md").read_text(encoding="utf-8")
        self.assertIn("gap detection and reuse gate", matrixloop)
        self.assertIn("not an extra Matrixloop stage", matrixloop)
        self.assertIn("NOT_SEARCHED", matrixloop)
        self.assertIn("research-coverage gap", gaps)
        self.assertIn("external pattern scout", gaps)
        self.assertIn("REUSE_EXISTING", gaps)
        self.assertIn("NOT_SEARCHED", gaps_de)
        self.assertIn("BLOCKED_UNKNOWN", gaps_de)
        self.assertIn("REUSE_EXISTING", gaps_de)

if __name__ == "__main__":
    unittest.main()
