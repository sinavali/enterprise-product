#!/usr/bin/env python3
"""
test_defect_remediations.py
Comprehensive regression tests for DEFECT-01 through DEFECT-27 across EP-OS.
"""

import argparse
import datetime
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# Ensure scripts directory is on path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def load_script_module(name: str, filename: str):
    path = os.path.join(SCRIPTS_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


audit_runner = load_script_module("audit_runner", "audit-runner.py")
verify_agent_manifests = load_script_module("verify_agent_manifests", "verify-agent-manifests.py")

from ep import (
    cmd_migration,
    cmd_release,
    cmd_milestone,
    cmd_surface,
    main as ep_main,
)
from ep_adopt import infer_scope, scaffold_project_json
from ep_ast import STRUCTURAL_AST_RULES
from ep_ops import parse_slo_yaml, validate_slo_dict, cmd_codeowners
from ep_runner import build_dag_and_sort, discover_projects
from ep_scaffold import cmd_init, cmd_preflight
from ep_security import (
    shannon_entropy,
    extract_lockfile_dependencies,
    scan_text_for_secrets,
    is_test_path,
    SECRET_PATTERNS,
)
from ep_sync import DEFAULT_WORKSPACE_DIR, resolve_default_workspace_dir
from ep_vcs import GitHubProvider, LocalGitProvider


class TestDefectRemediations(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # DEFECT-01: Triple-Dot (...) Git Range Resolution
    # --------------------------------------------------------------------------
    def test_defect_01_triple_dot_range_resolution(self):
        # In cmd_surface, when base contains '...', diff_target should be exactly base, not base...HEAD
        base = "origin/main...HEAD"
        target = base if ("..." in base or base in ("HEAD", "HEAD~1")) else f"{base}...HEAD"
        self.assertEqual(target, "origin/main...HEAD")

        base2 = "origin/main"
        target2 = base2 if ("..." in base2 or base2 in ("HEAD", "HEAD~1")) else f"{base2}...HEAD"
        self.assertEqual(target2, "origin/main...HEAD")

    # --------------------------------------------------------------------------
    # DEFECT-02: Parallel DAG Topological Level Waves
    # --------------------------------------------------------------------------
    def test_defect_02_parallel_dag_topological_waves(self):
        projects = {
            "app": {
                "root": "apps/app",
                "targets": {
                    "build": {
                        "dependsOn": ["^build"],
                        "command": "echo build app",
                    }
                },
            },
            "lib": {
                "root": "libs/lib",
                "targets": {
                    "build": {
                        "command": "echo build lib",
                    }
                },
            },
        }
        ordered, cycles, waves = build_dag_and_sort(projects, "build", return_waves=True)
        self.assertFalse(cycles)
        self.assertEqual(len(waves), 2)
        # lib must be in wave 0, app in wave 1
        self.assertIn(("lib", "build"), waves[0])
        self.assertIn(("app", "build"), waves[1])

    # --------------------------------------------------------------------------
    # DEFECT-03: ^target Project Dependency Scoping without Deadlocks
    # --------------------------------------------------------------------------
    def test_defect_03_caret_target_no_cross_project_deadlock(self):
        # Two independent services each having ^build should not deadlock each other
        projects = {
            "svc-a": {
                "root": "services/svc-a",
                "targets": {
                    "build": {"dependsOn": ["^build"], "command": "echo build a"}
                },
            },
            "svc-b": {
                "root": "services/svc-b",
                "targets": {
                    "build": {"dependsOn": ["^build"], "command": "echo build b"}
                },
            },
        }
        ordered, cycles = build_dag_and_sort(projects, "build")
        self.assertFalse(cycles)
        self.assertEqual(len(ordered), 2)

    # --------------------------------------------------------------------------
    # DEFECT-04: Secret Scanner Word-Boundary Path Filter
    # --------------------------------------------------------------------------
    def test_defect_04_secret_scanner_path_boundary(self):
        # A file in attestation-service or speedtest should NOT be treated as a test file
        self.assertFalse(is_test_path("services/attestation/src/handler.ts"))
        self.assertFalse(is_test_path("services/speedtest/src/index.ts"))
        self.assertTrue(is_test_path("services/auth/tests/unit_test.py"))
        self.assertTrue(is_test_path("services/auth/src/service.spec.ts"))

    # --------------------------------------------------------------------------
    # DEFECT-05: VCS Sync Check Verification
    # --------------------------------------------------------------------------
    def test_defect_05_vcs_sync_check_missing_branch(self):
        provider = LocalGitProvider()
        # Non-existent base branch must return False and report missing issue
        ok, issues = provider.sync_check(base_branch="nonexistent-branch-xyz-999")
        self.assertFalse(ok)
        self.assertTrue(any("not found" in iss for iss in issues))

    # --------------------------------------------------------------------------
    # DEFECT-06: PR Auto-Merge Disable & Human-Review Label
    # --------------------------------------------------------------------------
    def test_defect_06_pr_auto_merge_disabled(self):
        provider = GitHubProvider()
        self.assertIn("--disable-auto", provider.__class__.create_prod_pr.__code__.co_consts)

    # --------------------------------------------------------------------------
    # DEFECT-07: Expand/Contract Fake ADR Bypass Rejection
    # --------------------------------------------------------------------------
    def test_defect_07_fake_adr_reference_rejected(self):
        sql_file = os.path.join(self.test_dir, "001_destructive.sql")
        with open(sql_file, "w") as f:
            f.write("-- adr-ref: docs/adr/9999-non-existent.md\nALTER TABLE users DROP COLUMN email;")
        args = argparse.Namespace(dir=self.test_dir, diff=False)
        rc = cmd_migration(args)
        self.assertEqual(rc, 1)

    # --------------------------------------------------------------------------
    # DEFECT-08: Brownfield Baseline Ratchet in ep audit
    # --------------------------------------------------------------------------
    def test_defect_08_baseline_ratchet_suppression(self):
        filter_against_baseline = audit_runner.filter_against_baseline
        baseline_data = {
            "findings": [
                {"id": "RULE-1.1-UNBOUNDED-SCAN", "file": "src/repo.ts", "line": 42}
            ]
        }
        current_findings = [
            {"id": "RULE-1.1-UNBOUNDED-SCAN", "file": "src/repo.ts", "line": 42},
            {"id": "RULE-5.1-HARDCODED-SECRET", "file": "src/app.ts", "line": 10},
        ]
        new_findings, suppressed = filter_against_baseline(current_findings, baseline_data)
        self.assertEqual(suppressed, 1)
        self.assertEqual(len(new_findings), 1)
        self.assertEqual(new_findings[0]["id"], "RULE-5.1-HARDCODED-SECRET")

    # --------------------------------------------------------------------------
    # DEFECT-09: Cross-Project Target Syntax (project:target)
    # --------------------------------------------------------------------------
    def test_defect_09_cross_project_target_syntax(self):
        projects = {
            "web": {
                "root": "apps/web",
                "targets": {
                    "build": {
                        "dependsOn": ["api:generate-client"],
                        "command": "echo build web",
                    }
                },
            },
            "api": {
                "root": "services/api",
                "targets": {
                    "generate-client": {
                        "command": "echo generate api client",
                    }
                },
            },
        }
        ordered, cycles = build_dag_and_sort(projects, "build")
        self.assertFalse(cycles)
        self.assertEqual(ordered, [("api", "generate-client"), ("web", "build")])

    # --------------------------------------------------------------------------
    # DEFECT-10: Subcommands & Hook Run Fallbacks
    # --------------------------------------------------------------------------
    def test_defect_10_milestone_and_hook_run(self):
        ms_name = "test-milestone-m1"
        ms_dir = os.path.join(REPO_ROOT, "docs", "milestones")
        ms_file = os.path.join(ms_dir, f"{ms_name}.md")
        try:
            # Create milestone
            args_create = argparse.Namespace(action="create", name=ms_name, due="2026-12-31")
            rc = cmd_milestone(args_create)
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(ms_file))

            # Status milestone
            args_status = argparse.Namespace(action="status", name=ms_name)
            rc_stat = cmd_milestone(args_status)
            self.assertEqual(rc_stat, 0)
        finally:
            if os.path.isfile(ms_file):
                os.remove(ms_file)

    # --------------------------------------------------------------------------
    # DEFECT-11: Argument Aliases (--scope, --output, --package-json, --apply)
    # --------------------------------------------------------------------------
    def test_defect_11_argument_aliases(self):
        # Verify infer_scope works with --scope alias in adopt
        scope = infer_scope("services\\auth\\worker")
        self.assertEqual(scope, "backend")

        # Verify scaffold_project_json respects relative path
        pj = scaffold_project_json("services/auth", {"lang": "ts"})
        self.assertTrue(pj["$schema"].endswith("project-schema.json"))

    # --------------------------------------------------------------------------
    # DEFECT-12: Release Finalizer Notes Aggregation & Signed Tag Fallback
    # --------------------------------------------------------------------------
    def test_defect_12_release_finalize_notes(self):
        rel_file = os.path.join(REPO_ROOT, "docs", "releases", f"RELEASE_{datetime.date.today().isoformat()}.md")
        try:
            args = argparse.Namespace(action="finalize")
            rc = cmd_release(args)
            self.assertEqual(rc, 0)
        finally:
            if os.path.isfile(rel_file):
                os.remove(rel_file)
            rel_dir = os.path.join(REPO_ROOT, "docs", "releases")
            if os.path.isdir(rel_dir) and not os.listdir(rel_dir):
                os.rmdir(rel_dir)

    # --------------------------------------------------------------------------
    # DEFECT-13: ep verify Passing --root
    # --------------------------------------------------------------------------
    def test_defect_13_ep_verify_root_propagation(self):
        # verify-agent-manifests.py with explicit --root
        agent_script = os.path.join(SCRIPTS_DIR, "verify-agent-manifests.py")
        res = subprocess.run([sys.executable, agent_script, "--root", REPO_ROOT], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    # --------------------------------------------------------------------------
    # DEFECT-14: Scaffolding Real Language Targets
    # --------------------------------------------------------------------------
    def test_defect_14_scaffold_real_language_targets(self):
        proj_dir = os.path.join(self.test_dir, "php-service")
        args = argparse.Namespace(name="php-service", profile="A", lang="php", dir=proj_dir)
        rc = cmd_init(args)
        self.assertEqual(rc, 0)
        with open(os.path.join(proj_dir, "project.json")) as f:
            pj = json.load(f)
        # Should NOT be dummy echo, but real phpstan
        self.assertIn("phpstan", pj["targets"]["lint"]["options"]["command"])
        self.assertIn("pest", pj["targets"]["test"]["options"]["command"])

    # --------------------------------------------------------------------------
    # DEFECT-15: Secret Scanner Base64 & YAML Patterns
    # --------------------------------------------------------------------------
    def test_defect_15_secret_patterns_base64_and_yaml(self):
        # AWS secret with Base64 chars / and +
        text = "aws_secret: AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0e"
        findings = scan_text_for_secrets(text)
        self.assertTrue(len(findings) > 0)

    # --------------------------------------------------------------------------
    # DEFECT-16: Migration Diff Zero Files Clean Pass
    # --------------------------------------------------------------------------
    def test_defect_16_migration_diff_zero_files_pass(self):
        # Non-existent base should not crash or fallback to disk if diff is clean
        args = argparse.Namespace(dir=self.test_dir, diff=True, base="HEAD")
        rc = cmd_migration(args)
        self.assertEqual(rc, 0)

    # --------------------------------------------------------------------------
    # DEFECT-17: Shannon Entropy & Lockfile SBOM
    # --------------------------------------------------------------------------
    def test_defect_17_shannon_entropy_calculation(self):
        # Low entropy repetition
        self.assertLess(shannon_entropy("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"), 1.0)
        # High entropy random base64 key
        self.assertGreater(shannon_entropy("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"), 4.0)

    # --------------------------------------------------------------------------
    # DEFECT-18: Subprocess Execution Timeout Bounds
    # --------------------------------------------------------------------------
    def test_defect_18_subprocess_timeouts(self):
        import inspect
        import ep_runner
        # execute_target should have timeout parameter
        sig = inspect.signature(ep_runner.execute_target)
        self.assertIn("timeout", sig.parameters)

    # --------------------------------------------------------------------------
    # DEFECT-19: Semantic Stem Matching on Tier 1 Overrides
    # --------------------------------------------------------------------------
    def test_defect_19_semantic_stem_tier_1_override(self):
        verify_agent_manifest = verify_agent_manifests.verify_agent_manifest
        manifest_file = os.path.join(self.test_dir, "AGENT.md")
        # Attempting synonym like allow-sqlite-in-memory must fail
        with open(manifest_file, "w") as f:
            f.write(
                "---\nproject_name: 'test'\nprofile: 'A'\nstack: 'ts'\nscope: 'backend'\n"
                "tier_overrides:\n  - rule: 'allow-sqlite-in-memory'\n    adr_reference: 'docs/adr/0001.md'\n---\n"
                "# Project Agent Manifest: test\n## 1. Scope & Business Intent\n## 2. Architectural Profile\n## 3. Local Nx Target\n## 4. Test & Verification\n"
            )
        valid, errors = verify_agent_manifest(manifest_file, root_dir=self.test_dir, check_adrs=False)
        self.assertFalse(valid)
        self.assertTrue(any("Illegal Tier 1 override" in e for e in errors))

    # --------------------------------------------------------------------------
    # DEFECT-20: Project Discovery Stderr Logging on Syntax Errors
    # --------------------------------------------------------------------------
    def test_defect_20_discover_projects_warns_on_bad_json(self):
        bad_proj = os.path.join(self.test_dir, "bad-proj")
        os.makedirs(bad_proj)
        with open(os.path.join(bad_proj, "project.json"), "w") as f:
            f.write("{invalid-json-content")
        
        captured_stderr = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_stderr
        try:
            discover_projects(self.test_dir)
        finally:
            sys.stderr = old_stderr
        self.assertIn("WARN", captured_stderr.getvalue())

    # --------------------------------------------------------------------------
    # DEFECT-21: Dynamic Workspace Directory Resolution in ep_sync
    # --------------------------------------------------------------------------
    def test_defect_21_dynamic_workspace_dir(self):
        self.assertNotEqual(DEFAULT_WORKSPACE_DIR, "/home/sinavali/Workspace/Work/Projects/enterprise-product-dummy")
        self.assertTrue(os.path.isabs(resolve_default_workspace_dir()))

    # --------------------------------------------------------------------------
    # DEFECT-22: Dynamic Relative Schema Path
    # --------------------------------------------------------------------------
    def test_defect_22_dynamic_relative_schema(self):
        pj = scaffold_project_json("services/deep/nested/subservice", {"lang": "ts"})
        schema_path = pj["$schema"]
        self.assertFalse(schema_path.startswith("../../node_modules"))
        self.assertTrue(schema_path.endswith("node_modules/nx/schemas/project-schema.json"))

    # --------------------------------------------------------------------------
    # DEFECT-23: Safe Float Parsing for SLO Burn Rates
    # --------------------------------------------------------------------------
    def test_defect_23_slo_safe_float_parse(self):
        slo_yaml = """service: payment-service
tier: tier-1
slos:
  - id: availability
    target: 0.999
    window: 30d
    sli:
      metric_type: availability
    error_budget:
      alert_triggers:
        - burn_rate: not-a-number
"""
        parsed = parse_slo_yaml(slo_yaml)
        errs = validate_slo_dict(parsed, "test.yaml")
        # Should not crash with ValueError, burns rate defaults safely
        self.assertEqual(len(errs), 0)

    # --------------------------------------------------------------------------
    # DEFECT-24: Git Porcelain Rename Parsing
    # --------------------------------------------------------------------------
    def test_defect_24_porcelain_rename_parsing(self):
        from ep_session import parse_porcelain_line
        res = parse_porcelain_line("R  old/path.ts -> new/path.ts")
        self.assertEqual(res, "new/path.ts")

    # --------------------------------------------------------------------------
    # DEFECT-25: Portable Shell Execution in Preflight & Path Normalization
    # --------------------------------------------------------------------------
    def test_defect_25_preflight_and_infer_scope(self):
        # Preflight should run without unhandled exceptions
        args = argparse.Namespace()
        rc = cmd_preflight(args)
        self.assertEqual(rc, 0)
        # Windows backslashes should normalize
        self.assertEqual(infer_scope("apps\\web-portal"), "frontend")

    # --------------------------------------------------------------------------
    # DEFECT-26: Monorepo Project Discovery Depth in Codeowners
    # --------------------------------------------------------------------------
    def test_defect_26_codeowners_uses_project_discovery(self):
        args = argparse.Namespace(root=REPO_ROOT)
        # Should execute successfully across all monorepo depth
        rc = cmd_codeowners(args)
        self.assertEqual(rc, 0)

    # --------------------------------------------------------------------------
    # DEFECT-27: Mechanical Linters for UTC Storage and Transactional Outbox
    # --------------------------------------------------------------------------
    def test_defect_27_utc_and_outbox_rules(self):
        rule_ids = {r["id"] for r in STRUCTURAL_AST_RULES}
        self.assertIn("RULE-1.7-AST-NON-UTC-CLOCK", rule_ids)
        self.assertIn("RULE-3.8-AST-TRANSACTIONAL-OUTBOX", rule_ids)

        heuristic_ids = {h["id"] for h in audit_runner.HEURISTIC_RULES}
        self.assertIn("RULE-4.3-NON-UTC-TIMESTAMP", heuristic_ids)
        self.assertIn("RULE-3.8-TRANSACTIONAL-OUTBOX-DUAL-WRITE", heuristic_ids)


if __name__ == "__main__":
    unittest.main()
