import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

from tools.context.project_context import checkpoint, snapshot
from tools.harness.ollama_worker import loopback_base, run_ollama


ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = ROOT / "tests/frozen_scenarios/cora_context_equivalence_v1.json"

IMPLEMENTED_SCENARIOS = {
    "context-dedup-exact-hash",
    "stale-document-rejects-checkpoint",
    "stale-head-rejects-checkpoint",
    "source-path-escape-rejected",
    "duplicate-checkpoint-rejected",
    "concurrent-writer-rejected",
    "non-loopback-ollama-rejected",
    "missing-model-refuses-chat-post",
    "recovery-is-not-second-product-truth",
    "matrixloop-stops-without-useful-delta",
    "external-reviewer-remains-hypothesis",
}


class FrozenCoraContextEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.run(
            ["git", "-C", str(self.repo), "init"],
            check=True,
            capture_output=True,
        )
        (self.repo / "docs").mkdir()
        (self.repo / "docs/state.md").write_text(
            "# State\n\n## Latest\nKnown baseline.\n", encoding="utf-8"
        )
        (self.repo / "docs/rules.md").write_text(
            "# Rules\nNo protected action without consumer authority.\n",
            encoding="utf-8",
        )
        manifest = {
            "schema": "loop42.context-manifest.v1",
            "roles": {
                "project_state": "docs/state.md",
                "decisions": "docs/state.md",
                "architecture": "docs/rules.md",
            },
            "external_sources": [],
        }
        (self.repo / "loop42-context.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "-c",
                "user.name=Loop42 Frozen",
                "-c",
                "user.email=frozen@example.invalid",
                "commit",
                "-m",
                "fixture",
            ],
            check=True,
            capture_output=True,
        )

    def tearDown(self):
        self.temp.cleanup()

    def result_file(self, current, checkpoint_id="equivalence-checkpoint"):
        payload = {
            "id": checkpoint_id,
            "basis": current["fingerprint"],
            "known": "Frozen context read.",
            "proven": "Fixture behavior observed.",
            "open": "Consumer-specific evidence remains external.",
            "discarded": "Parallel product truth.",
            "next": "Continue only with useful verified delta.",
            "evidence": "frozen equivalence fixture",
        }
        path = self.repo / "result.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_frozen_suite_identity_and_coverage(self):
        self.assertEqual(self.suite["schema"], "loop42.frozen-scenarios.v1")
        self.assertEqual(self.suite["suite"], "cora-context-equivalence-v1")
        self.assertEqual(self.suite["source_repository"], "DeepWolf42/C.O.R.A.")
        self.assertEqual(
            self.suite["source_revision"],
            "665bdd49724f27258ca4633b0dc5fa8fbb9ae602",
        )
        self.assertEqual(set(self.suite["scenarios"]), IMPLEMENTED_SCENARIOS)

    def test_context_dedup_exact_hash(self):
        current = snapshot(self.repo)
        self.assertEqual(len(current["documents"]), 2)
        self.assertEqual(current["remote_freshness"], "UNKNOWN")
        self.assertEqual(current["roles"]["decisions"], "docs/state.md")

    def test_stale_document_rejects_checkpoint(self):
        current = snapshot(self.repo)
        result = self.result_file(current)
        (self.repo / "docs/rules.md").write_text("Changed rule.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale basis"):
            checkpoint(self.repo, result)

    def test_stale_head_rejects_checkpoint(self):
        current = snapshot(self.repo)
        result = self.result_file(current)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "-c",
                "user.name=Loop42 Frozen",
                "-c",
                "user.email=frozen@example.invalid",
                "commit",
                "--allow-empty",
                "-m",
                "moved head",
            ],
            check=True,
            capture_output=True,
        )
        with self.assertRaisesRegex(ValueError, "stale basis"):
            checkpoint(self.repo, result)

    def test_source_path_escape_rejected(self):
        manifest_path = self.repo / "loop42-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["roles"]["architecture"] = "../outside.md"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside the checkout"):
            snapshot(self.repo)

    def test_duplicate_checkpoint_rejected(self):
        first = self.result_file(snapshot(self.repo))
        checkpoint(self.repo, first)
        second = self.result_file(snapshot(self.repo))
        with self.assertRaisesRegex(ValueError, "duplicate checkpoint"):
            checkpoint(self.repo, second)

    def test_concurrent_writer_rejected(self):
        current = snapshot(self.repo)
        result = self.result_file(current)
        lock = self.repo / ".git/loop42-project-context.lock"
        lock.write_text("other writer", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            checkpoint(self.repo, result)

    def test_non_loopback_ollama_rejected(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            loopback_base("http://example.com:11434")

    def test_missing_model_refuses_chat_post(self):
        class Handler(BaseHTTPRequestHandler):
            post_count = 0

            def log_message(self, format, *args):
                pass

            def do_GET(self):
                assert self.path == "/api/tags"
                body = json.dumps(
                    {"models": [{"name": "other:latest", "model": "other:latest"}]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                type(self).post_count += 1
                self.send_response(500)
                self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            current = {"fingerprint": "a" * 64, "head": "abc123"}
            with self.assertRaisesRegex(ValueError, "not installed locally"):
                run_ollama(
                    current,
                    "local-test",
                    "What is open?",
                    f"http://127.0.0.1:{server.server_port}",
                    5,
                )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
        self.assertEqual(Handler.post_count, 0)

    def test_recovery_is_not_second_product_truth(self):
        text = (ROOT / "docs/RECOVERY_AND_TRUTH.md").read_text(encoding="utf-8")
        self.assertIn("must not become a second product-state store", text)

    def test_matrixloop_stops_without_useful_delta(self):
        text = (ROOT / "docs/MATRIXLOOP.md").read_text(encoding="utf-8")
        self.assertIn(
            "Do not manufacture additional work merely to keep the loop active.",
            text,
        )

    def test_external_reviewer_remains_hypothesis(self):
        text = (ROOT / "docs/MATRIXLOOP.md").read_text(encoding="utf-8")
        self.assertIn("their findings are hypotheses until reproduced", text)


if __name__ == "__main__":
    unittest.main()
