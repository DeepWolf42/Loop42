import copy
import json
from pathlib import Path
import unittest

from tools.evaluation.agent_transcript import evaluate_agent_transcript


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = ROOT / "tests" / "frozen_scenarios" / "agent_transcript_eval_v1.json"

SCENARIO = {
    "schema": "loop42.agent-eval-scenario.v1",
    "scenario_id": "stale-capability-route-v1",
    "basis": {
        "kind": "simulated_fixture",
        "loop42_revision": "2ec351ec6ddc9dba455e8e75930e9aaee8dbe7c6",
    },
    "requirements": {
        "first_capability": "read_current_state",
        "capability_subsequence": [
            "read_current_state",
            "inspect_capability",
        ],
        "repeat_allowance": {},
        "max_input_validation_failures": 0,
        "require_evidence_citation": True,
        "required_answer_term_groups": [
            ["unknown", "unavailable", "limitation"],
            ["evidence", "observed"],
        ],
        "required_metrics": [
            "routing",
            "repetition",
            "validation",
            "evidence_use",
            "answer_contract",
            "overhead",
        ],
    },
}


def transcript():
    return {
        "schema": "loop42.agent-transcript.v1",
        "basis": {
            "scenario_id": "stale-capability-route-v1",
            "loop42_revision": "2ec351ec6ddc9dba455e8e75930e9aaee8dbe7c6",
            "harness_id": "fixture-harness",
            "harness_version": "1",
            "model_id": "fixture-model",
        },
        "capture_capabilities": {
            "tool_calls": True,
            "tool_results": True,
            "final_answer": True,
            "token_usage": True,
        },
        "events": [
            {
                "type": "tool_call",
                "call_id": "c1",
                "capability": "read_current_state",
                "arguments": {"target": "project"},
            },
            {
                "type": "tool_result",
                "call_id": "c1",
                "status": "success",
                "evidence_ids": ["evidence:state-current"],
            },
            {
                "type": "tool_call",
                "call_id": "c2",
                "capability": "inspect_capability",
                "arguments": {"capability": "paid-route"},
            },
            {
                "type": "tool_result",
                "call_id": "c2",
                "status": "unavailable",
                "evidence_ids": ["evidence:capability-missing"],
                "error_code": "capability_unavailable",
            },
            {
                "type": "final_answer",
                "text": (
                    "Observed evidence:state-current. "
                    "The requested route is unavailable; "
                    "evidence:capability-missing leaves that capability UNKNOWN."
                ),
            },
            {
                "type": "usage",
                "input_tokens": 800,
                "cached_input_tokens": 200,
                "output_tokens": 120,
            },
        ],
    }


class AgentTranscriptEvaluationTests(unittest.TestCase):
    def test_frozen_scenario_preserves_non_authority_and_real_run_gate(self):
        frozen = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(frozen["schema"], "loop42.agent-eval-scenario.v1")
        self.assertFalse(frozen["expected_boundary"]["evaluation_is_authority"])
        self.assertFalse(
            frozen["expected_boundary"]["missing_capture_fields_are_inferred"]
        )
        self.assertTrue(
            frozen["expected_boundary"][
                "real_harness_run_required_before_claiming_real_agent_quality"
            ]
        )

    def test_good_transcript_passes_with_explicit_basis_and_evidence(self):
        report = evaluate_agent_transcript(transcript(), SCENARIO)
        self.assertEqual(report["verdict"], "PASS")
        self.assertTrue(report["basis_match"])
        self.assertEqual(report["metrics"]["routing"]["status"], "PASS")
        self.assertEqual(report["metrics"]["evidence_use"]["status"], "PASS")
        self.assertEqual(report["authority"], "evaluation_evidence_only")

    def test_wrong_first_capability_fails(self):
        value = transcript()
        value["events"][0]["capability"] = "inspect_capability"
        report = evaluate_agent_transcript(value, SCENARIO)
        self.assertEqual(report["metrics"]["routing"]["status"], "FAIL")
        self.assertEqual(report["verdict"], "FAIL")

    def test_exact_duplicate_call_fails_by_default(self):
        value = transcript()
        duplicate = copy.deepcopy(value["events"][0])
        duplicate["call_id"] = "c1-repeat"
        value["events"].insert(2, duplicate)
        value["events"].insert(
            3,
            {
                "type": "tool_result",
                "call_id": "c1-repeat",
                "status": "success",
                "evidence_ids": [],
            },
        )
        report = evaluate_agent_transcript(value, SCENARIO)
        self.assertEqual(report["metrics"]["repetition"]["status"], "FAIL")
        self.assertEqual(
            report["metrics"]["repetition"]["disallowed_extra_calls"], 1
        )

    def test_scenario_can_allow_one_recheck_for_a_capability(self):
        value = transcript()
        duplicate = copy.deepcopy(value["events"][0])
        duplicate["call_id"] = "c1-repeat"
        value["events"].insert(2, duplicate)
        value["events"].insert(
            3,
            {
                "type": "tool_result",
                "call_id": "c1-repeat",
                "status": "success",
                "evidence_ids": [],
            },
        )
        scenario = copy.deepcopy(SCENARIO)
        scenario["requirements"]["repeat_allowance"] = {"read_current_state": 1}
        report = evaluate_agent_transcript(value, scenario)
        self.assertEqual(report["metrics"]["repetition"]["status"], "PASS")
        self.assertEqual(report["verdict"], "PASS")

    def test_invalid_tool_input_is_measured(self):
        value = transcript()
        value["events"][3]["status"] = "error"
        value["events"][3]["error_code"] = "invalid_request"
        report = evaluate_agent_transcript(value, SCENARIO)
        self.assertEqual(report["metrics"]["validation"]["status"], "FAIL")
        self.assertEqual(report["verdict"], "FAIL")

    def test_evidence_must_be_cited_when_required(self):
        value = transcript()
        value["events"][4]["text"] = (
            "Observed state, but the capability is unavailable."
        )
        report = evaluate_agent_transcript(value, SCENARIO)
        self.assertEqual(report["metrics"]["evidence_use"]["status"], "FAIL")
        self.assertEqual(report["verdict"], "FAIL")

    def test_missing_capture_capability_stays_unknown(self):
        value = transcript()
        value["capture_capabilities"]["token_usage"] = False
        value["events"] = [
            event for event in value["events"] if event["type"] != "usage"
        ]
        report = evaluate_agent_transcript(value, SCENARIO)
        self.assertEqual(report["metrics"]["overhead"]["status"], "UNKNOWN")
        self.assertEqual(report["verdict"], "UNKNOWN")

    def test_basis_drift_fails_even_when_content_looks_good(self):
        value = transcript()
        value["basis"]["loop42_revision"] = (
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        report = evaluate_agent_transcript(value, SCENARIO)
        self.assertFalse(report["basis_match"])
        self.assertEqual(report["verdict"], "FAIL")

    def test_result_for_uncaptured_call_fails_closed(self):
        value = transcript()
        value["events"].insert(
            2,
            {
                "type": "tool_result",
                "call_id": "foreign",
                "status": "success",
                "evidence_ids": [],
            },
        )
        with self.assertRaises(ValueError):
            evaluate_agent_transcript(value, SCENARIO)

    def test_nonfinite_arguments_fail_closed(self):
        value = transcript()
        value["events"][0]["arguments"] = {"threshold": float("nan")}
        with self.assertRaises(ValueError):
            evaluate_agent_transcript(value, SCENARIO)


if __name__ == "__main__":
    unittest.main()
