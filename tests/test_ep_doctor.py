"""
test_ep_doctor.py — Unit and integration tests for EP-OS Doctor and Product Skill generator
"""

import os
import shutil
import subprocess
import tempfile
import unittest

from scripts.ep_doctor import (
    check_codeowners,
    check_container_engine,
    check_git_hooks,
    check_manifests,
    check_product_skill,
    check_project_contracts,
    check_vcs_branches,
    cmd_ci,
    generate_product_skill,
    run_doctor,
)


class TestEpDoctor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_check_hooks(self):
        # Empty dir -> fail
        ok, msg = check_git_hooks(self.test_dir)
        self.assertFalse(ok)

        # Mock hooks
        hooks_dir = os.path.join(self.test_dir, ".git", "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        for h in ["pre-commit", "pre-push", "commit-msg"]:
            with open(os.path.join(hooks_dir, h), "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
        ok, msg = check_git_hooks(self.test_dir)
        self.assertTrue(ok)

    def test_check_codeowners(self):
        ok, msg = check_codeowners(self.test_dir)
        self.assertFalse(ok)

        gh_dir = os.path.join(self.test_dir, ".github")
        os.makedirs(gh_dir, exist_ok=True)
        with open(os.path.join(gh_dir, "CODEOWNERS"), "w") as f:
            f.write("* @core-team\n")

        ok, msg = check_codeowners(self.test_dir)
        self.assertTrue(ok)

    def test_check_nx_contracts(self):
        ok, msg = check_project_contracts(self.test_dir)
        self.assertFalse(ok)

        with open(os.path.join(self.test_dir, "project.json"), "w") as f:
            f.write('{"name": "test-pkg", "targets": {"test": {}}}')

        ok, msg = check_project_contracts(self.test_dir)
        self.assertTrue(ok)

    def test_check_agent_manifest(self):
        ok, msg = check_manifests(self.test_dir)
        self.assertFalse(ok)

        with open(os.path.join(self.test_dir, "AGENT.md"), "w") as f:
            f.write("# Agent Manifest\n")

        ok, msg = check_manifests(self.test_dir)
        self.assertTrue(ok)

    def test_check_product_skill(self):
        ok, msg = check_product_skill(self.test_dir)
        self.assertFalse(ok)

        with open(os.path.join(self.test_dir, "PRODUCT_SKILL.md"), "w") as f:
            f.write("# Tailored Product Skill\n")

        ok, msg = check_product_skill(self.test_dir)
        self.assertTrue(ok)

    def test_check_container_engine(self):
        ok, msg = check_container_engine()
        # Should return a tuple of (bool, str) without throwing exceptions
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)

    def test_generate_product_skill(self):
        # Scaffold a multi-project monorepo with multiple profiles
        svc_a = os.path.join(self.test_dir, "services", "billing")
        os.makedirs(svc_a, exist_ok=True)
        with open(os.path.join(svc_a, "project.json"), "w") as f:
            f.write('{"name": "billing-svc", "tags": ["profile:A", "scope:backend"], "targets": {}}')

        app_b = os.path.join(self.test_dir, "apps", "portal")
        os.makedirs(app_b, exist_ok=True)
        with open(os.path.join(app_b, "project.json"), "w") as f:
            f.write('{"name": "portal-web", "tags": ["profile:B", "scope:frontend"], "targets": {}}')

        out_path = os.path.join(self.test_dir, "PRODUCT_SKILL.md")
        res = generate_product_skill(root_dir=self.test_dir, output_path=out_path)
        self.assertEqual(res, out_path)
        self.assertTrue(os.path.exists(out_path))

        with open(out_path, "r") as f:
            content = f.read()

        self.assertIn("billing-svc", content)
        self.assertIn("portal-web", content)
        self.assertIn("Profile A", content)
        self.assertIn("Profile B", content)
        self.assertIn("Single-Turn Ingestion Mandate", content)
        lines = content.splitlines()
        self.assertLess(len(lines), 150)

    def test_doctor_heal(self):
        # Initialize a minimal git repository in test_dir
        subprocess.run(["git", "init", "-b", "main"], cwd=self.test_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.test_dir, check=True)

        with open(os.path.join(self.test_dir, "README.md"), "w") as f:
            f.write("# Root\n")
        subprocess.run(["git", "add", "README.md"], cwd=self.test_dir, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.test_dir, check=True)

        # Pre-heal: doctor should report failures
        code_pre = run_doctor(root_dir=self.test_dir, heal=False)
        self.assertEqual(code_pre, 1)

        # Run with heal=True
        code_heal = run_doctor(root_dir=self.test_dir, heal=True)
        # Hooks, branches, codeowners, product_skill should be healed
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, ".github", "CODEOWNERS")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "PRODUCT_SKILL.md")))

        # Check git branches
        res = subprocess.run(["git", "branch"], cwd=self.test_dir, capture_output=True, text=True, check=True)
        self.assertIn("test", res.stdout)
        self.assertIn("stage", res.stdout)
        self.assertIn("prod", res.stdout)

    def test_cmd_ci_init(self):
        import argparse
        args = argparse.Namespace(platform="github", root=self.test_dir)
        ret = cmd_ci(args)
        self.assertEqual(ret, 0)
        ci_path = os.path.join(self.test_dir, ".github", "workflows", "ep-ci.yml")
        self.assertTrue(os.path.exists(ci_path))


if __name__ == "__main__":
    unittest.main()
