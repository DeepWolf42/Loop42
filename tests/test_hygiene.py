import unittest

from tools.checks.hygiene import (
    HygieneCategory,
    HygieneEvidence,
    HygieneItem,
    HygieneKind,
    _load_json,
    classify_hygiene,
    hygiene_report,
)


class HygieneTests(unittest.TestCase):
    def item(self, *, kind=HygieneKind.FILE, protected=False, **evidence):
        basis = {"fresh": True, "complete": True}
        basis.update(evidence)
        return HygieneItem(
            item_id="item:test",
            kind=kind,
            protected=protected,
            evidence=HygieneEvidence(**basis),
        )

    def test_core_categories_from_explicit_fresh_evidence(self):
        cases = (
            (self.item(active=True), HygieneCategory.ACTIVE),
            (self.item(historical=True), HygieneCategory.HISTORICAL),
            (self.item(superseded=True), HygieneCategory.SUPERSEDED),
            (
                self.item(kind=HygieneKind.BRANCH, merged=True),
                HygieneCategory.MERGED_BRANCH,
            ),
            (
                self.item(duplicate_candidate=True),
                HygieneCategory.DUPLICATE_CANDIDATE,
            ),
            (self.item(referenced=False), HygieneCategory.ORPHANED),
            (self.item(stale_reference=True), HygieneCategory.STALE_REFERENCE),
            (self.item(), HygieneCategory.UNKNOWN),
        )
        for item, expected in cases:
            with self.subTest(expected=expected):
                result = classify_hygiene(item)
                self.assertEqual(result.category, expected)
                self.assertFalse(result.destructive_action_allowed)

    def test_stale_or_incomplete_evidence_stays_unknown(self):
        for item in (self.item(fresh=False), self.item(complete=False)):
            with self.subTest(item=item):
                self.assertEqual(
                    classify_hygiene(item).category,
                    HygieneCategory.UNKNOWN,
                )

    def test_same_name_or_missing_duplicate_proof_does_not_create_duplicate(self):
        result = classify_hygiene(self.item(duplicate_candidate=False))
        self.assertEqual(result.category, HygieneCategory.UNKNOWN)

    def test_protected_cleanup_candidate_is_never_deletion_authority(self):
        result = classify_hygiene(
            self.item(kind=HygieneKind.BRANCH, protected=True, merged=True)
        )
        self.assertEqual(result.category, HygieneCategory.MERGED_BRANCH)
        self.assertTrue(result.cleanup_candidate)
        self.assertIn("protected_retention_guard", result.reasons)
        self.assertFalse(result.destructive_action_allowed)

    def test_merged_evidence_is_branch_only(self):
        with self.assertRaises(ValueError):
            self.item(kind=HygieneKind.FILE, merged=True)

    def test_report_is_deterministic_and_never_authorizes_destruction(self):
        request = {
            "schema": "loop42.hygiene-input.v1",
            "scope": "github:DeepWolf42/Loop42",
            "items": [
                {
                    "item_id": "branch:old",
                    "kind": "branch",
                    "protected": False,
                    "evidence": {
                        "fresh": True,
                        "complete": True,
                        "merged": True,
                    },
                },
                {
                    "item_id": "doc:current",
                    "kind": "document",
                    "protected": True,
                    "evidence": {
                        "fresh": True,
                        "complete": True,
                        "active": True,
                    },
                },
            ],
        }
        report = hygiene_report(request)
        reverse = dict(request)
        reverse["items"] = list(reversed(request["items"]))
        report_reverse = hygiene_report(reverse)
        self.assertEqual(report["fingerprint"], report_reverse["fingerprint"])
        self.assertFalse(report["destructive_actions_allowed"])
        self.assertEqual(report["counts"]["merged_branch"], 1)
        self.assertEqual(report["counts"]["active"], 1)

    def test_strict_json_and_unknown_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            _load_json(b'{"schema":"x","schema":"y"}')
        with self.assertRaises(ValueError):
            hygiene_report(
                {
                    "schema": "loop42.hygiene-input.v1",
                    "scope": "repo:test",
                    "items": [],
                    "surprise": True,
                }
            )

    def test_duplicate_item_ids_fail_closed(self):
        item = {
            "item_id": "file:x",
            "kind": "file",
            "protected": False,
            "evidence": {"fresh": True, "complete": True},
        }
        with self.assertRaises(ValueError):
            hygiene_report(
                {
                    "schema": "loop42.hygiene-input.v1",
                    "scope": "repo:test",
                    "items": [item, dict(item)],
                }
            )


if __name__ == "__main__":
    unittest.main()
