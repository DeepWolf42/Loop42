import unittest
from datetime import datetime, timezone

from tools.harness.verification_receipt import (
    CriterionStatus,
    CriterionVerification,
    EvidenceRef,
    VerificationReceipt,
    receipt_fingerprint,
    validate_receipt,
)
from tools.harness.worker_dispatch import DispatchTask

NOW = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc)
REV = "a" * 40
CTX = "b" * 64
SUBJECT = "c" * 64
EVIDENCE = "d" * 64
VERIFIER_REV = "e" * 40


def task():
    return DispatchTask(
        "review-cora",
        "attempt-1",
        REV,
        CTX,
        ("tests are green", "output matches requested scope"),
    )


def receipt(*, status=CriterionStatus.PASS, subject=SUBJECT, attempt="attempt-1"):
    criteria = tuple(
        CriterionVerification(
            criterion,
            status,
            (EvidenceRef(f"test:{index}", EVIDENCE),),
        )
        for index, criterion in enumerate(task().acceptance_criteria, start=1)
    )
    return VerificationReceipt(
        task_id="review-cora",
        attempt_id=attempt,
        source_revision=REV,
        context_fingerprint=CTX,
        subject_fingerprint=subject,
        verifier_id="loop42:test-suite",
        verifier_revision=VERIFIER_REV,
        verified_at=NOW,
        criteria=criteria,
    )


class VerificationReceiptTests(unittest.TestCase):
    def test_exact_pass_receipt_validates_and_is_deterministic(self):
        value = receipt()
        first = validate_receipt(value, task(), subject_fingerprint=SUBJECT)
        second = validate_receipt(value, task(), subject_fingerprint=SUBJECT)
        self.assertTrue(first.valid)
        self.assertEqual(first.reasons, ())
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(first.fingerprint, receipt_fingerprint(value))
        self.assertEqual(len(first.fingerprint), 64)

    def test_receipt_fingerprint_changes_with_verified_subject(self):
        first = receipt_fingerprint(receipt(subject="c" * 64))
        second = receipt_fingerprint(receipt(subject="f" * 64))
        self.assertNotEqual(first, second)

    def test_wrong_attempt_fails_identity_validation(self):
        result = validate_receipt(receipt(attempt="attempt-2"), task())
        self.assertFalse(result.valid)
        self.assertIn("task_identity_mismatch", result.reasons)

    def test_failed_or_unknown_criterion_is_not_success(self):
        for status in (CriterionStatus.FAIL, CriterionStatus.UNKNOWN):
            with self.subTest(status=status):
                result = validate_receipt(receipt(status=status), task())
                self.assertFalse(result.valid)
                self.assertIn("acceptance_not_fully_passed", result.reasons)

    def test_omitted_or_reordered_acceptance_criteria_fail_closed(self):
        value = receipt()
        omitted = VerificationReceipt(
            task_id=value.task_id,
            attempt_id=value.attempt_id,
            source_revision=value.source_revision,
            context_fingerprint=value.context_fingerprint,
            subject_fingerprint=value.subject_fingerprint,
            verifier_id=value.verifier_id,
            verifier_revision=value.verifier_revision,
            verified_at=value.verified_at,
            criteria=value.criteria[:1],
        )
        self.assertIn(
            "acceptance_criteria_mismatch",
            validate_receipt(omitted, task()).reasons,
        )
        reordered = VerificationReceipt(
            task_id=value.task_id,
            attempt_id=value.attempt_id,
            source_revision=value.source_revision,
            context_fingerprint=value.context_fingerprint,
            subject_fingerprint=value.subject_fingerprint,
            verifier_id=value.verifier_id,
            verifier_revision=value.verifier_revision,
            verified_at=value.verified_at,
            criteria=tuple(reversed(value.criteria)),
        )
        self.assertIn(
            "acceptance_criteria_mismatch",
            validate_receipt(reordered, task()).reasons,
        )

    def test_pass_requires_evidence(self):
        with self.assertRaisesRegex(ValueError, "PASS criteria require"):
            CriterionVerification(
                "tests are green",
                CriterionStatus.PASS,
                (),
            )

    def test_subject_mismatch_is_not_valid(self):
        result = validate_receipt(
            receipt(),
            task(),
            subject_fingerprint="f" * 64,
        )
        self.assertFalse(result.valid)
        self.assertIn("subject_fingerprint_mismatch", result.reasons)

    def test_receipt_hash_is_not_claimed_as_authentication(self):
        value = receipt()
        self.assertTrue(validate_receipt(value, task()).valid)
        self.assertEqual(value.verifier_id, "loop42:test-suite")


if __name__ == "__main__":
    unittest.main()
