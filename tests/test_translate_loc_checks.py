from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKS_SCRIPT = REPO_ROOT / ".codex" / "skills" / "translate-loc" / "scripts" / "checks.py"


class TranslateLocChecksTests(unittest.TestCase):
    def test_checks_allows_extra_keys_in_translated_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "source.ini"
            translated = temp_root / "translated.ini"

            source.write_text("key_a=Hello %s\nkey_b=World\n", encoding="utf-8")
            translated.write_text(
                "key_a=Hola %s\nkey_b=Mundo\nlegacy_key=Valor antiguo\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(CHECKS_SCRIPT), str(source), str(translated)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("Warnings: 1", completed.stdout)
            self.assertIn("extra keys", completed.stdout)

    def test_checks_fails_when_source_keys_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "source.ini"
            translated = temp_root / "translated.ini"

            source.write_text("key_a=Hello\nkey_b=World\n", encoding="utf-8")
            translated.write_text("key_a=Hola\n", encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, str(CHECKS_SCRIPT), str(source), str(translated)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Missing required keys from source", completed.stdout)


if __name__ == "__main__":
    unittest.main()
