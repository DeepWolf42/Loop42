import unittest

from tools.harness.change_set import (
    ChangeOperation,
    ChangeSet,
    CreateChange,
    DeleteChange,
    ModifyChange,
    changeset_schema_fingerprint,
    normalize_changeset,
    parse_changeset,
    sha256_text,
)


class ChangeSetTests(unittest.TestCase):
    def test_modify_exact_match_normalizes_to_diff(self):
        before = "a = 1\nb = 2\n"
        proposal = ChangeSet(
            changes=(
                ModifyChange(
                    path="pkg/mod.py",
                    base_sha256=sha256_text(before),
                    search="b = 2",
                    replace="b = 3",
                ),
            ),
            requested_verification=("unit:pkg",),
        )
        result = normalize_changeset(proposal, {"pkg/mod.py": before})
        self.assertEqual(result.files[0].operation, ChangeOperation.MODIFY)
        self.assertEqual(result.files[0].after_text, "a = 1\nb = 3\n")
        self.assertIn("--- a/pkg/mod.py", result.unified_diff)
        self.assertIn("+++ b/pkg/mod.py", result.unified_diff)
        self.assertEqual(result.requested_verification, ("unit:pkg",))
        self.assertEqual(len(result.fingerprint), 64)

    def test_modify_rejects_missing_ambiguous_or_stale_basis(self):
        before = "x\nx\n"
        with self.assertRaisesRegex(ValueError, "exactly once"):
            normalize_changeset(
                ChangeSet((ModifyChange("a.txt", sha256_text(before), "x", "y"),)),
                {"a.txt": before},
            )
        with self.assertRaisesRegex(ValueError, "base hash mismatch"):
            normalize_changeset(
                ChangeSet((ModifyChange("a.txt", "0" * 64, "x", "y"),)),
                {"a.txt": "x\n"},
            )
        with self.assertRaisesRegex(ValueError, "does not exist"):
            normalize_changeset(
                ChangeSet((ModifyChange("a.txt", sha256_text("x"), "x", "y"),)),
                {},
            )

    def test_create_and_delete_are_explicit(self):
        old = "obsolete\n"
        proposal = ChangeSet(
            (
                CreateChange("new.txt", "hello\n"),
                DeleteChange("old.txt", sha256_text(old)),
            )
        )
        result = normalize_changeset(proposal, {"old.txt": old})
        self.assertEqual(
            [item.operation for item in result.files],
            [ChangeOperation.CREATE, ChangeOperation.DELETE],
        )
        self.assertIn("--- /dev/null", result.unified_diff)
        self.assertIn("+++ b/new.txt", result.unified_diff)
        self.assertIn("--- a/old.txt", result.unified_diff)
        self.assertIn("+++ /dev/null", result.unified_diff)

    def test_create_existing_and_delete_stale_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            normalize_changeset(ChangeSet((CreateChange("x.txt", "new"),)), {"x.txt": "old"})
        with self.assertRaisesRegex(ValueError, "base hash mismatch"):
            normalize_changeset(
                ChangeSet((DeleteChange("x.txt", "0" * 64),)),
                {"x.txt": "old"},
            )

    def test_duplicate_paths_and_shell_like_verification_are_rejected(self):
        base = sha256_text("x")
        with self.assertRaisesRegex(ValueError, "one operation per path"):
            ChangeSet((ModifyChange("x.txt", base, "x", "y"), DeleteChange("x.txt", base)))
        with self.assertRaisesRegex(ValueError, "identifiers, not commands"):
            ChangeSet((CreateChange("x.txt", "x"),), requested_verification=("pytest -q",))

    def test_path_escape_and_non_one_match_contract_are_rejected(self):
        with self.assertRaises(ValueError):
            CreateChange("../escape.txt", "x")
        with self.assertRaises(ValueError):
            CreateChange("a\\b.txt", "x")
        with self.assertRaisesRegex(ValueError, "expected_matches=1"):
            ModifyChange("a.txt", "0" * 64, "x", "y", expected_matches=2)

    def test_provider_json_contract_is_strict_and_schema_fingerprinted(self):
        before = "x = 1\n"
        value = {
            "schema": "loop42.changeset.v1",
            "changes": [
                {
                    "operation": "modify",
                    "path": "x.py",
                    "base_sha256": sha256_text(before),
                    "search": "x = 1",
                    "replace": "x = 2",
                    "expected_matches": 1,
                }
            ],
            "requested_verification": ["unit:x"],
        }
        parsed = parse_changeset(value)
        self.assertEqual(parsed.changes[0].path, "x.py")
        self.assertEqual(len(changeset_schema_fingerprint()), 64)
        bad = dict(value)
        bad["surprise"] = True
        with self.assertRaisesRegex(ValueError, "unexpected or missing fields"):
            parse_changeset(bad)
        bad_change = dict(value)
        bad_change["changes"] = [dict(value["changes"][0], shell="pytest -q")]
        with self.assertRaisesRegex(ValueError, "unexpected or missing fields"):
            parse_changeset(bad_change)


if __name__ == "__main__":
    unittest.main()
