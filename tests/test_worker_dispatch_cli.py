import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.harness.worker_dispatch_cli import SCHEMA, _load_json, run_request


ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-09-30T18:30:00+00:00"
REV = "a" * 40
CTX = "b" * 64
RECEIPT = "c" * 64


def task():
    return {
        "task_id": "cora-review",
        "attempt_id": "a1",
        "source_revision": REV,
        "context_fingerprint": CTX,
        "acceptance_criteria": ["return a bounded review"],
    }


def request(operation, **extra):
    value = {
        "schema": SCHEMA,
        "operation": operation,
        "now": NOW,
        "observation": None,
        "artifacts": [],
    }
    value.update(extra)
    return value


class WorkerDispatchCliTests(unittest.TestCase):
    def test_reconcile_missing_host_remains_unknown(self):
        result = run_request(request("reconcile", expected=task()))
        state = result["state"]
        self.assertEqual(state["host"], "unknown")
        self.assertEqual(state["worker"], "unknown")
        self.assertEqual(state["lifecycle"], "unknown")
        self.assertEqual(state["freshness"], "unknown")
        self.assertFalse(state["can_dispatch"])
        self.assertIn("host_observation_missing", state["reasons"])

    def test_reconcile_accepts_only_matching_terminal_identity(self):
        artifact = {
            "kind": "result",
            "task_id": "cora-review",
            "attempt_id": "a1",
            "source_revision": REV,
            "context_fingerprint": CTX,
            "observed_at": NOW,
            "success": True,
            "receipt_fingerprint": RECEIPT,
        }
        result = run_request(
            request("reconcile", expected=task(), artifacts=[artifact])
        )
        self.assertEqual(result["state"]["lifecycle"], "succeeded")
        self.assertEqual(result["state"]["result_receipt"], RECEIPT)

        stale = dict(artifact)
        stale["source_revision"] = "d" * 40
        conflict = run_request(
            request("reconcile", expected=task(), artifacts=[stale])
        )
        self.assertEqual(conflict["state"]["lifecycle"], "conflict")
        self.assertIn("attempt_identity_mismatch", conflict["state"]["reasons"])

    def test_permit_roundtrip_requires_same_fresh_basis(self):
        observation = {
            "observed_at": NOW,
            "session_id": "host-1",
            "reachable": True,
            "worker_sessions": [],
            "safety_stop": False,
        }
        issued = run_request(
            request(
                "issue-permit",
                task=task(),
                observation=observation,
            )
        )
        self.assertIsNotNone(issued["permit"])

        validated = run_request(
            request(
                "validate-permit",
                task=task(),
                permit=issued["permit"],
                observation=observation,
            )
        )
        self.assertTrue(validated["valid"])

        changed = dict(observation)
        changed["safety_stop"] = True
        rejected = run_request(
            request(
                "validate-permit",
                task=task(),
                permit=issued["permit"],
                observation=changed,
            )
        )
        self.assertFalse(rejected["valid"])

    def test_unknown_fields_and_duplicate_json_keys_fail_closed(self):
        value = request("reconcile", expected=task())
        value["surprise"] = True
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            run_request(value)

        raw = b'{"schema":"a","schema":"b"}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            _load_json(raw)

    def test_module_cli_reads_stdin_and_emits_json(self):
        payload = json.dumps(request("reconcile", expected=task()))
        completed = subprocess.run(
            [sys.executable, "-m", "tools.harness.worker_dispatch_cli"],
            cwd=ROOT,
            input=payload,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertEqual(value["schema"], SCHEMA)
        self.assertEqual(value["state"]["lifecycle"], "unknown")


if __name__ == "__main__":
    unittest.main()
