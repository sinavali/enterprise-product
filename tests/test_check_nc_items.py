#!/usr/bin/env python3
"""
Unit and integration tests for check-nc-items CLI tool and 14-day escalation gate.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "scripts" / "bin"


class TestCheckNcItems(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_open_item_under_14_days_passes(self):
        nc_file = os.path.join(self.temp_dir, "NC-001.md")
        content = """---
id: "NC-20261010-001"
status: "OPEN"
created_date: "2026-10-10"
discovered_by: "agent"
affected_projects:
  - "services/order"
---
# NC Item 1
"""
        with open(nc_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
                "--as-of-date",
                "2026-10-12",
                "--max-age",
                "14",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[OK]", proc.stdout)

    def test_case_insensitive_nc_id_passes(self):
        nc_file = os.path.join(self.temp_dir, "NC-LOWER.md")
        content = """---
id: "nc-20261010-009"
status: "OPEN"
created_date: "2026-10-10"
discovered_by: "agent"
affected_projects:
  - "services/order"
---
# Lowercase NC Item
"""
        with open(nc_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
                "--as-of-date",
                "2026-10-12",
                "--max-age",
                "14",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[OK]", proc.stdout)

    def test_open_item_over_14_days_blocks(self):
        nc_file = os.path.join(self.temp_dir, "NC-OLD.md")
        content = """---
id: "NC-20260901-001"
status: "OPEN"
created_date: "2026-09-01"
discovered_by: "agent"
affected_projects:
  - "services/order"
---
# Old NC Item
"""
        with open(nc_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
                "--as-of-date",
                "2026-10-12",
                "--max-age",
                "14",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("[MERGE BLOCK DETECTED]", proc.stdout)

    def test_iso_timestamp_and_slash_date_formats(self):
        nc_file = os.path.join(self.temp_dir, "NC-ISO.md")
        content = """---
id: "NC-20261010-002"
status: "OPEN"
created_date: "2026-10-10T14:30:00Z"
discovered_by: "agent"
affected_projects:
- "services/order"
---
# ISO Date Item
"""
        with open(nc_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
                "--as-of-date",
                "2026-10-12",
                "--max-age",
                "14",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[OK]", proc.stdout)

    def test_resolved_item_over_14_days_passes(self):
        nc_file = os.path.join(self.temp_dir, "NC-RESOLVED.md")
        content = """---
id: "NC-20260901-002"
status: "RESOLVED"
created_date: "2026-09-01"
resolved_date: "2026-09-05"
discovered_by: "agent"
---
# Resolved NC Item
"""
        with open(nc_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
                "--as-of-date",
                "2026-10-12",
                "--max-age",
                "14",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("[OK]", proc.stdout)

    def test_templates_and_placeholders_ignored(self):
        tmpl_file = os.path.join(self.temp_dir, "NEED_CLARIFICATION.template.md")
        content = """---
id: "NC-YYYYMMDD-001"
status: "OPEN"
created_date: "YYYY-MM-DD"
---
# Template
"""
        with open(tmpl_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
                "--as-of-date",
                "2026-10-12",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Found 0 NC items", proc.stdout)

    def test_malformed_nc_file_triggers_parse_error_and_block(self):
        nc_dir = os.path.join(self.temp_dir, "docs", "nc")
        os.makedirs(nc_dir, exist_ok=True)
        bad_file = os.path.join(nc_dir, "NC-INVALID.md")
        content = """# Malformed NC Item without frontmatter
Missing frontmatter block completely.
"""
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                nc_dir,
                "--as-of-date",
                "2026-10-12",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("[PARSE ERRORS]", proc.stdout)


    def test_as_of_date_with_slash_format(self):
        nc_file = os.path.join(self.temp_dir, "NC-SLASH.md")
        content = """---
id: "NC-20261010-008"
status: "OPEN"
created_date: "2026-10-10"
discovered_by: "agent"
---
# Slash Date Test
"""
        with open(nc_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
                "--as-of-date",
                "2026/10/12",
                "--max-age",
                "14",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[OK]", proc.stdout)

    def test_explicit_nonexistent_dir_fails(self):
        nonexistent = os.path.join(self.temp_dir, "does_not_exist")
        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                nonexistent,
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("does not exist", proc.stderr)

    def test_resolved_item_missing_resolved_date_fails(self):
        nc_file = os.path.join(self.temp_dir, "NC-RESOLVED-NO-DATE.md")
        content = """---
id: "NC-20260901-003"
status: "RESOLVED"
created_date: "2026-09-01"
discovered_by: "agent"
---
# Incomplete Resolved Item
"""
        with open(nc_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("missing required 'resolved_date'", proc.stdout)


    def test_inline_bracket_list_affected_projects(self):
        nc_file = os.path.join(self.temp_dir, "NC-BRACKET.md")
        content = """---
id: "NC-20261010-011"
status: "OPEN"
created_date: "2026-10-10"
discovered_by: "agent"
affected_projects: ["services/order", "services/billing"]
---
# Bracket List Item
"""
        with open(nc_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [
                str(BIN_DIR / "check-nc-items"),
                "--dir",
                self.temp_dir,
                "--as-of-date",
                "2026-10-12",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        import json
        res = json.loads(proc.stdout)
        self.assertEqual(len(res["open_items"]), 1)
        self.assertEqual(res["open_items"][0]["affected_projects"], ["services/order", "services/billing"])


if __name__ == "__main__":
    unittest.main()
