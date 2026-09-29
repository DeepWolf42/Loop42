from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".toml", ".yml", ".yaml"}
EMAIL = re.compile(r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)
WINDOWS_ABSOLUTE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:\\\\(?:Users|Documents|Desktop|Downloads|OneDrive|Google Drive)\\\\", re.IGNORECASE)
SECRET_ASSIGNMENT = re.compile(
    r"\b(?:client[_-]?secret|access[_-]?token|refresh[_-]?token|api[_-]?key|password)\b"
    r"\s*[:=]\s*[\"']?[^\s\"',;]+",
    re.IGNORECASE,
)


class PublicHygieneTests(unittest.TestCase):
    def _text_files(self):
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if ".git" in path.parts:
                continue
            yield path

    def test_no_real_email_addresses_in_tracked_text(self):
        offenders = []
        allowed_domains = {"example.invalid", "example.com", "users.noreply.github.com"}
        for path in self._text_files():
            text = path.read_text(encoding="utf-8")
            for match in EMAIL.finditer(text):
                if match.group(1).lower() not in allowed_domains:
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(sorted(set(offenders)), [])

    def test_no_common_machine_local_user_paths(self):
        offenders = []
        for path in self._text_files():
            text = path.read_text(encoding="utf-8")
            if WINDOWS_ABSOLUTE.search(text):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_no_literal_secret_assignments(self):
        offenders = []
        for path in self._text_files():
            if path == Path(__file__):
                continue
            text = path.read_text(encoding="utf-8")
            if SECRET_ASSIGNMENT.search(text):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
