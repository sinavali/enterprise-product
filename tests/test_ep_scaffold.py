#!/usr/bin/env python3
"""
Unit and integration tests for ep_scaffold.py and project contract generation.
"""

import argparse
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from scripts.ep_scaffold import cmd_init
except ImportError:
    from ep_scaffold import cmd_init  # type: ignore[import-not-found,no-redef]


class TestEpScaffold(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scaffold_profile_a_go(self):
        target = os.path.join(self.temp_dir, "services", "payment")
        args = argparse.Namespace(name="payment", profile="A", lang="go", dir=target)
        rc = cmd_init(args)
        self.assertEqual(rc, 0)

        pj_path = os.path.join(target, "project.json")
        self.assertTrue(os.path.isfile(pj_path))
        with open(pj_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["name"], "payment")
        self.assertEqual(data["projectType"], "application")
        self.assertEqual(data["sourceRoot"], f"{target}/src")
        self.assertIn("profile:a", data["tags"])
        self.assertIn("scope:backend", data["tags"])
        self.assertIn("lang:go", data["tags"])
        self.assertIn("golangci-lint", data["targets"]["lint"]["options"]["command"])
        self.assertIn("go test", data["targets"]["test"]["options"]["command"])
        self.assertIn("go build", data["targets"]["build"]["options"]["command"])

    def test_scaffold_profile_b_nextjs(self):
        target = os.path.join(self.temp_dir, "apps", "web")
        args = argparse.Namespace(name="web", profile="B", lang="ts", dir=target)
        rc = cmd_init(args)
        self.assertEqual(rc, 0)

        pj_path = os.path.join(target, "project.json")
        self.assertTrue(os.path.isfile(pj_path))
        with open(pj_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["name"], "web")
        self.assertEqual(data["projectType"], "application")
        self.assertEqual(data["sourceRoot"], f"{target}/src")
        self.assertIn("profile:b", data["tags"])
        self.assertIn("scope:frontend", data["tags"])
        self.assertEqual(data["targets"]["build"]["options"]["command"], "pnpm next build")

    def test_scaffold_profile_c_flutter(self):
        target = os.path.join(self.temp_dir, "apps", "mobile")
        args = argparse.Namespace(name="mobile", profile="C", lang="dart", dir=target)
        rc = cmd_init(args)
        self.assertEqual(rc, 0)

        pj_path = os.path.join(target, "project.json")
        self.assertTrue(os.path.isfile(pj_path))
        with open(pj_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["name"], "mobile")
        self.assertEqual(data["projectType"], "application")
        # Profile C must have sourceRoot: <dir>/lib
        self.assertEqual(data["sourceRoot"], f"{target}/lib")
        self.assertIn("profile:c", data["tags"])
        self.assertIn("scope:mobile", data["tags"])
        self.assertIn("lang:dart", data["tags"])

        # Check directory layout
        self.assertTrue(os.path.isdir(os.path.join(target, "lib", "core")))
        self.assertTrue(os.path.isdir(os.path.join(target, "lib", "features", "sample", "domain")))
        self.assertTrue(os.path.isdir(os.path.join(target, "test", "unit")))

    def test_scaffold_profile_d_contracts(self):
        target = os.path.join(self.temp_dir, "libs", "contracts")
        args = argparse.Namespace(name="contracts", profile="D", lang="ts", dir=target)
        rc = cmd_init(args)
        self.assertEqual(rc, 0)

        pj_path = os.path.join(target, "project.json")
        self.assertTrue(os.path.isfile(pj_path))
        with open(pj_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["name"], "contracts")
        self.assertEqual(data["projectType"], "library")
        self.assertIn("profile:d", data["tags"])
        self.assertIn("scope:shared", data["tags"])
        self.assertIn("generate-ts", data["targets"])

    def test_scaffold_profile_a_rust(self):
        target = os.path.join(self.temp_dir, "services", "engine")
        args = argparse.Namespace(name="engine", profile="A", lang="rust", dir=target)
        rc = cmd_init(args)
        self.assertEqual(rc, 0)

        pj_path = os.path.join(target, "project.json")
        with open(pj_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("lang:rust", data["tags"])
        self.assertIn("cargo test", data["targets"]["test"]["options"]["command"])

    def test_scaffold_profile_a_python(self):
        target = os.path.join(self.temp_dir, "services", "ai")
        args = argparse.Namespace(name="ai", profile="A", lang="python", dir=target)
        rc = cmd_init(args)
        self.assertEqual(rc, 0)

        pj_path = os.path.join(target, "project.json")
        with open(pj_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("lang:python", data["tags"])
        self.assertIn("pytest", data["targets"]["test"]["options"]["command"])

    def test_scaffold_existing_directory_fails(self):
        target = os.path.join(self.temp_dir, "services", "existing")
        os.makedirs(target, exist_ok=True)
        args = argparse.Namespace(name="existing", profile="A", lang="go", dir=target)
        rc = cmd_init(args)
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
