from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryPolicyTests(unittest.TestCase):
    def test_required_seed_files_exist(self):
        required = (
            "README.md",
            "THIRD_PARTY.md",
            "docs/MATRIXLOOP.md",
            "docs/HARNESS_CONTRACT.md",
            "docs/RECOVERY_AND_TRUTH.md",
            "docs/EVALUATION.md",
            "docs/LICENSE_POLICY.md",
            "docs/assets/loop42-mark.webp",
            "tools/harness/README.md",
            "tools/context/README.md",
            "tools/checks/README.md",
            "tests/frozen_scenarios/README.md",
            "adapters/examples/README.md",
        )
        missing = [path for path in required if not (ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_private_seed_has_no_root_project_license(self):
        forbidden = ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING")
        present = [name for name in forbidden if (ROOT / name).exists()]
        self.assertEqual(present, [])

    def test_naming_boundary_is_explicit(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Loop42", readme)
        self.assertIn("Matrixloop", readme)
        self.assertIn("project-agnostic", readme)
        self.assertIn("Consumer projects keep their own product state", readme)

    def test_recovery_contract_rejects_parallel_product_truth(self):
        recovery = (ROOT / "docs/RECOVERY_AND_TRUTH.md").read_text(encoding="utf-8")
        self.assertIn("must not become a second product-state store", recovery)
        self.assertIn("Recovery is not specification", recovery)

    def test_consumer_product_truth_files_do_not_live_here(self):
        forbidden = (
            ROOT / "docs/CURRENT_PROJECT_STATE.md",
            ROOT / "project-context.json",
            ROOT / "src/cora",
        )
        present = [str(path.relative_to(ROOT)) for path in forbidden if path.exists()]
        self.assertEqual(present, [])

    def test_no_legacy_github_owner_references(self):
        legacy_owner = "michaelwolf" + "2289-lang"
        text_suffixes = {".md", ".txt", ".py", ".json", ".toml", ".yml", ".yaml"}
        offenders = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in text_suffixes:
                continue
            if legacy_owner in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
