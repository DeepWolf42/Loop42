import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.context.repository_map import MAP_SCHEMA, repository_map


def run(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class RepositoryMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        run(self.repo, "init")
        run(self.repo, "config", "user.email", "loop42@example.invalid")
        run(self.repo, "config", "user.name", "Loop42 Test")

        (self.repo / "pkg").mkdir()
        (self.repo / "pkg/__init__.py").write_text("", encoding="utf-8")
        (self.repo / "pkg/core.py").write_text(
            "class Engine:\n"
            "    pass\n\n"
            "def calculate(value: int, scale: int = 1) -> int:\n"
            "    return value * scale\n",
            encoding="utf-8",
        )
        (self.repo / "app.py").write_text(
            "from pkg.core import Engine, calculate\n\n"
            "def main():\n"
            "    return calculate(Engine() is not None)\n",
            encoding="utf-8",
        )
        (self.repo / "worker.py").write_text(
            "import pkg.core\n\n"
            "def work():\n"
            "    return pkg.core.calculate(2)\n",
            encoding="utf-8",
        )
        (self.repo / "README.md").write_text(
            "# Demo\n\n## Architecture\nSmall fixture.\n",
            encoding="utf-8",
        )
        (self.repo / "config.json").write_text(
            json.dumps({"schema": "demo.v1", "enabled": True}),
            encoding="utf-8",
        )
        run(self.repo, "add", ".")
        run(self.repo, "commit", "-m", "fixture")

    def tearDown(self):
        self.temp.cleanup()

    def test_query_prioritizes_matching_symbol_and_dependency(self):
        result = repository_map(self.repo, query="Engine", budget_bytes=4096)
        self.assertEqual(result["schema"], MAP_SCHEMA)
        self.assertEqual(result["head"], run(self.repo, "rev-parse", "HEAD"))
        paths = [entry["path"] for entry in result["entries"]]
        self.assertEqual(paths[0], "pkg/core.py")
        core = result["entries"][0]
        self.assertEqual(core["inbound_references"], 2)
        names = [symbol["name"] for symbol in core["symbols"]]
        self.assertIn("Engine", names)
        self.assertIn("calculate", names)
        signature = next(
            symbol["signature"]
            for symbol in core["symbols"]
            if symbol["name"] == "calculate"
        )
        self.assertEqual(signature, "def calculate(value: int, scale: int=...) -> int")

    def test_explicit_target_is_included_and_untracked_files_are_not_candidates(self):
        (self.repo / "scratch.py").write_text("def hidden(): pass\n", encoding="utf-8")
        result = repository_map(
            self.repo,
            targets=("config.json",),
            budget_bytes=2048,
        )
        paths = [entry["path"] for entry in result["entries"]]
        self.assertIn("config.json", paths)
        self.assertNotIn("scratch.py", paths)
        self.assertEqual(result["candidate_count"], 5)
        config = next(entry for entry in result["entries"] if entry["path"] == "config.json")
        self.assertEqual(
            [symbol["name"] for symbol in config["symbols"]],
            ["schema", "enabled"],
        )

    def test_unknown_target_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "not a tracked file"):
            repository_map(
                self.repo,
                targets=("scratch.py",),
                budget_bytes=2048,
            )

    def test_working_tree_bytes_are_bound_even_when_head_is_unchanged(self):
        before = repository_map(
            self.repo,
            query="calculate",
            targets=("pkg/core.py",),
            budget_bytes=4096,
        )
        head = before["head"]
        (self.repo / "pkg/core.py").write_text(
            "class Engine:\n"
            "    pass\n\n"
            "def calculate(value: int, scale: int = 2) -> int:\n"
            "    return value * scale\n",
            encoding="utf-8",
        )
        after = repository_map(
            self.repo,
            query="calculate",
            targets=("pkg/core.py",),
            budget_bytes=4096,
        )
        self.assertEqual(after["head"], head)
        self.assertNotEqual(before["fingerprint"], after["fingerprint"])
        old_hash = next(
            entry["sha256"] for entry in before["entries"] if entry["path"] == "pkg/core.py"
        )
        new_hash = hashlib.sha256((self.repo / "pkg/core.py").read_bytes()).hexdigest()
        self.assertNotEqual(old_hash, new_hash)
        self.assertEqual(
            next(entry["sha256"] for entry in after["entries"] if entry["path"] == "pkg/core.py"),
            new_hash,
        )

    def test_budget_is_bounded_and_reports_truncation(self):
        result = repository_map(self.repo, budget_bytes=1400)
        encoded = json.dumps(
            result, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertLessEqual(len(encoded), 1400)
        self.assertTrue(result["truncated"])

    def test_invalid_python_is_visible_not_silently_treated_as_parsed(self):
        (self.repo / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        run(self.repo, "add", "broken.py")
        result = repository_map(
            self.repo,
            targets=("broken.py",),
            budget_bytes=2048,
        )
        broken = next(entry for entry in result["entries"] if entry["path"] == "broken.py")
        self.assertEqual(broken["status"], "parse_error")
        self.assertEqual(broken["symbols"], [])


if __name__ == "__main__":
    unittest.main()
