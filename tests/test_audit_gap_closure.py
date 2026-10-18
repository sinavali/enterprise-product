#!/usr/bin/env python3
"""
tests/test_audit_gap_closure.py
Tests verifying gap closure across scaffolding, polyglot stack detection,
brownfield adoption manifest schema, human-only-prod override banning, and runbook heuristics.
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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Import verify-agent-manifests via importlib due to hyphen in filename
spec_vam = importlib.util.spec_from_file_location("verify_agent_manifests", str(REPO_ROOT / "scripts" / "verify-agent-manifests.py"))
vam = importlib.util.module_from_spec(spec_vam)
spec_vam.loader.exec_module(vam)
verify_agent_manifest = vam.verify_agent_manifest

# Import audit-runner via importlib due to hyphen in filename
spec_ar = importlib.util.spec_from_file_location("audit_runner", str(REPO_ROOT / "scripts" / "audit-runner.py"))
audit_runner = importlib.util.module_from_spec(spec_ar)
spec_ar.loader.exec_module(audit_runner)
run_audit = audit_runner.run_audit

from ep_adopt import scaffold_agent_manifest, scaffold_project_json
from ep_scaffold import cmd_init
from ep_stack import detect_stack


class TestScaffoldingAndStackContracts(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_node_ts_profile_a_scaffold_has_real_targets(self):
        target_dir = os.path.join(self.temp_dir, "services", "node-backend")
        args = argparse.Namespace(name="node-backend", profile="A", lang="ts", dir=target_dir)
        code = cmd_init(args)
        self.assertEqual(code, 0)

        proj_file = os.path.join(target_dir, "project.json")
        self.assertTrue(os.path.exists(proj_file))
        with open(proj_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        targets = data.get("targets", {})
        self.assertIn("lint", targets)
        self.assertIn("test", targets)
        self.assertIn("build", targets)
        self.assertIn("audit", targets)

        # Ensure no mock echo commands
        self.assertIn("eslint", targets["lint"]["options"]["command"])
        self.assertIn("vitest", targets["test"]["options"]["command"])
        self.assertIn("audit", targets["audit"]["options"]["command"])

    def test_python_profile_a_scaffold_has_real_targets(self):
        target_dir = os.path.join(self.temp_dir, "services", "py-backend")
        args = argparse.Namespace(name="py-backend", profile="A", lang="python", dir=target_dir)
        code = cmd_init(args)
        self.assertEqual(code, 0)

        proj_file = os.path.join(target_dir, "project.json")
        self.assertTrue(os.path.exists(proj_file))
        with open(proj_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        targets = data.get("targets", {})
        self.assertIn("ruff", targets["lint"]["options"]["command"])
        self.assertIn("pytest", targets["test"]["options"]["command"])
        self.assertIn("pip-audit", targets["audit"]["options"]["command"])

    def test_detect_stack_returns_audit_command(self):
        rust_dir = os.path.join(self.temp_dir, "rust_proj")
        os.makedirs(rust_dir, exist_ok=True)
        with open(os.path.join(rust_dir, "Cargo.toml"), "w") as fh:
            fh.write("[package]\nname = 'test'\n")

        stack = detect_stack(rust_dir)
        self.assertEqual(stack["lang"], "rust")
        self.assertIn("audit", stack)
        self.assertIn("cargo audit", stack["audit"])

        py_dir = os.path.join(self.temp_dir, "py_proj")
        os.makedirs(py_dir, exist_ok=True)
        with open(os.path.join(py_dir, "pyproject.toml"), "w") as fh:
            fh.write("[project]\nname = 'test'\n")

        stack_py = detect_stack(py_dir)
        self.assertEqual(stack_py["lang"], "python")
        self.assertIn("pip-audit", stack_py["audit"])


class TestBrownfieldAdoptionSchema(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scaffolded_agent_manifest_conforms_to_verifier(self):
        project_path = "services/billing-service"
        stack_info = {"lang": "go", "lint": "golangci-lint run ./...", "test": "go test ./...", "build": "go build", "audit": "govulncheck ./..."}
        content = scaffold_agent_manifest(project_path, stack_info, profile="A")

        manifest_file = os.path.join(self.temp_dir, "AGENT.md")
        with open(manifest_file, "w", encoding="utf-8") as fh:
            fh.write(content)

        valid, errors = verify_agent_manifest(manifest_file, root_dir=self.temp_dir, check_adrs=False)
        self.assertTrue(valid, f"Scaffolded manifest failed verification: {errors}")


class TestTier1HumanOnlyProdGate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_human_only_prod_override_is_blocked(self):
        content = """---
project_name: "rogue-service"
profile: "A"
stack: "node-ts-20"
scope: "backend"
owner: "rogue"
tier_overrides:
  - rule: "human-only-prod"
    adr_reference: "docs/adr/0099-bypass.md"
---

# Project Agent Manifest: rogue-service

## 1. Scope & Business Intent
Rogue bypass.

## 2. Architectural Profile
Profile A.

## 3. Local Nx Target
- `nx lint`
- `nx test`
- `nx build`
- `nx audit`

## 4. Test & Verification
Testing.
"""
        manifest_file = os.path.join(self.temp_dir, "AGENT.md")
        with open(manifest_file, "w", encoding="utf-8") as fh:
            fh.write(content)

        valid, errors = verify_agent_manifest(manifest_file, root_dir=self.temp_dir, check_adrs=False)
        self.assertFalse(valid)
        self.assertTrue(any("Illegal Tier 1 override attempted" in e for e in errors))


class TestOperationalRunbookAuditCheck(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_service_without_runbook_suggests_runbook(self):
        svc_dir = os.path.join(self.temp_dir, "services", "payment-service")
        os.makedirs(svc_dir, exist_ok=True)
        with open(os.path.join(svc_dir, "project.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": "payment-service"}, fh)

        findings, _ = run_audit(self.temp_dir)
        rule_ids = [f["id"] for f in findings]
        self.assertIn("RULE-9.5-OPERATIONAL-RUNBOOK", rule_ids)

    def test_service_with_runbook_passes(self):
        svc_dir = os.path.join(self.temp_dir, "services", "payment-service")
        os.makedirs(svc_dir, exist_ok=True)
        with open(os.path.join(svc_dir, "project.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": "payment-service"}, fh)
        with open(os.path.join(svc_dir, "RUNBOOK.md"), "w", encoding="utf-8") as fh:
            fh.write("# Runbook\n")

        findings, _ = run_audit(self.temp_dir)
        rule_ids = [f["id"] for f in findings if f["id"] == "RULE-9.5-OPERATIONAL-RUNBOOK"]
        self.assertEqual(len(rule_ids), 0)


if __name__ == "__main__":
    unittest.main()
