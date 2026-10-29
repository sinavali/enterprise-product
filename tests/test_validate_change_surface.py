#!/usr/bin/env python3
"""
Unit and integration tests for validate-change-surface CLI tool.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "scripts" / "bin"


class TestValidateChangeSurface(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_change_surface(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        content = """---
title: "Feature Test"
author: "Engineer 1"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "services/billing"
---

# Change Surface: Feature Test

## 1. Intent & Business Rationale
Implement billing discount recalculation.

## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/billing | Profile A | Recalculate invoice |

## 3. Code Surface
- `services/billing/src/domain/discount.ts`: Add discount logic
### Added Files
- `services/billing/src/domain/discount.ts`

## 4. Test Surface
- `services/billing/tests/unit/discount.spec.ts`

## 5. Invariants Preserved
- Pure domain isolation preserved.

## 6. Risk Matrix & Rollback Strategy
- Risk: Low.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0, got {proc.returncode}: {proc.stdout} {proc.stderr}")
        self.assertIn("[SUCCESS]", proc.stdout)

    def test_asterisk_bullet_list_passes(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE_ASTERISK.md")
        content = """---
title: "Feature Asterisk"
author: "Engineer 2"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "MEDIUM"
affected_projects:
- "services/orders"
---

# Change Surface: Feature Asterisk

## 1. Intent & Business Rationale
Rationale.

## 2. Affected Monorepo Projects & Profiles
Projects.

## 3. Code Surface
* `services/orders/src/domain/order.ts`: Add cancel logic
* `services/orders/src/domain/events.ts`: Add cancelled event

## 4. Test Surface
- `services/orders/tests/unit/order.spec.ts`

## 5. Invariants
Invariants.

## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[SUCCESS]", proc.stdout)

    def test_missing_section_fails(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE_BAD.md")
        content = """---
title: "Incomplete"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "services/billing"
---

# Incomplete
## 1. Intent & Business Rationale
Rationale.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("[ERROR]", proc.stdout)

    def test_bare_wildcard_in_code_surface_fails(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE_WILDCARD.md")
        content = """---
title: "Wildcard Test"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "services/billing"
---

# Test
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects
Projects.
## 3. Code Surface
- `services/billing/*`
*
## 4. Test Surface
Tests.
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("bare wildcard", proc.stdout)

    def test_invalid_risk_level_fails(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE_RISK.md")
        content = """---
title: "Invalid Risk"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "UNKNOWN_RISK"
affected_projects:
  - "services/billing"
---
# Invalid Risk
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects
Projects.
## 3. Code Surface
- `services/billing/test.ts`
## 4. Test Surface
Tests.
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Invalid risk_level", proc.stdout)

    def test_docs_changes_fallback_resolution(self):
        docs_changes = os.path.join(self.temp_dir, "docs", "changes")
        os.makedirs(docs_changes, exist_ok=True)
        versioned_file = os.path.join(docs_changes, "20261012-feature.md")
        content = """---
title: "Versioned Change Surface"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "services/billing"
---
# Versioned Change Surface
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/billing | Profile A | Logic |
## 3. Code Surface
- `services/billing/index.ts`
## 4. Test Surface
- `services/billing/index.spec.ts`
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(versioned_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface")],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[SUCCESS]", proc.stdout)
        # Verify the actual resolved target_file is reported, not hardcoded args.file
        self.assertIn("20261012-feature.md", proc.stdout)


    def test_numbered_list_in_code_surface(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        content = """---
title: "Numbered Code Surface"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "services/billing"
---
# Numbered Code Surface
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/billing | Profile A | Logic |
## 3. Code Surface
1. `services/billing/index.ts`
2. `services/billing/model.ts`
## 4. Test Surface
- `services/billing/index.spec.ts`
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[SUCCESS]", proc.stdout)

    def test_inline_bracket_list_in_affected_projects(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        content = """---
title: "Inline List Surface"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects: ["services/order", "services/user"]
---
# Inline List Surface
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/order | Profile A | Logic |
## 3. Code Surface
- `services/order/index.ts`
## 4. Test Surface
- `services/order/index.spec.ts`
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[SUCCESS]", proc.stdout)

    def test_empty_affected_projects_fails(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        content = """---
title: "Empty Projects Surface"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects: []
---
# Empty Projects Surface
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/order | Profile A | Logic |
## 3. Code Surface
- `services/order/index.ts`
## 4. Test Surface
- `services/order/index.spec.ts`
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("must contain at least one project", proc.stdout)


    def test_invalid_created_date_fails(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        content = """---
title: "Invalid Date Surface"
author: "Engineer"
created_date: "2026-99-99"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "services/order"
---
# Invalid Date Surface
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/order | Profile A | Logic |
## 3. Code Surface
- `services/order/index.ts`
## 4. Test Surface
- `services/order/index.spec.ts`
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Invalid created_date", proc.stdout)

    def test_empty_test_surface_targets_fails(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        content = """---
title: "No Tests Surface"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "services/order"
---
# No Tests Surface
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/order | Profile A | Logic |
## 3. Code Surface
- `services/order/index.ts`
## 4. Test Surface
Pending tests or no test suites declared here.
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Test Surface does not list explicit test files", proc.stdout)

    def test_na_in_test_surface_passes(self):
        file_path = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        content = """---
title: "NA Tests Surface"
author: "Engineer"
created_date: "2026-10-12"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "services/order"
---
# NA Tests Surface
## 1. Intent & Business Rationale
Rationale.
## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/order | Profile A | Logic |
## 3. Code Surface
- `services/order/index.ts`
## 4. Test Surface
N/A for configuration changes.
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "validate-change-surface"), file_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("[SUCCESS]", proc.stdout)

    def test_ep_surface_init_scaffolds_valid_surface(self):
        ep_script = REPO_ROOT / "scripts" / "ep.py"
        target_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        proc = subprocess.run(
            [sys.executable, str(ep_script), "surface", "init", "--surface-file", target_file, "--scope", "services/order"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Error: {proc.stderr}")
        self.assertTrue(os.path.isfile(target_file))
        self.assertIn("[OK] Initialized Change Surface", proc.stdout)

    def test_archive_change_surface_success_and_reset(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from ep_scaffold import archive_change_surface

        target_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        changes_dir = os.path.join(self.temp_dir, "docs", "changes")
        content = """---
title: "Change Surface: Automated Billing Engine"
author: "Lead Architect"
created_date: "2026-10-27"
target_branch: "feat/billing"
risk_level: "LOW"
affected_projects:
  - "services/billing"
---

# Change Surface: Automated Billing Engine

## 1. Intent & Business Rationale
Implement automated billing recalculation.

## 2. Affected Monorepo Projects & Profiles
| Project | Profile | Responsibility |
|---|---|---|
| services/billing | Profile A | Recalculate invoice |

## 3. Code Surface
- `services/billing/src/domain/billing.ts`

## 4. Test Surface
- `services/billing/tests/unit/billing.spec.ts`

## 5. Invariants
- UTC timestamps preserved.

## 6. Risk Matrix
- Rollback: Revert commits.
"""
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        ok, archived_path = archive_change_surface(target_file, changes_dir=changes_dir, reset_root=True)
        self.assertTrue(ok)
        self.assertTrue(os.path.isfile(archived_path))
        self.assertEqual(os.path.basename(archived_path), "2026-10-27-automated-billing-engine.md")

        with open(archived_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

        # Root file should be reset to clean baseline template
        with open(target_file, "r", encoding="utf-8") as f:
            reset_content = f.read()
        self.assertIn("[Short Descriptive Title]", reset_content)
        self.assertIn("[Feature or Task Title]", reset_content)

    def test_archive_change_surface_no_reset(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from ep_scaffold import archive_change_surface

        target_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        changes_dir = os.path.join(self.temp_dir, "docs", "changes")
        content = """---
title: "Change Surface: Cache Layer"
author: "Engineer"
created_date: "2026-10-27"
target_branch: "feat/cache"
risk_level: "LOW"
affected_projects:
  - "services/cache"
---

# Change Surface: Cache Layer

## 1. Intent & Business Rationale
Add caching.

## 2. Affected Monorepo Projects
- `services/cache`

## 3. Code Surface
- `services/cache/cache.ts`

## 4. Test Surface
- `services/cache/cache.spec.ts`

## 5. Invariants
Invariants preserved.

## 6. Risk Matrix
Low.
"""
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        ok, archived_path = archive_change_surface(target_file, changes_dir=changes_dir, reset_root=False)
        self.assertTrue(ok)
        self.assertTrue(os.path.isfile(archived_path))

        # Root file remains unreset
        with open(target_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_archive_unpopulated_template_skips(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from ep_scaffold import archive_change_surface, get_clean_surface_template

        target_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        changes_dir = os.path.join(self.temp_dir, "docs", "changes")
        template = get_clean_surface_template()
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(template)

        ok, msg = archive_change_surface(target_file, changes_dir=changes_dir)
        self.assertFalse(ok)
        self.assertIn("unpopulated baseline template", msg)
        self.assertFalse(os.path.exists(changes_dir))

    def test_archive_collision_handling(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from ep_scaffold import archive_change_surface

        target_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        changes_dir = os.path.join(self.temp_dir, "docs", "changes")
        os.makedirs(changes_dir, exist_ok=True)

        existing_path = os.path.join(changes_dir, "2026-10-27-payment-gateway.md")
        with open(existing_path, "w", encoding="utf-8") as f:
            f.write("Existing different content")

        new_content = """---
title: "Payment Gateway"
author: "Engineer"
created_date: "2026-10-27"
target_branch: "feat/payment"
risk_level: "LOW"
affected_projects:
  - "services/payment"
---
# Payment Gateway
## 1. Intent & Business Rationale
Intent
## 2. Affected Monorepo Projects
- services/payment
## 3. Code Surface
- `services/payment/index.ts`
## 4. Test Surface
- `services/payment/index.spec.ts`
## 5. Invariants
Invariants
## 6. Risk Matrix
Risk
"""
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        ok, archived_path = archive_change_surface(target_file, changes_dir=changes_dir, reset_root=False)
        self.assertTrue(ok)
        self.assertEqual(os.path.basename(archived_path), "2026-10-27-payment-gateway-1.md")
        self.assertTrue(os.path.exists(existing_path))

    def test_ep_surface_archive_cli(self):
        ep_script = REPO_ROOT / "scripts" / "ep.py"
        target_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        changes_dir = os.path.join(self.temp_dir, "docs", "changes")

        content = """---
title: "Change Surface: CLI Archive Verification"
author: "CLI Tester"
created_date: "2026-10-27"
target_branch: "feat/cli-archive"
risk_level: "LOW"
affected_projects:
  - "services/cli"
---
# Change Surface: CLI Archive Verification
## 1. Intent & Business Rationale
Verify CLI surface archive.
## 2. Affected Monorepo Projects
- services/cli
## 3. Code Surface
- `services/cli/main.ts`
## 4. Test Surface
- `services/cli/main.spec.ts`
## 5. Invariants
Invariants.
## 6. Risk Matrix
Risk.
"""
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [sys.executable, str(ep_script), "surface", "archive", target_file, "--changes-dir", changes_dir],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"CLI error: {proc.stderr}")
        self.assertIn("[OK] Change Surface archived to", proc.stdout)

        archived_files = os.listdir(changes_dir)
        self.assertEqual(len(archived_files), 1)
        self.assertTrue(archived_files[0].endswith("cli-archive-verification.md"))

    def test_ep_surface_init_auto_archives_existing_surface(self):
        ep_script = REPO_ROOT / "scripts" / "ep.py"
        target_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        docs_changes = os.path.join(self.temp_dir, "docs", "changes")

        old_content = """---
title: "Change Surface: Old Feature Prior To Init"
author: "Prior Engineer"
created_date: "2026-10-26"
target_branch: "feat/old"
risk_level: "LOW"
affected_projects:
  - "services/old"
---
# Change Surface: Old Feature Prior To Init
## 1. Intent & Business Rationale
Old rationale.
## 2. Affected Monorepo Projects
- services/old
## 3. Code Surface
- `services/old/old.ts`
## 4. Test Surface
- `services/old/old.spec.ts`
## 5. Invariants
Old invariants.
## 6. Risk Matrix
Old risk.
"""
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(old_content)

        proc = subprocess.run(
            [sys.executable, str(ep_script), "surface", "init", "--surface-file", target_file, "--scope", "services/new"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Error: {proc.stderr}")
        self.assertIn("Auto-archived previous populated surface", proc.stdout)
        self.assertIn("[OK] Initialized Change Surface", proc.stdout)

        archived_files = os.listdir(docs_changes)
        self.assertEqual(len(archived_files), 1)
        self.assertIn("old-feature-prior-to-init", archived_files[0])



if __name__ == "__main__":
    unittest.main()
