import unittest

from tools.harness.change_set import ChangeSet, CreateChange
from tools.harness.worker_provider import (
    WorkerRequest,
    WorkerResult,
    WorkerStatus,
    WorkerUsage,
)


class WorkerProviderContractTests(unittest.TestCase):
    def request(self):
        return WorkerRequest(
            task_id="task-1",
            attempt_id="attempt-1",
            source_revision="abcdef1",
            context_fingerprint="a" * 64,
            task="Add a bounded file.",
            context="repo snapshot",
            allowed_capabilities=("propose_changes", "request_verification"),
        )

    def test_request_is_provider_neutral_and_bounded(self):
        request = self.request()
        self.assertEqual(request.requested_role, "general")
        self.assertEqual(request.allowed_capabilities[0], "propose_changes")

    def test_proposal_requires_changeset(self):
        request = self.request()
        result = WorkerResult(
            status=WorkerStatus.PROPOSAL,
            provider="example",
            model="model-x",
            task_id=request.task_id,
            attempt_id=request.attempt_id,
            source_revision=request.source_revision,
            context_fingerprint=request.context_fingerprint,
            rationale_summary="Create the requested file.",
            changeset=ChangeSet((CreateChange("x.txt", "hello\n"),)),
            usage=WorkerUsage(input_tokens=10, output_tokens=5, cost_microunits=0),
            raw_response_fingerprint="b" * 64,
        )
        self.assertEqual(result.status, WorkerStatus.PROPOSAL)
        self.assertIsNotNone(result.changeset)

    def test_failed_or_blocked_result_must_not_carry_changes(self):
        request = self.request()
        for status in (WorkerStatus.FAILED, WorkerStatus.BLOCKED):
            with self.assertRaisesRegex(ValueError, "only proposal"):
                WorkerResult(
                    status=status,
                    provider="example",
                    model="model-x",
                    task_id=request.task_id,
                    attempt_id=request.attempt_id,
                    source_revision=request.source_revision,
                    context_fingerprint=request.context_fingerprint,
                    rationale_summary="blocked",
                    changeset=ChangeSet((CreateChange("x.txt", "hello"),)),
                )

    def test_shell_capability_text_and_negative_usage_fail_closed(self):
        with self.assertRaises(ValueError):
            WorkerRequest(
                task_id="task-1",
                attempt_id="attempt-1",
                source_revision="abcdef1",
                context_fingerprint="a" * 64,
                task="x",
                context="x",
                allowed_capabilities=("run pytest -q",),
            )
        with self.assertRaises(ValueError):
            WorkerUsage(input_tokens=-1)


if __name__ == "__main__":
    unittest.main()
