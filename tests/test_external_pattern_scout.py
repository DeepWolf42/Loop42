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
        self.assertEqual(expected["preferred_candidate"], "SmallCheckpointPattern")


if __name__ == "__main__":
    unittest.main()
