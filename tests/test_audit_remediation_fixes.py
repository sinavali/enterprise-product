#!/usr/bin/env python3
"""
tests/test_audit_remediation_fixes.py
Comprehensive verification test suite asserting all 11 defect remediations
from DEEP_POLYGLOT_AUDIT_REPORT.md.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Import scripts with hyphens
spec_vcs = importlib.util.spec_from_file_location("validate_change_surface", str(SCRIPTS_DIR / "validate-change-surface.py"))
vcs_mod = importlib.util.module_from_spec(spec_vcs)  # type: ignore[arg-type]
spec_vcs.loader.exec_module(vcs_mod)  # type: ignore[union-attr]
is_surface_unpopulated_validator = vcs_mod.is_surface_unpopulated

spec_ar = importlib.util.spec_from_file_location("audit_runner", str(SCRIPTS_DIR / "audit-runner.py"))
ar_mod = importlib.util.module_from_spec(spec_ar)  # type: ignore[arg-type]
spec_ar.loader.exec_module(ar_mod)  # type: ignore[union-attr]
scan_file_for_violations = ar_mod.scan_file_for_violations
HEURISTIC_RULES = ar_mod.HEURISTIC_RULES

from ep import cmd_release
from ep_ast import STRUCTURAL_AST_RULES
from ep_context import collect_files_from_surface
from ep_doctor import check_vcs_branches
from ep_ops import cmd_finops, cmd_telemetry
from ep_runner import cmd_graph
from ep_scaffold import cmd_init, cmd_worktree, is_surface_unpopulated
from ep_security import cmd_policy
from ep_stack import detect_stack
from ep_sync import TRACKED_ROOT_FILES, TRACKED_SUBDIRS, get_tracked_manifest, sync_trees
from ep_vcs import get_git_provider


class TestAuditRemediationFixes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # FIX-01: Change Surface Fallback Cascade
    # --------------------------------------------------------------------------
    def test_fix_01_surface_fallback_when_unpopulated(self):
        # 1. Unpopulated detection helper
        template_text = "---\ntitle: \"[Feature or Task Title]\"\nauthor: \"[Author or Agent ID]\"\n---\n"
        self.assertTrue(is_surface_unpopulated(template_text))
        self.assertTrue(is_surface_unpopulated_validator(template_text))

        populated_text = "---\ntitle: \"Add Payment Gateway\"\nauthor: \"Alice\"\ncreated_date: \"2026-10-28\"\n---\n"
        self.assertFalse(is_surface_unpopulated(populated_text))
        self.assertFalse(is_surface_unpopulated_validator(populated_text))

        # 2. Context collection fallback
        surface_path = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        with open(surface_path, "w", encoding="utf-8") as f:
            f.write(template_text)

        changes_dir = os.path.join(self.temp_dir, "docs", "changes")
        os.makedirs(changes_dir, exist_ok=True)
        archived_file = os.path.join(changes_dir, "2026-10-27-feature.md")
        with open(archived_file, "w", encoding="utf-8") as f:
            f.write(
                "---\n"
                "title: \"Archived Feature\"\n"
                "author: \"Alice\"\n"
                "created_date: \"2026-10-27\"\n"
                "target_branch: \"main\"\n"
                "risk_level: \"LOW\"\n"
                "affected_projects:\n"
                "  - \"services/auth\"\n"
                "---\n\n"
                "## 1. Intent & Business Rationale\nArchived change rationale.\n\n"
                "## 2. Affected Monorepo Projects\n- services/auth\n\n"
                "## 3. Code Surface\n- `services/auth/src/login.ts`\n\n"
                "## 4. Test Surface\n- `services/auth/tests/login.test.ts`\n\n"
                "## 5. Invariants\n- No invariants broken.\n\n"
                "## 6. Risk Matrix\n- Low risk.\n"
            )

        auth_ts = os.path.join(self.temp_dir, "services", "auth", "src", "login.ts")
        os.makedirs(os.path.dirname(auth_ts), exist_ok=True)
        with open(auth_ts, "w", encoding="utf-8") as f:
            f.write("// login logic\n")

        files = collect_files_from_surface(root_dir=self.temp_dir)
        self.assertEqual(files, ["services/auth/src/login.ts"])

        # 3. CLI surface validate with ./CHANGE_SURFACE.md fallback
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            from ep import cmd_surface
            rc = cmd_surface(argparse.Namespace(action="validate", file="./CHANGE_SURFACE.md", strict=False, output=None, surface_file=None))
            self.assertEqual(rc, 0)
        finally:
            os.chdir(orig_cwd)

    # --------------------------------------------------------------------------
    # FIX-02: Canonical Skill Sync Engine & Orphan Pruning
    # --------------------------------------------------------------------------
    def test_fix_02_sync_engine_tracked_and_orphan_pruning(self):
        # Verify expanded tracked sets
        for expected in ["AGENT.md", "CLAUDE.md", ".cursorrules", ".windsurfrules", "CHANGE_SURFACE.md", "PRODUCT_SKILL.md", "project.json", "LICENSE", ".gitignore"]:
            self.assertIn(expected, TRACKED_ROOT_FILES)
        self.assertIn("docs", TRACKED_SUBDIRS)
        self.assertIn(".github", TRACKED_SUBDIRS)

        # Test orphan pruning in sync_trees
        src_dir = os.path.join(self.temp_dir, "src")
        dst_dir = os.path.join(self.temp_dir, "dst")
        os.makedirs(os.path.join(src_dir, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, "scripts"), exist_ok=True)

        with open(os.path.join(src_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("source\n")
        with open(os.path.join(dst_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("dest\n")
        with open(os.path.join(dst_dir, "scripts", "orphan.py"), "w", encoding="utf-8") as f:
            f.write("orphan\n")

        self.assertTrue(os.path.isfile(os.path.join(dst_dir, "scripts", "orphan.py")))
        updated = sync_trees(src_dir, dst_dir)
        self.assertTrue(any("orphan.py" in u for u in updated))
        self.assertFalse(os.path.exists(os.path.join(dst_dir, "scripts", "orphan.py")))

    # --------------------------------------------------------------------------
    # FIX-03: Scaffolding AGENT Manifest Header
    # --------------------------------------------------------------------------
    def test_fix_03_scaffold_agent_manifest_header(self):
        proj_dir = os.path.join(self.temp_dir, "services", "new-svc")
        args = argparse.Namespace(name="new-svc", profile="A", lang="ts", dir=proj_dir)
        rc = cmd_init(args)
        self.assertEqual(rc, 0)

        agent_file = os.path.join(proj_dir, "AGENT.md")
        self.assertTrue(os.path.isfile(agent_file))
        with open(agent_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("## 3. Local Nx Target Delegations", content)

    # --------------------------------------------------------------------------
    # FIX-04: Contracts Scope Tag
    # --------------------------------------------------------------------------
    def test_fix_04_contracts_scope_tag(self):
        template_file = REPO_ROOT / "templates" / "profiles" / "contracts-project.json"
        with open(template_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        tags = data.get("tags", [])
        self.assertIn("scope:shared", tags)
        self.assertNotIn("scope:contracts", tags)

    # --------------------------------------------------------------------------
    # FIX-05 & FIX-06: Multi-Tier VCS Alignment & Doctor Reachability Gate
    # --------------------------------------------------------------------------
    def test_fix_05_06_vcs_reachability_and_doctor_gate(self):
        provider = get_git_provider()
        ok, issues = provider.sync_check(base_branch="main")
        self.assertTrue(ok, f"Expected clean VCS sync, got: {issues}")

        doc_ok, msg = check_vcs_branches()
        self.assertTrue(doc_ok, f"Expected doctor VCS check pass, got: {msg}")

    # --------------------------------------------------------------------------
    # FIX-07: Zero-Stub Removal (Telemetry, FinOps, Policy, cppcheck)
    # --------------------------------------------------------------------------
    def test_fix_07_zero_stubs_replaced(self):
        # 1. Telemetry
        rc_tel = cmd_telemetry(argparse.Namespace(action="verify", root=str(REPO_ROOT), config=None))
        self.assertEqual(rc_tel, 0)

        # 2. FinOps
        rc_fin = cmd_finops(argparse.Namespace(action="check", root=str(REPO_ROOT), path=None))
        self.assertEqual(rc_fin, 0)

        # 3. Policy
        rc_pol = cmd_policy(argparse.Namespace(action="test", root=str(REPO_ROOT), scope=None))
        self.assertEqual(rc_pol, 0)

        # 4. cpp stack detection uses cppcheck
        cpp_dir = os.path.join(self.temp_dir, "cpp_app")
        os.makedirs(cpp_dir, exist_ok=True)
        with open(os.path.join(cpp_dir, "CMakeLists.txt"), "w") as f:
            f.write("cmake_minimum_required(VERSION 3.10)\n")
        stack_info = detect_stack(cpp_dir)
        self.assertEqual(stack_info["lang"], "cpp")
        self.assertEqual(stack_info["audit"], "cppcheck")

    # --------------------------------------------------------------------------
    # FIX-08: AST Taxonomy & Pattern Refinement
    # --------------------------------------------------------------------------
    def test_fix_08_ast_utc_clock_dimension_and_filter(self):
        utc_rule = next((r for r in STRUCTURAL_AST_RULES if r["id"] == "RULE-4.4-AST-NON-UTC-CLOCK"), None)
        self.assertIsNotNone(utc_rule)
        self.assertEqual(utc_rule["dim"], 4)  # type: ignore[index]

        # Path filter should match domain/persistence but ignore tests
        path_filter = utc_rule["path_filter"]  # type: ignore[index]
        self.assertTrue(path_filter("services/billing/domain/invoice.ts"))
        self.assertTrue(path_filter("services/auth/models/user.py"))
        self.assertFalse(path_filter("services/billing/tests/invoice_test.py"))
        self.assertFalse(path_filter("apps/web/src/components/button.tsx"))

    # --------------------------------------------------------------------------
    # FIX-09: Polyglot Heuristic Expansion
    # --------------------------------------------------------------------------
    def test_fix_09_polyglot_heuristics(self):
        # 1. Line ceiling co-located test matching (*_test.go, *_test.rs)
        long_go_test = os.path.join(self.temp_dir, "handler_test.go")
        with open(long_go_test, "w", encoding="utf-8") as f:
            f.write("\n".join(["// test line"] * 850))

        long_rs_test = os.path.join(self.temp_dir, "auth_test.rs")
        with open(long_rs_test, "w", encoding="utf-8") as f:
            f.write("\n".join(["// test line"] * 850))

        go_findings = scan_file_for_violations(long_go_test, max_file_lines=800)
        self.assertFalse(any(f["id"] == "RULE-2.6-FILE-SIZE-CEILING" for f in go_findings))

        rs_findings = scan_file_for_violations(long_rs_test, max_file_lines=800)
        self.assertFalse(any(f["id"] == "RULE-2.6-FILE-SIZE-CEILING" for f in rs_findings))

        # 2. RULE-8.1-EMPTY-CATCH in Python and Go (single-line and multi-line)
        bad_py = os.path.join(self.temp_dir, "worker.py")
        with open(bad_py, "w", encoding="utf-8") as f:
            f.write("try:\n    do_task()\n" + "except" + " ValueError: pass\n")

        py_findings = scan_file_for_violations(bad_py)
        self.assertTrue(any(f["id"] == "RULE-8.1-EMPTY-CATCH" for f in py_findings))

        bad_py_ellipsis = os.path.join(self.temp_dir, "worker_ellipsis.py")
        with open(bad_py_ellipsis, "w", encoding="utf-8") as f:
            f.write("try:\n    do_task()\n" + "except" + " ValueError: ...\n")
        py_ell_findings = scan_file_for_violations(bad_py_ellipsis)
        self.assertTrue(any(f["id"] == "RULE-8.1-EMPTY-CATCH" for f in py_ell_findings))

        bad_py_bare = os.path.join(self.temp_dir, "worker_bare.py")
        with open(bad_py_bare, "w", encoding="utf-8") as f:
            f.write("try:\n    do_task()\n" + "except" + ": pass\n")
        py_bare_findings = scan_file_for_violations(bad_py_bare)
        self.assertTrue(any(f["id"] == "RULE-8.1-EMPTY-CATCH" for f in py_bare_findings))

        bad_go_spaces = os.path.join(self.temp_dir, "server_spaces.go")
        with open(bad_go_spaces, "w", encoding="utf-8") as f:
            f.write("if err != nil {   }\n")
        go_sp_findings = scan_file_for_violations(bad_go_spaces)
        self.assertTrue(any(f["id"] == "RULE-8.1-EMPTY-CATCH" for f in go_sp_findings))

        # 3. RULE-4.3-NON-UTC-TIMESTAMP in Go and PHP
        bad_go_time = os.path.join(self.temp_dir, "domain", "order.go")
        os.makedirs(os.path.dirname(bad_go_time), exist_ok=True)
        with open(bad_go_time, "w", encoding="utf-8") as f:
            f.write("package domain\nfunc Now() { t := time.Now() }\n")

        go_time_findings = scan_file_for_violations(bad_go_time)
        self.assertTrue(any(f["id"] == "RULE-4.3-NON-UTC-TIMESTAMP" for f in go_time_findings))

        bad_php_date = os.path.join(self.temp_dir, "models", "User.php")
        os.makedirs(os.path.dirname(bad_php_date), exist_ok=True)
        with open(bad_php_date, "w", encoding="utf-8") as f:
            f.write("<?php class User { public function stamp() { return date('Y-m-d'); } }\n")

        php_date_findings = scan_file_for_violations(bad_php_date)
        self.assertTrue(any(f["id"] == "RULE-4.3-NON-UTC-TIMESTAMP" for f in php_date_findings))

    # --------------------------------------------------------------------------
    # FIX-10: Worktree Creation Existing Branch
    # --------------------------------------------------------------------------
    def test_fix_10_worktree_existing_branch(self):
        repo_dir = os.path.join(self.temp_dir, "repo")
        subprocess.run(["git", "init", "-b", "main", repo_dir], capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)

        with open(os.path.join(repo_dir, "init.txt"), "w") as f:
            f.write("init\n")
        subprocess.run(["git", "add", "init.txt"], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True)

        # Create branch 'feature-1'
        subprocess.run(["git", "branch", "feature-1"], cwd=repo_dir, check=True)

        # Calling cmd_worktree create on existing branch should not crash with branch exists error
        orig_cwd = os.getcwd()
        try:
            os.chdir(repo_dir)
            args = argparse.Namespace(action="create", branch="feature-1")
            rc = cmd_worktree(args)
            self.assertEqual(rc, 0)
        finally:
            os.chdir(orig_cwd)

    # --------------------------------------------------------------------------
    # FIX-11: Release Scoping to Tag & --prod Handling
    # --------------------------------------------------------------------------
    def test_fix_11_release_scoping_and_prod(self):
        repo_dir = os.path.join(self.temp_dir, "rel_repo")
        subprocess.run(["git", "init", "-b", "main", repo_dir], capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)

        changes_dir = os.path.join(repo_dir, "docs", "changes")
        os.makedirs(changes_dir, exist_ok=True)

        # 1. Pre-tag change file
        old_change = os.path.join(changes_dir, "2026-10-01-old.md")
        with open(old_change, "w", encoding="utf-8") as f:
            f.write("# Old Change\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "v1.0.0 commit"], cwd=repo_dir, check=True)
        subprocess.run(["git", "tag", "-a", "v1.0.0", "-m", "v1.0.0"], cwd=repo_dir, check=True)

        # 2. Post-tag new change file
        new_change = os.path.join(changes_dir, "2026-10-28-new.md")
        with open(new_change, "w", encoding="utf-8") as f:
            f.write("# New Scoped Change\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "feature commit"], cwd=repo_dir, check=True)

        orig_cwd = os.getcwd()
        try:
            os.chdir(repo_dir)
            args = argparse.Namespace(action="finalize", prod=True, version="v1.1.0")
            rc = cmd_release(args)
            self.assertEqual(rc, 0)

            rel_file = os.path.join(repo_dir, "docs", "releases", "RELEASE_v1.1.0.md")
            self.assertTrue(os.path.isfile(rel_file))
            with open(rel_file, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("Production Release Notes: v1.1.0", content)
            self.assertIn("2026-10-28-new.md", content)
            self.assertNotIn("2026-10-01-old.md", content)

            # Also test finalize with version_flag alias
            args_flag = argparse.Namespace(action="finalize", prod=True, version=None, version_flag="v1.2.0")
            rc_flag = cmd_release(args_flag)
            self.assertEqual(rc_flag, 0)
            self.assertTrue(os.path.isfile(os.path.join(repo_dir, "docs", "releases", "RELEASE_v1.2.0.md")))
        finally:
            os.chdir(orig_cwd)


if __name__ == "__main__":
    unittest.main()
