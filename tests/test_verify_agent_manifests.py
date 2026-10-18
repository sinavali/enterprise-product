#!/usr/bin/env python3
"""
Unit and integration tests for verify-agent-manifests CLI tool and inheritance model.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "scripts" / "bin"


class TestVerifyAgentManifests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_agent_manifest(self):
        proj_dir = os.path.join(self.temp_dir, "services", "billing")
        os.makedirs(proj_dir, exist_ok=True)
        agent_file = os.path.join(proj_dir, "AGENT.md")

        content = """---
project_name: "billing-service"
profile: "A"
stack: "node-20"
scope: "backend"
owner: "billing-team"
tier_overrides: []
---

# Billing Service Manifest

## 1. Scope & Business Intent
Handles billing and subscriptions.

## 2. Architectural Profile & Boundaries
Profile A (DDD/Hexagonal).

## 3. Local Nx Target Delegations
Local targets.

## 4. Test & Verification Rules
Test rules.
"""
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "verify-agent-manifests"), "--root", self.temp_dir],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout}")
        self.assertIn("[PASS]", proc.stdout)

    def test_root_agent_manifest_passes_without_subproject_properties(self):
        root_agent = os.path.join(self.temp_dir, "AGENT.md")
        content = """---
governance: "enterprise-product"
organization: "enterprise"
---

# Root Enterprise Governance Manifest

## Directives
P1 through P10.
"""
        with open(root_agent, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "verify-agent-manifests"), "--root", self.temp_dir],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[PASS]", proc.stdout)

    def test_illegal_tier_1_override_fails(self):
        proj_dir = os.path.join(self.temp_dir, "services", "illegal")
        os.makedirs(proj_dir, exist_ok=True)
        agent_file = os.path.join(proj_dir, "AGENT.md")

        content = """---
project_name: "illegal-service"
profile: "A"
stack: "node-20"
scope: "backend"
owner: "rogue-team"
tier_overrides:
  - rule: "pure_domain"
    adr_reference: "docs/adr/0001.md"
    justification: "We want ORM in domain"
---

# Illegal Manifest
## 1. Scope & Business Intent
Scope.
## 2. Architectural Profile
Profile.
## 3. Local Nx Target
Target.
## 4. Test & Verification
Tests.
"""
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "verify-agent-manifests"), "--root", self.temp_dir, "--no-check-adrs"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Illegal Tier 1 override", proc.stdout)

    def test_anti_mvp_tier_1_override_fails(self):
        proj_dir = os.path.join(self.temp_dir, "services", "mvp-service")
        os.makedirs(proj_dir, exist_ok=True)
        agent_file = os.path.join(proj_dir, "AGENT.md")

        content = """---
project_name: "mvp-service"
profile: "A"
stack: "node-20"
scope: "backend"
owner: "mvp-team"
tier_overrides:
  - rule: "anti-mvp"
    adr_reference: "docs/adr/0002.md"
    justification: "We want to ship an MVP prototype first"
---

# MVP Service Manifest
## 1. Scope & Business Intent
Scope.
## 2. Architectural Profile
Profile.
## 3. Local Nx Target
Target.
## 4. Test & Verification
Tests.
"""
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "verify-agent-manifests"), "--root", self.temp_dir, "--no-check-adrs"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Illegal Tier 1 override attempted for rule 'anti-mvp'", proc.stdout)

    def test_file_relative_and_symlinked_adr_resolution(self):
        proj_dir = os.path.join(self.temp_dir, "services", "override-service")
        adr_dir = os.path.join(self.temp_dir, "docs", "adr")
        os.makedirs(proj_dir, exist_ok=True)
        os.makedirs(adr_dir, exist_ok=True)

        real_adr = os.path.join(adr_dir, "0042.md")
        with open(real_adr, "w", encoding="utf-8") as f:
            f.write("# ADR 42: Coverage Adjustment\n")

        agent_file = os.path.join(proj_dir, "AGENT.md")
        content = """---
project_name: "override-service"
profile: "B"
stack: "nextjs-14"
scope: "frontend"
tier_overrides:
  - rule: "coverage-threshold"
    adr_reference: "../../docs/adr/0042.md"
---

# Override Service
## 1. Scope & Business Intent
Scope.
## 2. Architectural Profile
Profile.
## 3. Local Nx Target
Target.
## 4. Test & Verification
Tests.
"""
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "verify-agent-manifests"), "--root", self.temp_dir],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[PASS]", proc.stdout)

    def test_scoped_root_still_enforces_subproject_properties(self):
        # Even if --root points directly to a subproject dir, subproject rules apply
        sub_dir = os.path.join(self.temp_dir, "services", "scoped-service")
        os.makedirs(sub_dir, exist_ok=True)
        bad_agent = os.path.join(sub_dir, "AGENT.md")
        with open(bad_agent, "w", encoding="utf-8") as f:
            f.write("# Incomplete subproject manifest without required frontmatter\n")

        proc = subprocess.run(
            [str(BIN_DIR / "verify-agent-manifests"), "--root", sub_dir],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Missing required YAML frontmatter", proc.stdout)


    def test_nonexistent_root_fails(self):
        nonexistent = os.path.join(self.temp_dir, "does_not_exist")
        proc = subprocess.run(
            [str(BIN_DIR / "verify-agent-manifests"), "--root", nonexistent],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("does not exist", proc.stderr)

    def test_leading_slash_adr_reference_resolves(self):
        adr_dir = os.path.join(self.temp_dir, "docs", "adr")
        os.makedirs(adr_dir, exist_ok=True)
        adr_file = os.path.join(adr_dir, "0099.md")
        with open(adr_file, "w", encoding="utf-8") as f:
            f.write("# ADR 99\n")

        sub_dir = os.path.join(self.temp_dir, "services", "slash-adr")
        os.makedirs(sub_dir, exist_ok=True)
        agent_file = os.path.join(sub_dir, "AGENT.md")
        content = """---
project_name: "slash-adr"
profile: "A"
stack: "node"
scope: "backend"
tier_overrides:
  - rule: "coverage-threshold"
    adr_reference: "/docs/adr/0099.md"
---

# Service
## 1. Scope & Business Intent
Scope.
## 2. Architectural Profile
Profile.
## 3. Local Nx Target
Target.
## 4. Test & Verification
Tests.
"""
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write(content)

        proc = subprocess.run(
            [str(BIN_DIR / "verify-agent-manifests"), "--root", self.temp_dir],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0: {proc.stdout} {proc.stderr}")
        self.assertIn("[PASS]", proc.stdout)


    def test_additional_tier_1_overrides_fail(self):
        for banned_rule in ["max-dir-depth", "expand-contract", "mandatory-change-surface", "nc-block"]:
            sub_dir = os.path.join(self.temp_dir, "services", f"test-{banned_rule}")
            os.makedirs(sub_dir, exist_ok=True)
            agent_file = os.path.join(sub_dir, "AGENT.md")
            content = f"""---
project_name: "test-{banned_rule}"
profile: "A"
stack: "node"
scope: "backend"
tier_overrides:
  - rule: "{banned_rule}"
    adr_reference: "docs/adr/0001.md"
---

# Service
## 1. Scope & Business Intent
Scope.
## 2. Architectural Profile
Profile.
## 3. Local Nx Target
Target.
## 4. Test & Verification
Tests.
"""
            with open(agent_file, "w", encoding="utf-8") as f:
                f.write(content)

            proc = subprocess.run(
                [str(BIN_DIR / "verify-agent-manifests"), "--root", sub_dir],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(f"Illegal Tier 1 override attempted for rule '{banned_rule}'", proc.stdout)


if __name__ == "__main__":
    unittest.main()
