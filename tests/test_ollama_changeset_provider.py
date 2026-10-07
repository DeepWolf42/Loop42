import json
import unittest
from unittest import mock

from tools.harness.change_set import sha256_text
from tools.harness.ollama_changeset_provider import OllamaChangeSetProvider, _payload
from tools.harness.worker_provider import WorkerRequest, WorkerStatus


class OllamaChangeSetProviderTests(unittest.TestCase):
    def request(self, capabilities=("propose_changes", "request_verification")):
        return WorkerRequest(
            task_id="task-1",
            attempt_id="attempt-1",
            source_revision="abcdef1",
            context_fingerprint="a" * 64,
            task="Change x.",
            context="x.py currently contains x = 1",
            allowed_capabilities=capabilities,
        )

    def proposal(self):
        return {
            "rationale_summary": "Change the evidenced assignment.",
            "evidence": ["x.py"],
            "changeset": {
                "schema": "loop42.changeset.v1",
                "changes": [{
                    "operation": "modify",
                    "path": "x.py",
                    "base_sha256": sha256_text("x = 1\n"),
                    "search": "x = 1",
                    "replace": "x = 2",
                    "expected_matches": 1,
                }],
                "requested_verification": ["unit:x"],
            },
        }

    def test_payload_is_structured_proposal_only(self):
        payload = _payload(self.request(), "model-x")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["options"]["temperature"], 0)
        self.assertEqual(payload["format"]["properties"]["changeset"]["properties"]["schema"]["const"], "loop42.changeset.v1")
        self.assertIn("never return terminal commands", payload["messages"][0]["content"])

    def test_missing_capability_blocks_without_network(self):
        provider = OllamaChangeSetProvider("model-x")
        with mock.patch("tools.harness.ollama_changeset_provider.ollama_http") as http:
            result = provider.run(self.request(capabilities=("request_verification",)))
        http.assert_not_called()
        self.assertEqual(result.status, WorkerStatus.BLOCKED)

    def test_missing_model_blocks_without_implicit_download(self):
        provider = OllamaChangeSetProvider("model-x")
        with mock.patch("tools.harness.ollama_changeset_provider.ollama_http", return_value={"models": []}) as http:
            result = provider.run(self.request())
        self.assertEqual(result.status, WorkerStatus.BLOCKED)
        self.assertEqual(http.call_count, 1)

    def test_valid_response_maps_to_provider_neutral_result(self):
        provider = OllamaChangeSetProvider("model-x")
        response = {
            "model": "model-x:latest",
            "done": True,
            "message": {"content": json.dumps(self.proposal())},
            "prompt_eval_count": 100,
            "eval_count": 20,
        }
        with mock.patch("tools.harness.ollama_changeset_provider.ollama_http", side_effect=[{"models": [{"name": "model-x"}]}, response]):
            result = provider.run(self.request())
        self.assertEqual(result.status, WorkerStatus.PROPOSAL)
        self.assertEqual(result.task_id, "task-1")
        self.assertEqual(result.changeset.changes[0].path, "x.py")
        self.assertEqual(result.usage.input_tokens, 100)
        self.assertEqual(len(result.raw_response_fingerprint), 64)

    def test_verification_request_without_capability_fails_closed(self):
        provider = OllamaChangeSetProvider("model-x")
        response = {
            "model": "model-x",
            "done": True,
            "message": {"content": json.dumps(self.proposal())},
        }
        with mock.patch(
            "tools.harness.ollama_changeset_provider.ollama_http",
            side_effect=[{"models": [{"name": "model-x"}]}, response],
        ):
            with self.assertRaisesRegex(ValueError, "invalid structured worker proposal"):
                provider.run(self.request(capabilities=("propose_changes",)))

    def test_extra_or_malformed_fields_fail_closed(self):
        provider = OllamaChangeSetProvider("model-x")
        bad = self.proposal()
        bad["surprise"] = True
        response = {"model": "model-x", "done": True, "message": {"content": json.dumps(bad)}}
        with mock.patch("tools.harness.ollama_changeset_provider.ollama_http", side_effect=[{"models": [{"name": "model-x"}]}, response]):
            with self.assertRaisesRegex(ValueError, "invalid structured worker proposal"):
                provider.run(self.request())


if __name__ == "__main__":
    unittest.main()
