import unittest

from tools.checks.consumer_profile import validate_profile


REVISION = "1" * 40


def profile():
    return {
        "schema": "loop42.consumer-profile.v1",
        "loop42": {
            "repository": "Example/Loop42",
            "revision": REVISION,
        },
        "consumer": {
            "name": "Example",
            "repository": "Example/Project",
            "context_manifest": "project-context.json",
            "canonical_sources": {
                "project_state": "docs/CURRENT_PROJECT_STATE.md",
                "recovery": "docs/CURRENT_PROJECT_STATE.md",
            },
        },
        "capabilities": [
            "context.snapshot",
            "context.checkpoint",
            "harness.ollama.proposal",
        ],
        "authority": {
            "product_truth": "consumer",
            "recovery": "consumer",
            "execution": "consumer-policy",
        },
        "evidence": {
            "equivalence_suite": "example-equivalence-v1",
            "status": "verified",
            "verified_loop42_revision": REVISION,
        },
    }


class ConsumerProfileTests(unittest.TestCase):
    def test_valid_exact_revision_profile(self):
        result = validate_profile(profile(), expected_revision=REVISION)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["loop42_revision"], REVISION)

    def test_branch_name_is_not_a_revision_pin(self):
        value = profile()
        value["loop42"]["revision"] = "main"
        with self.assertRaisesRegex(ValueError, "40-hex"):
            validate_profile(value)

    def test_stale_expected_revision_fails_visibly(self):
        with self.assertRaisesRegex(ValueError, "stale Loop42 revision pin"):
            validate_profile(profile(), expected_revision="2" * 40)

    def test_evidence_revision_must_match_pin(self):
        value = profile()
        value["evidence"]["verified_loop42_revision"] = "2" * 40
        with self.assertRaisesRegex(ValueError, "must equal"):
            validate_profile(value)

    def test_product_truth_cannot_move_into_loop42(self):
        value = profile()
        value["authority"]["product_truth"] = "loop42"
        with self.assertRaisesRegex(ValueError, "authority boundary"):
            validate_profile(value)

    def test_recovery_cannot_move_into_loop42(self):
        value = profile()
        value["authority"]["recovery"] = "loop42"
        with self.assertRaisesRegex(ValueError, "authority boundary"):
            validate_profile(value)

    def test_capabilities_are_explicit_unique_opt_ins(self):
        value = profile()
        value["capabilities"].append("context.snapshot")
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_profile(value)


if __name__ == "__main__":
    unittest.main()
