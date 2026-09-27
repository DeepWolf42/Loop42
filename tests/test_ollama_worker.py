import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest

from tools.harness.ollama_worker import (
    loopback_base,
    ollama_payload,
    run_ollama,
)


class OllamaWorkerTests(unittest.TestCase):
    def test_non_loopback_endpoint_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            loopback_base("http://example.com:11434")

    def test_request_payload_keeps_snapshot_proposal_only(self):
        current = {
            "schema": "loop42.project-snapshot.v1",
            "head": "abc123",
            "fingerprint": "a" * 64,
            "documents": [],
        }
        payload = ollama_payload(current, "local-test", "What is open?")
        self.assertEqual(payload["model"], "local-test")
        self.assertFalse(payload["stream"])
        self.assertEqual(json.loads(payload["messages"][1]["content"]), current)
        self.assertEqual(payload["messages"][2]["content"], "What is open?")
        self.assertIn("not execution authority", payload["messages"][0]["content"])

    def test_missing_model_refuses_chat_post(self):
        class Handler(BaseHTTPRequestHandler):
            post_count = 0

            def log_message(self, format, *args):
                pass

            def do_GET(self):
                self.assertEqual(self.path, "/api/tags")
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

    def test_exact_snapshot_is_sent_and_proposal_is_bound_to_it(self):
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
                self.assertEqual(self.path, "/api/tags")
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
                self.assertEqual(self.path, "/api/chat")
                size = int(self.headers["Content-Length"])
                type(self).payload = json.loads(self.rfile.read(size))
                body = json.dumps(
                    {
                        "model": "local-test:latest",
                        "message": {
                            "role": "assistant",
                            "content": "bounded local proposal",
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

        self.assertEqual(output["schema"], "loop42.ollama-worker-result.v1")
        self.assertEqual(output["basis"], current["fingerprint"])
        self.assertEqual(output["head"], current["head"])
        self.assertEqual(output["proposal"], "bounded local proposal")
        self.assertTrue(output["authority"].startswith("proposal-only"))
        self.assertEqual(output["metrics"]["prompt_eval_count"], 123)
        self.assertEqual(Handler.payload["model"], "local-test")
        self.assertFalse(Handler.payload["stream"])
        self.assertEqual(
            json.loads(Handler.payload["messages"][1]["content"]),
            current,
        )


if __name__ == "__main__":
    unittest.main()
