#!/usr/bin/env python3
"""
Unit and integration tests for audit-runner CLI tool and 10-dimension audit engine.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "scripts" / "bin"


class TestAuditRunner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_directory_passes_audit(self):
        clean_file = os.path.join(self.temp_dir, "service.ts")
        with open(clean_file, "w", encoding="utf-8") as f:
            f.write("export class PureService { compute(): number { return 42; } }\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        self.assertEqual(res["verdict"], "PASS")
        self.assertEqual(res["total_blocking"], 0)

    def test_banned_patterns_detected_as_blocking(self):
        domain_dir = os.path.join(self.temp_dir, "domain")
        os.makedirs(domain_dir, exist_ok=True)
        bad_domain = os.path.join(domain_dir, "user.ts")
        with open(bad_domain, "w", encoding="utf-8") as f:
            f.write("import { Column } from 'typeorm';\nexport class User {}\n")

        tests_dir = os.path.join(self.temp_dir, "tests", "integration")
        os.makedirs(tests_dir, exist_ok=True)
        bad_test = os.path.join(tests_dir, "repo.test.ts")
        bad_snippet = "const db = createConnection({ type: '" + "sqlite', database: ':" + "memory:' });\n"
        with open(bad_test, "w", encoding="utf-8") as f:
            f.write(bad_snippet)

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertGreaterEqual(res["total_blocking"], 2)

    def test_empty_catch_block_detected(self):
        bad_file = os.path.join(self.temp_dir, "handler.ts")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("try { doWork(); } catch (e) {}\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        self.assertEqual(res["verdict"], "FAIL")
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-8.1-EMPTY-CATCH", found_ids)

    def test_skipped_test_detected(self):
        bad_spec = os.path.join(self.temp_dir, "order.spec.ts")
        with open(bad_spec, "w", encoding="utf-8") as f:
            f.write("it." + "skip('should charge card', () => {});\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        self.assertEqual(res["verdict"], "FAIL")
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-10.2-SKIPPED-TEST", found_ids)

    def test_file_size_ceiling_detected(self):
        big_file = os.path.join(self.temp_dir, "monolith.ts")
        with open(big_file, "w", encoding="utf-8") as f:
            for i in range(850):
                f.write(f"export const item_{i} = {i};\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-2.6-FILE-SIZE-CEILING", found_ids)

    def test_over_nested_directory_detected(self):
        deep_dir = os.path.join(self.temp_dir, "l1", "l2", "l3", "l4", "l5", "l6", "l7")
        os.makedirs(deep_dir, exist_ok=True)
        deep_file = os.path.join(deep_dir, "deep.ts")
        with open(deep_file, "w", encoding="utf-8") as f:
            f.write("export const deep = true;\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-2.5-OVER-NESTED-DIRECTORY", found_ids)

    def test_generic_dumping_ground_detected(self):
        dump_dir = os.path.join(self.temp_dir, "src", "utils")
        os.makedirs(dump_dir, exist_ok=True)
        dump_file = os.path.join(dump_dir, "helper.ts")
        with open(dump_file, "w", encoding="utf-8") as f:
            f.write("export const helper = true;\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-2.8-GENERIC-DUMPING-GROUND", found_ids)

    def test_pii_logging_detected(self):
        services_dir = os.path.join(self.temp_dir, "services", "auth")
        os.makedirs(services_dir, exist_ok=True)
        bad_log_file = os.path.join(services_dir, "auth.ts")
        with open(bad_log_file, "w", encoding="utf-8") as f:
            f.write("logger.info('Authenticating user', password);\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-6.5-PII-LOGGING", found_ids)

    def test_libs_directory_scanned_for_violations(self):
        libs_dir = os.path.join(self.temp_dir, "libs", "core-contracts", "src")
        os.makedirs(libs_dir, exist_ok=True)
        bad_lib = os.path.join(libs_dir, "types.ts")
        with open(bad_lib, "w", encoding="utf-8") as f:
            f.write("export const rawValue: any = {};\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-8.2-EXPLICIT-ANY", found_ids)

    def test_polyglot_patterns_detected(self):
        # 1. Go ORM import in domain
        domain_dir = os.path.join(self.temp_dir, "domain")
        os.makedirs(domain_dir, exist_ok=True)
        go_domain = os.path.join(domain_dir, "entity.go")
        with open(go_domain, "w", encoding="utf-8") as f:
            f.write("package domain\nimport \"gorm.io/gorm\"\n")

        # 2. Python exception PII log
        apps_dir = os.path.join(self.temp_dir, "apps", "api")
        os.makedirs(apps_dir, exist_ok=True)
        py_api = os.path.join(apps_dir, "views.py")
        with open(py_api, "w", encoding="utf-8") as f:
            f.write("logger.warning(f'Failed login for user with {password}')\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-2.1-ORM-IN-DOMAIN", found_ids)
        self.assertIn("RULE-6.5-PII-LOGGING", found_ids)

    def test_deprecated_datetime_utcnow_flagged(self):
        d_dir = os.path.join(self.temp_dir, "models")
        os.makedirs(d_dir, exist_ok=True)
        bad_file = os.path.join(d_dir, "entity.py")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("import datetime\ncreated = datetime." + "utcnow()\n")
        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-4.3-NON-UTC-TIMESTAMP", found_ids)

    def test_tautological_assert_false_flagged(self):
        t_dir = os.path.join(self.temp_dir, "tests")
        os.makedirs(t_dir, exist_ok=True)
        bad_test = os.path.join(t_dir, "test_vacuous.py")
        with open(bad_test, "w", encoding="utf-8") as f:
            f.write("def test_vacuous():\n    " + "assert " + "False ==" + " False\n")
        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-10.1-TAUTOLOGICAL-TEST", found_ids)

    def test_markdown_report_includes_tier_1_checks(self):
        clean_file = os.path.join(self.temp_dir, "service.ts")
        with open(clean_file, "w", encoding="utf-8") as f:
            f.write("export const value = 1;\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("## 3. Mandatory Tier 1 Invariant Checks", proc.stdout)
        self.assertIn("[x] Single Monorepo compliance", proc.stdout)
        self.assertIn("## 4. Next Step & Protocol Action", proc.stdout)

    def test_baseline_ratchet_suppresses_known_issues(self):
        bad_file = os.path.join(self.temp_dir, "legacy.ts")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("try { doLegacy(); } catch (e) {}\n")

        baseline_json = os.path.join(self.temp_dir, "baseline.json")

        proc1 = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--save-baseline", baseline_json],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc1.returncode, 0)
        self.assertTrue(os.path.exists(baseline_json))

        proc2 = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--baseline", baseline_json, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc2.returncode, 0)
        res2 = json.loads(proc2.stdout)
        self.assertEqual(res2["verdict"], "PASS")
        self.assertEqual(res2["total_blocking"], 0)
        self.assertGreaterEqual(res2["baseline_suppressed"], 1)

    def test_audit_repo_itself_clean(self):
        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", str(REPO_ROOT), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected clean audit of repo, got: {proc.stdout}")
        res = json.loads(proc.stdout)
        self.assertEqual(res["verdict"], "PASS")
        self.assertEqual(res["total_blocking"], 0)


    def test_nonexistent_scope_fails(self):
        nonexistent = os.path.join(self.temp_dir, "does_not_exist")
        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", nonexistent],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("does not exist", proc.stderr)

    def test_binary_files_skipped(self):
        png_file = os.path.join(self.temp_dir, "asset.png")
        with open(png_file, "wb") as f:
            f.write(b"SELECT * FROM users; catch () {}")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        self.assertEqual(len(res["findings"]), 0)

    def test_dummy_secret_exempted(self):
        service_file = os.path.join(self.temp_dir, "auth.ts")
        with open(service_file, "w", encoding="utf-8") as f:
            f.write("export const apiKey = 'mock_secret_key_12345678901234';\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertNotIn("RULE-5.1-HARDCODED-SECRET", found_ids)

    def test_unbounded_scan_without_semicolon(self):
        apps_dir = os.path.join(self.temp_dir, "apps", "api")
        os.makedirs(apps_dir, exist_ok=True)
        query_file = os.path.join(apps_dir, "repo.ts")
        with open(query_file, "w", encoding="utf-8") as f:
            f.write("const q = \"SELECT * FROM users\";\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-1.1-UNBOUNDED-SCAN", found_ids)

    def test_corrupted_baseline_handled_gracefully(self):
        bad_baseline = os.path.join(self.temp_dir, "corrupt.json")
        with open(bad_baseline, "w", encoding="utf-8") as f:
            f.write("NOT_VALID_JSON{{{")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--baseline", bad_baseline, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Failed to parse baseline", proc.stdout)


    def test_go_and_python_test_conventions_detected(self):
        tests_dir = os.path.join(self.temp_dir, "tests")
        os.makedirs(tests_dir, exist_ok=True)

        go_test = os.path.join(tests_dir, "user_test.go")
        with open(go_test, "w", encoding="utf-8") as f:
            f.write("package test\nimport \"testing\"\nfunc TestUser(t *testing.T) { " + "assert." + "True(true) }\n")

        py_test = os.path.join(tests_dir, "test_order.py")
        with open(py_test, "w", encoding="utf-8") as f:
            f.write("import unittest\n@" + "unittest.skip('temporarily disabled')\ndef test_fn(): pass\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-10.1-TAUTOLOGICAL-TEST", found_ids)
        self.assertIn("RULE-10.2-SKIPPED-TEST", found_ids)

    def test_packages_directory_scanned_for_violations(self):
        pkg_dir = os.path.join(self.temp_dir, "packages", "common", "src")
        os.makedirs(pkg_dir, exist_ok=True)
        bad_pkg_file = os.path.join(pkg_dir, "logger.ts")
        with open(bad_pkg_file, "w", encoding="utf-8") as f:
            f.write("console.log('Unstructured debug statement');\n")

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        res = json.loads(proc.stdout)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-6.1-BARE-CONSOLE-LOG", found_ids)

    def test_subproject_depth_calculation(self):
        # 6 levels inside services/billing: src/l1/l2/l3/l4/l5 (total 8 parts from root) -> PASS
        ok_dir = os.path.join(self.temp_dir, "services", "billing", "src", "l1", "l2", "l3", "l4", "l5")
        os.makedirs(ok_dir, exist_ok=True)
        ok_file = os.path.join(ok_dir, "billing.ts")
        with open(ok_file, "w", encoding="utf-8") as f:
            f.write("export const ok = 1;\n")

        proc1 = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc1.returncode, 0)
        res1 = json.loads(proc1.stdout)
        found_ids1 = [f["id"] for f in res1["findings"]]
        self.assertNotIn("RULE-2.5-OVER-NESTED-DIRECTORY", found_ids1)

        # 7 levels inside services/billing: src/l1/l2/l3/l4/l5/l6/l7 (total 10 parts from root) -> FAIL
        too_deep = os.path.join(self.temp_dir, "services", "billing", "src", "l1", "l2", "l3", "l4", "l5", "l6", "l7")
        os.makedirs(too_deep, exist_ok=True)
        deep_file = os.path.join(too_deep, "deep.ts")
        with open(deep_file, "w", encoding="utf-8") as f:
            f.write("export const deep = 1;\n")

        proc2 = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc2.returncode, 0)
        res2 = json.loads(proc2.stdout)
        found_ids2 = [f["id"] for f in res2["findings"]]
        self.assertIn("RULE-2.5-OVER-NESTED-DIRECTORY", found_ids2)

    def test_dict_baseline_handled_gracefully(self):
        bad_file = os.path.join(self.temp_dir, "legacy_file.ts")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("try { doLegacy(); } catch (e) {}\n")

        dict_baseline = os.path.join(self.temp_dir, "dict_baseline.json")
        baseline_content = {
            "verdict": "FAIL",
            "findings": [
                {
                    "id": "RULE-8.1-EMPTY-CATCH",
                    "file": bad_file.replace("\\", "/"),
                    "line": 1,
                }
            ],
        }
        with open(dict_baseline, "w", encoding="utf-8") as f:
            json.dump(baseline_content, f)

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", self.temp_dir, "--baseline", dict_baseline, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        self.assertEqual(res["verdict"], "PASS")
        self.assertEqual(res["baseline_suppressed"], 1)

    def test_diff_fallback_to_head_when_diff_base_missing(self):
        """When diff_base does not exist, fallback to HEAD~1 and catch defects."""
        repo_dir = os.path.join(self.temp_dir, "repo")
        os.makedirs(repo_dir, exist_ok=True)
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)

        with open(os.path.join(repo_dir, "clean.ts"), "w", encoding="utf-8") as f:
            f.write("export const val = 1;\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True)

        test_dir = os.path.join(repo_dir, "tests", "integration")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "repo.test.ts"), "w", encoding="utf-8") as f:
            f.write("const db = createConnection({ type: 'sqlite', database: ':memory:' });\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add bad test"], cwd=repo_dir, check=True, capture_output=True)

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", repo_dir, "--diff", "origin/nonexistent", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertIn("fallback", proc.stderr.lower())
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-4.1-SQLITE-IN-INTEGRATION", found_ids)

    def test_diff_fallback_to_target_scan_when_single_commit(self):
        """When diff_base and HEAD~1 both fail, fallback to full target scan."""
        repo_dir = os.path.join(self.temp_dir, "single_commit_repo")
        os.makedirs(repo_dir, exist_ok=True)
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)

        test_dir = os.path.join(repo_dir, "tests", "integration")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "repo.test.ts"), "w", encoding="utf-8") as f:
            f.write("const db = createConnection({ type: 'sqlite', database: ':memory:' });\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init bad test"], cwd=repo_dir, check=True, capture_output=True)

        proc = subprocess.run(
            [str(BIN_DIR / "audit-runner"), "--scope", repo_dir, "--diff", "origin/main", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertIn("Falling back to full scan", proc.stderr)
        found_ids = [f["id"] for f in res["findings"]]
        self.assertIn("RULE-4.1-SQLITE-IN-INTEGRATION", found_ids)


if __name__ == "__main__":
    unittest.main()

