"""Synthetic negative controls: these do not measure actual model quality."""

import copy
import unittest
from tools.checks.refinement_trial import evaluate_refinement_trial


def fixture():
    revision, s1, s2, before, after = "a" * 40, "7" * 64, "8" * 64, "1" * 64, "2" * 64

    def case(ident, kind, scenario, original, revised):
        def run(result, prompt, receipt):
            return dict(result=result, source_revision=revision, prompt_sha256=prompt,
                        scenario_sha256=scenario, verifier_id="independent-check",
                        verifier_revision="b" * 40, harness_id="harness:0.1", model_id="model:fixed",
                        evidence_sha256=receipt * 64)
        return dict(scenario_id=ident, scenario_sha256=scenario, kind=kind,
                    baseline=run(original, before, "3"), candidate=run(revised, after, "4"))

    return dict(schema="loop42.refinement-trial.v1", source_revision=revision,
                baseline_prompt_sha256=before, candidate_prompt_sha256=after,
                lesson="Check entitlement before recommending paid setup.", cases=[
                    case("blocked-feature", "target", s1, "FAIL", "PASS"),
                    case("known-good", "holdout", s2, "PASS", "PASS"),
                ])


class RefinementTrialTests(unittest.TestCase):
    def assert_status(self, expected, transform=None):
        d = fixture()
        if transform:
            transform(d)
        self.assertEqual(evaluate_refinement_trial(d).status, expected)

    def test_improved_target_and_preserved_holdout_only_promising(self):
        self.assert_status("PROMISING")

    def test_regression_rejected(self):
        self.assert_status("REJECT", lambda d: d["cases"][1]["candidate"].update(result="FAIL"))

    def test_no_target_improvement_inconclusive(self):
        self.assert_status("INCONCLUSIVE", lambda d: d["cases"][0]["baseline"].update(result="PASS"))

    def test_unknown_inconclusive(self):
        self.assert_status("INCONCLUSIVE", lambda d: d["cases"][1]["candidate"].update(result="UNKNOWN"))

    def test_broken_holdout_not_safety_evidence(self):
        def change(d):
            d["cases"][1]["baseline"]["result"] = "FAIL"
            d["cases"][1]["candidate"]["result"] = "FAIL"
        self.assert_status("INCONCLUSIVE", change)

    def test_fixed_holdout_not_safety_evidence(self):
        self.assert_status("INCONCLUSIVE", lambda d: d["cases"][1]["baseline"].update(result="FAIL"))

    def test_all_holdouts_must_be_preserved(self):
        def change(d):
            bad = copy.deepcopy(d["cases"][1])
            bad["scenario_id"] = "other"
            bad["baseline"]["result"] = bad["candidate"]["result"] = "FAIL"
            d["cases"].append(bad)
        self.assert_status("INCONCLUSIVE", change)

    def test_target_only_not_a_trial(self):
        self.assert_status("INCONCLUSIVE", lambda d: d["cases"][1].update(kind="target"))

    def test_prompt_mismatch_rejected(self):
        def change(d):
            d["cases"][0]["candidate"]["prompt_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "mismatched"):
            evaluate_refinement_trial(self._changed(change))

    def test_scenario_mismatch_rejected(self):
        def change(d):
            d["cases"][0]["candidate"]["scenario_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "mismatched"):
            evaluate_refinement_trial(self._changed(change))

    def test_stale_source_rejected(self):
        def change(d):
            d["cases"][0]["candidate"]["source_revision"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "stale"):
            evaluate_refinement_trial(self._changed(change))

    def test_foreign_harness_rejected(self):
        def change(d):
            d["cases"][0]["candidate"]["harness_id"] = "other"
        with self.assertRaisesRegex(ValueError, "harness/model"):
            evaluate_refinement_trial(self._changed(change))

    def test_foreign_model_rejected(self):
        def change(d):
            d["cases"][1]["candidate"]["model_id"] = "other-model"
        with self.assertRaisesRegex(ValueError, "harness/model"):
            evaluate_refinement_trial(self._changed(change))

    def test_per_scenario_verifiers_allowed(self):
        def change(d):
            for arm in ("baseline", "candidate"):
                d["cases"][1][arm]["verifier_id"] = "another-independent-check"
        self.assert_status("PROMISING", change)

    def test_different_verifiers_per_arm_rejected(self):
        def change(d):
            d["cases"][1]["candidate"]["verifier_id"] = "self-grader"
        with self.assertRaisesRegex(ValueError, "verifier"):
            evaluate_refinement_trial(self._changed(change))

    def test_duplicate_scenario_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluate_refinement_trial(self._changed(lambda d: d["cases"][1].update(scenario_id=d["cases"][0]["scenario_id"])))

    def test_same_verifier_id_with_different_revision_per_arm_rejected(self):
        for index in (0, 1):
            d = fixture()
            before, after = d["cases"][index]["baseline"], d["cases"][index]["candidate"]
            self.assertEqual(before["verifier_id"], after["verifier_id"])
            after["verifier_revision"] = "c" * 40
            with self.subTest(kind=d["cases"][index]["kind"]), self.assertRaisesRegex(ValueError, "verifier"):
                evaluate_refinement_trial(d)

    def test_unknown_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "exact"):
            evaluate_refinement_trial(self._changed(lambda d: d.update(auto_apply=True)))

    def test_self_reported_pass_not_accepted_as_state(self):
        with self.assertRaisesRegex(ValueError, "result"):
            evaluate_refinement_trial(self._changed(lambda d: d["cases"][0]["candidate"].update(result="SELF_REPORT_PASS")))

    def test_empty_identical_instruction_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, "no identifiable"):
            evaluate_refinement_trial(self._changed(lambda d: d.update(candidate_prompt_sha256=d["baseline_prompt_sha256"])))

    def test_invalid_case_result_type_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid result"):
            evaluate_refinement_trial(self._changed(lambda d: d["cases"][0]["baseline"].update(result=[])))

    @staticmethod
    def _changed(f):
        d = fixture()
        f(d)
        return d


if __name__ == "__main__":
    unittest.main()
