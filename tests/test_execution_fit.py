import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "tests" / "frozen_scenarios" / "execution_fit_private_repo_paid_feature_v1.json"
CAPACITY_SCENARIO = ROOT / "tests" / "frozen_scenarios" / "execution_fit_limited_task_capacity_v1.json"


class ExecutionFitContractTests(unittest.TestCase):
    def test_matrixloop_integrates_execution_fit_before_implementation(self):
        matrixloop = (ROOT / "docs" / "MATRIXLOOP.md").read_text(encoding="utf-8")
        self.assertIn("## Execution Fit", matrixloop)
        self.assertIn("Capability Fit", matrixloop)
        self.assertIn("Value Fit", matrixloop)
        self.assertIn("Operator Fit", matrixloop)
        self.assertLess(matrixloop.index("## Execution Fit"), matrixloop.index("## Stop rule"))

    def test_execution_fit_docs_are_bilingual_and_preserve_core_order(self):
        english = (ROOT / "docs" / "EXECUTION_FIT.md").read_text(encoding="utf-8")
        german = (ROOT / "docs" / "EXECUTION_FIT.de.md").read_text(encoding="utf-8")

        for term in ("Capability Fit", "Value Fit", "Operator Fit"):
            self.assertIn(term, english)
            self.assertIn(term, german)

        self.assertLess(english.index("Capability Fit"), english.index("Value Fit"))
        self.assertLess(english.index("Value Fit"), english.index("Operator Fit"))
        self.assertLess(german.index("Capability Fit"), german.index("Value Fit"))
        self.assertLess(german.index("Value Fit"), german.index("Operator Fit"))

        self.assertIn("demonstrated net benefit", english)
        self.assertIn("migration, learning, maintenance, lock-in and operator cost", english)
        self.assertIn("belegbarer Netto-Vorteil", german)
        self.assertIn("Wechsel-, Lern-, Wartungs-, Lock-in- und Operator-Kosten", german)
        self.assertNotIn("existing installed tools over new dependencies", english)
        self.assertNotIn("bereits installierte Werkzeuge statt neuer Abhängigkeiten", german)

    def test_private_repo_paid_feature_scenario_guards_operator_friction(self):
        data = json.loads(SCENARIO.read_text(encoding="utf-8"))

        self.assertEqual(data["schema"], "loop42-frozen-scenario-v1")
        self.assertEqual(data["basis"]["kind"], "simulated_fixture")
        self.assertFalse(data["input_state"]["current_entitlement_supports_enforcement"])
        self.assertTrue(data["input_state"]["simpler_viable_fallback_exists"])

        required = data["required_behavior"]
        self.assertEqual(
            required,
            [
                "verify_prerequisites_and_entitlement_first",
                "stop_the_blocked_route_before_downstream_setup",
                "evaluate_upgrade_value_against_cost_and_goal",
                "choose_the_lowest_friction_viable_fallback",
                "give_operator_steps_only_for_an_actionable_route",
            ],
        )

        bad = set(data["bad_behavior"])
        self.assertIn("give_detailed_setup_before_prerequisite_check", bad)
        self.assertIn("recommend_paid_upgrade_without_value_comparison", bad)

        expected = data["expected_outcome"]
        self.assertEqual(expected["operator_setup_steps_before_fit_check"], 0)
        self.assertEqual(expected["paid_actions"], 0)


    def test_operator_sovereignty_and_task_compression_are_explicit(self):
        english = (ROOT / "docs" / "EXECUTION_FIT.md").read_text(encoding="utf-8")
        german = (ROOT / "docs" / "EXECUTION_FIT.de.md").read_text(encoding="utf-8")

        self.assertIn("## Operator sovereignty", english)
        self.assertIn("## Task and automation compression", english)
        self.assertIn("Decision compression should reduce how often the operator is interrupted", english)
        self.assertIn("## Entscheidungshoheit des Operators", german)
        self.assertIn("## Aufgaben- und Automationskompression", german)
        self.assertIn("Decision Compression soll die Zahl der Unterbrechungen reduzieren", german)

    def test_limited_capacity_scenario_compresses_overlapping_watchers(self):
        data = json.loads(CAPACITY_SCENARIO.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "loop42-frozen-scenario-v1")
        self.assertEqual(data["input_state"]["task_slots_available"], 5)
        self.assertTrue(data["input_state"]["one_combined_scout_can_cover_sources"])

        required = set(data["required_behavior"])
        self.assertIn("compress_related_sources_into_one_coherent_task", required)
        self.assertIn("preserve_spare_task_capacity", required)
        self.assertIn("keep_protected_decisions_with_operator", required)

        expected = data["expected_outcome"]
        self.assertEqual(expected["new_persistent_tasks"], 1)
        self.assertEqual(expected["operator_manual_report_merge_steps"], 0)
        self.assertEqual(expected["protected_decisions_transferred_to_automation"], 0)


if __name__ == "__main__":
    unittest.main()
