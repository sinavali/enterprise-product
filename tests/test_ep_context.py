#!/usr/bin/env python3
"""
test_ep_context.py — Tests for EP-OS Context Ingestion & Single-Turn Pack Engine
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ep_context import (
    collect_files_from_scope,
    collect_files_from_surface,
    pack_files,
    is_binary_file,
)


class TestEpContext(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pack_files_structure(self):
        file1 = os.path.join(self.temp_dir, "file1.ts")
        with open(file1, "w", encoding="utf-8") as f:
            f.write("console.log('hello world');\nexport const x = 42;\n")

        bundle, count, lines, bytes_count = pack_files(["file1.ts"], root_dir=self.temp_dir)
        self.assertEqual(count, 1)
        self.assertEqual(lines, 2)
        self.assertIn("=== [EP-OS CONTEXT BUNDLE: file1.ts] ===", bundle)
        self.assertIn("=== [END: file1.ts] ===", bundle)
        self.assertIn("export const x = 42;", bundle)

    def test_pack_files_truncation(self):
        file1 = os.path.join(self.temp_dir, "long.txt")
        with open(file1, "w", encoding="utf-8") as f:
            for i in range(50):
                f.write(f"line {i}\n")

        bundle, count, lines, bytes_count = pack_files(["long.txt"], max_lines=10, root_dir=self.temp_dir)
        self.assertEqual(count, 1)
        self.assertEqual(lines, 50)
        self.assertIn("line 9", bundle)
        self.assertIn("TRUNCATED", bundle)

    def test_collect_files_from_scope(self):
        sub_dir = os.path.join(self.temp_dir, "services", "auth")
        os.makedirs(sub_dir)
        with open(os.path.join(sub_dir, "index.ts"), "w") as f:
            f.write("export * from './auth';")
        with open(os.path.join(sub_dir, "logo.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00")

        files = collect_files_from_scope("services/auth", root_dir=self.temp_dir)
        self.assertEqual(files, ["services/auth/index.ts"])

    def test_collect_files_from_surface(self):
        changes_dir = os.path.join(self.temp_dir, "docs", "changes")
        os.makedirs(changes_dir)
        cs_file = os.path.join(changes_dir, "2026-10-19-test-change.md")
        src_file = os.path.join(self.temp_dir, "src", "service.ts")
        os.makedirs(os.path.dirname(src_file))
        with open(src_file, "w") as f:
            f.write("export class Service {}")

        with open(cs_file, "w") as f:
            f.write("""# Change Surface
## 3. Code Surface
- `src/service.ts`: Core service logic.
## 4. Test Surface
""")

        files = collect_files_from_surface(root_dir=self.temp_dir)
        self.assertEqual(files, ["src/service.ts"])

    def test_ep_cli_pack_command(self):
        ep_script = SCRIPTS_DIR / "ep.py"
        target_file = os.path.join(self.temp_dir, "sample.py")
        with open(target_file, "w") as f:
            f.write("print('fast context')\n")

        proc = subprocess.run(
            [sys.executable, str(ep_script), "pack", "--files", "sample.py", "--root", self.temp_dir],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("=== [EP-OS CONTEXT BUNDLE: sample.py] ===", proc.stdout)
        self.assertIn("[EP-OS PACK] Successfully bundled 1 file(s)", proc.stderr)


if __name__ == "__main__":
    unittest.main()
