from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class SecurityBaselineTests(unittest.TestCase):
    def test_local_secret_patterns_are_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for required in (
            ".env",
            ".env.*",
            "*.pem",
            "*.key",
            "client_secret*.json",
            "credentials*.json",
            "token*.json",
        ):
            self.assertIn(required, ignore)

    def test_dependabot_groups_github_actions_updates(self):
        text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        self.assertIn('package-ecosystem: "github-actions"', text)
        self.assertIn('interval: "weekly"', text)
        self.assertIn("groups:", text)
        self.assertIn('          - "*"', text)

    def test_gitleaks_scans_full_history_read_only(self):
        text = (WORKFLOWS / "gitleaks.yml").read_text(encoding="utf-8")
        self.assertIn("fetch-depth: 0", text)
        self.assertIn("permissions:\n  contents: read\n  pull-requests: read", text)
        self.assertIn('GITLEAKS_ENABLE_COMMENTS: "false"', text)
        self.assertIn('GITLEAKS_ENABLE_UPLOAD_ARTIFACT: "false"', text)

    def test_all_workflow_actions_are_pinned_to_commit_sha(self):
        unpinned = []
        pattern = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
        sha40 = re.compile(r"^[0-9a-f]{40}$")
        for path in WORKFLOWS.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                uses = match.group(1)
                if uses.startswith("./"):
                    continue
                if "@" not in uses:
                    unpinned.append(f"{path.name}: {uses}")
                    continue
                ref = uses.rsplit("@", 1)[1]
                if not sha40.fullmatch(ref):
                    unpinned.append(f"{path.name}: {uses}")
        self.assertEqual(unpinned, [])


if __name__ == "__main__":
    unittest.main()
