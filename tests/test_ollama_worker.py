import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest

from tools.harness.ollama_worker import (
    PROPOSAL_SCHEMA,
    loopback_base,
    ollama_payload,
    prompt_contract_fingerprint,
    proposal_schema_fingerprint,
    run_ollama,
    strict_json,
    validate_structured_proposal,
)


def proposal():
    return {
        "summary": "Bounded local proposal",
        "known": ["Current state was supplied in the snapshot."],
        "proven": ["No external action is proven by model text."],
        "open": ["Physical evidence remains unavailable."],
        "discarded": [],
        "next": ["Inspect the next evidenced software delta."],
        "evidence_paths": ["docs/state.md"],
    }


class OllamaWorkerTests(unittest.TestCase):
    def test_non_loopback_endpoint_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            loopback_base("http://example.com:11434")

    def test_request_payload_keeps_snapshot_proposal_only_and_schema_bound(self):
        current = {
            "schema": "loop42.project-snapshot.v1",
            "head": "abc123",
            "fingerprint": "a" * 64,
            "documents": [],
        }
        payload = ollama_payload(current, "local-test", "What is open?")
        self.assertEqual(payload["model"], "local-test")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["format"], PROPOSAL_SCHEMA)
        self.assertEqual(payload["options"], {"temperature": 0})
        self.assertEqual(json.loads(payload["messages"][1]["content"]), current)
        self.assertTrue(payload["messages"][2]["content"].startswith("What is open?"))
        self.assertIn("Required proposal JSON schema", payload["messages"][2]["content"])
        self.assertIn("not execution authority", payload["messages"][0]["content"])
        self.assertIn("Return only JSON", payload["messages"][0]["content"])

    def test_prompt_contract_fingerprint_is_deterministic_and_prompt_bound(self):
        first = prompt_contract_fingerprint("What is open?")
        second = prompt_contract_fingerprint("What is open?")
        changed = prompt_contract_fingerprint("What changed?")
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(len(first), 64)

    def test_schema_fingerprint_is_deterministic(self):
        first = proposal_schema_fingerprint()
        second = proposal_schema_fingerprint()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_structured_proposal_validation_fails_closed(self):
        valid = proposal()
        self.assertEqual(validate_structured_proposal(valid), valid)

        extra = {**valid, "confidence": 0.99}
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            validate_structured_proposal(extra)

        duplicate = {**valid, "known": ["same", "same"]}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_structured_proposal(duplicate)

        no_next = {**valid, "next": []}
        with self.assertRaisesRegex(ValueError, "next"):
            validate_structured_proposal(no_next)

    def test_strict_json_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            strict_json(b'{"summary":"first","summary":"second"}')

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

    def test_exact_snapshot_is_sent_and_structured_proposal_is_bound_to_it(self):
        current = {
            "schema": "loop42.project-snapshot.v1",
            "head": "abc123",
            "fingerprint": "b" * 64,
            "documents": [{"path": "docs/state.md", "sha256": "c" * 64, "text": "# State"}],
        }

        class Handler(BaseHTTPRequestHandler):
            payload = None

            def log_message(self, format, *args):
                pass

            def do_GET(self):
                assert self.path == "/api/tags"
                body = json.dumps(
                    {
                        "models": [
                            {
                                "name": "local-test:latest",
                                "model": "local-test:latest",
                            }
                        ]
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                assert self.path == "/api/chat"
                size = int(self.headers["Content-Length"])
                type(self).payload = json.loads(self.rfile.read(size))
                body = json.dumps(
                    {
                        "model": "local-test:latest",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(proposal()),
                        },
                        "done": True,
                        "done_reason": "stop",
                        "prompt_eval_count": 123,
                        "eval_count": 17,
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            output = run_ollama(
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

        self.assertEqual(output["schema"], "loop42.ollama-worker-result.v2")
        self.assertEqual(output["basis"], current["fingerprint"])
        self.assertEqual(output["head"], current["head"])
        self.assertEqual(output["proposal"], proposal())
        self.assertEqual(
            output["proposal_schema_sha256"],
            proposal_schema_fingerprint(),
        )
        self.assertEqual(
            output["prompt_contract_sha256"],
            prompt_contract_fingerprint("What is open?"),
        )
        self.assertTrue(output["authority"].startswith("proposal-only"))
        self.assertEqual(output["metrics"]["prompt_eval_count"], 123)
        self.assertEqual(Handler.payload["model"], "local-test")
        self.assertFalse(Handler.payload["stream"])
        self.assertEqual(Handler.payload["format"], PROPOSAL_SCHEMA)
        self.assertEqual(Handler.payload["options"], {"temperature": 0})
        self.assertEqual(
            json.loads(Handler.payload["messages"][1]["content"]),
            current,
        )

    def test_invalid_structured_response_never_becomes_success(self):
        current = {"fingerprint": "d" * 64, "head": "abc123"}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                body = json.dumps(
                    {"models": [{"name": "local-test:latest"}]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                body = json.dumps(
                    {
                        "model": "local-test:latest",
                        "message": {"role": "assistant", "content": "not-json"},
                        "done": True,
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaisesRegex(ValueError, "invalid structured proposal"):
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


if __name__ == "__main__":
    unittest.main()
