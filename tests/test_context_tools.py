import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.context.project_context import checkpoint, snapshot


class ContextToolTests(unittest.TestCase):
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
            "# Rules\nNo protected actions without consumer authority.\n",
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
                "user.name=Loop42 Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-m",
                "fixture",
            ],
            check=True,
            capture_output=True,
        )

    def tearDown(self):
        self.temp.cleanup()

    def result_file(self, current, checkpoint_id="test-checkpoint"):
        result = {
            "id": checkpoint_id,
            "basis": current["fingerprint"],
            "known": "Shared context read.",
            "proven": "Fixture verified.",
            "open": "Consumer-specific evidence remains external.",
            "discarded": "Duplicated product state.",
            "next": "Review the next useful change.",
            "evidence": "unittest fixture",
        }
        path = self.repo / "result.json"
        path.write_text(json.dumps(result), encoding="utf-8")
        return path

    def test_snapshot_deduplicates_and_hashes_exact_sources(self):
        first = snapshot(self.repo)
        second = snapshot(self.repo)
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "loop42.project-snapshot.v1")
        self.assertEqual(len(first["documents"]), 2)
        state = next(
            item for item in first["documents"] if item["path"] == "docs/state.md"
        )
        expected = hashlib.sha256((self.repo / "docs/state.md").read_bytes()).hexdigest()
        self.assertEqual(state["sha256"], expected)
        self.assertEqual(first["remote_freshness"], "UNKNOWN")
        self.assertEqual(first["roles"]["decisions"], "docs/state.md")

    def test_checkpoint_updates_existing_state_and_rejects_replay(self):
        current = snapshot(self.repo)
        result_path = self.result_file(current)
        output = checkpoint(self.repo, result_path)
        self.assertEqual(output["updated"], "docs/state.md")
        text = (self.repo / "docs/state.md").read_text(encoding="utf-8")
        self.assertIn("Shared context read.", text)
        self.assertIn("Known baseline.", text)
        self.assertLess(text.index("Shared context read."), text.index("Known baseline."))
        with self.assertRaisesRegex(ValueError, "stale basis|duplicate"):
            checkpoint(self.repo, result_path)

    def test_stale_result_cannot_overwrite_changed_source(self):
        current = snapshot(self.repo)
        result_path = self.result_file(current)
        before = (self.repo / "docs/state.md").read_bytes()
        (self.repo / "docs/rules.md").write_text(
            "Newer verified rule.", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "stale basis"):
            checkpoint(self.repo, result_path)
        self.assertEqual((self.repo / "docs/state.md").read_bytes(), before)

    def test_invalid_source_path_fails_closed(self):
        manifest_path = self.repo / "loop42-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["roles"]["architecture"] = "../outside.md"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside the checkout"):
            snapshot(self.repo)

    def test_oversized_source_is_not_silently_truncated(self):
        (self.repo / "docs/rules.md").write_text(
            "x" * (256 * 1024 + 1), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "oversized"):
            snapshot(self.repo)

    def test_concurrent_writer_lock_fails_without_mutation(self):
        current = snapshot(self.repo)
        result_path = self.result_file(current)
        lock = self.repo / ".git/loop42-project-context.lock"
        lock.write_text("other writer", encoding="utf-8")
        before = (self.repo / "docs/state.md").read_bytes()
        with self.assertRaises(FileExistsError):
            checkpoint(self.repo, result_path)
        self.assertEqual((self.repo / "docs/state.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
