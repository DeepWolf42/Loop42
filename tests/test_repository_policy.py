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


if __name__ == "__main__":
    unittest.main()
