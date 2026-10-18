#!/usr/bin/env python3
"""
tests/test_enterprise_catalog_enforcement.py
Comprehensive automated test suite verifying mechanical enforcement of the
Canonical Enterprise Engineering Catalog in EP-OS.
Tests new audit heuristics, AST rules, IaC gates, SLO validator, CODEOWNERS auditor,
DORA metrics calculator, and k6 performance dry-run.
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
EP_SCRIPT = REPO_ROOT / "scripts" / "ep.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Import audit-runner via importlib due to hyphen in filename
spec_ar = importlib.util.spec_from_file_location("audit_runner", str(REPO_ROOT / "scripts" / "audit-runner.py"))
audit_runner = importlib.util.module_from_spec(spec_ar)
spec_ar.loader.exec_module(audit_runner)
scan_file_for_violations = audit_runner.scan_file_for_violations

# Import verify-agent-manifests via importlib due to hyphen in filename
spec_vam = importlib.util.spec_from_file_location("verify_agent_manifests", str(REPO_ROOT / "scripts" / "verify-agent-manifests.py"))
vam = importlib.util.module_from_spec(spec_vam)
spec_vam.loader.exec_module(vam)
parse_agent_yaml = vam.parse_agent_yaml
verify_agent_manifest = vam.verify_agent_manifest

from ep_ast import scan_structural_rules
from ep_ops import cmd_codeowners, cmd_dora, cmd_perf, cmd_slo, parse_slo_yaml, validate_slo_dict
from ep_security import cmd_iac, scan_iac_files


class TestEnterpriseCatalogAuditRules(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rule_1_5_mutable_global_state_in_handler(self):
        handler_dir = os.path.join(self.temp_dir, "handlers")
        os.makedirs(handler_dir, exist_ok=True)
        handler_file = os.path.join(handler_dir, "user_handler.ts")
        with open(handler_file, "w", encoding="utf-8") as f:
            f.write("let sessions = {};\nexport function handleUser() {}\n")

        findings = scan_file_for_violations(handler_file)
        rule_ids = [f["id"] for f in findings]
        self.assertIn("RULE-1.5-MUTABLE-GLOBAL-STATE", rule_ids)

    def test_rule_3_7_unbounded_queue_prefetch(self):
        consumer_dir = os.path.join(self.temp_dir, "consumers")
        os.makedirs(consumer_dir, exist_ok=True)
        consumer_file = os.path.join(consumer_dir, "event_consumer.ts")
        with open(consumer_file, "w", encoding="utf-8") as f:
            f.write("channel.consume(queue, handler, { prefetch: 0, noAck: true });\n")

        findings = scan_file_for_violations(consumer_file)
        rule_ids = [f["id"] for f in findings]
        self.assertIn("RULE-3.7-UNBOUNDED-QUEUE-PREFETCH", rule_ids)

    def test_rule_6_7_trace_propagation(self):
        adapter_dir = os.path.join(self.temp_dir, "clients")
        os.makedirs(adapter_dir, exist_ok=True)
        client_file = os.path.join(adapter_dir, "payment_client.ts")
        with open(client_file, "w", encoding="utf-8") as f:
            f.write("export async function callGateway() {\n  return axios.get(url);\n}\n")

        findings = scan_file_for_violations(client_file)
        rule_ids = [f["id"] for f in findings]
        self.assertIn("RULE-6.7-TRACE-PROPAGATION", rule_ids)

    def test_rule_8_6_naked_env_in_domain(self):
        domain_dir = os.path.join(self.temp_dir, "services", "billing", "domain")
        os.makedirs(domain_dir, exist_ok=True)
        domain_file = os.path.join(domain_dir, "order_aggregate.ts")
        with open(domain_file, "w", encoding="utf-8") as f:
            f.write("export class Order {\n  taxRate = process.env.TAX_RATE;\n}\n")

        findings = scan_file_for_violations(domain_file)
        rule_ids = [f["id"] for f in findings]
        self.assertIn("RULE-8.6-NAKED-ENV-IN-DOMAIN", rule_ids)
        # Severity must be blocking
        blocking_rules = [f["id"] for f in findings if f["severity"] == "blocking"]
        self.assertIn("RULE-8.6-NAKED-ENV-IN-DOMAIN", blocking_rules)


class TestIacSecurityGate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dockerfile_root_user_blocked(self):
        df = os.path.join(self.temp_dir, "Dockerfile")
        with open(df, "w", encoding="utf-8") as f:
            f.write("FROM alpine:3.19\nRUN apk add curl\nUSER root\nENTRYPOINT [\"sh\"]\n")

        findings = scan_iac_files(self.temp_dir)
        rule_ids = [f["rule"] for f in findings]
        self.assertIn("IAC-DOCKER-ROOT-USER", rule_ids)

    def test_dockerfile_missing_user_directive_blocked(self):
        df = os.path.join(self.temp_dir, "Dockerfile")
        with open(df, "w", encoding="utf-8") as f:
            f.write("FROM alpine:3.19\nRUN apk add curl\nCMD [\"curl\"]\n")

        findings = scan_iac_files(self.temp_dir)
        rule_ids = [f["rule"] for f in findings]
        self.assertIn("IAC-DOCKER-NO-USER-DIRECTIVE", rule_ids)

    def test_dockerfile_clean_non_root_passes(self):
        df = os.path.join(self.temp_dir, "Dockerfile")
        with open(df, "w", encoding="utf-8") as f:
            f.write("FROM alpine:3.19@sha256:c5b1261d6d3e43071626931fc004f70149baeba2c8ec672bd49f277b3b51a03e\n"
                    "RUN adduser -D appuser\n"
                    "USER appuser\n"
                    "CMD [\"echo\", \"safe\"]\n")

        findings = scan_iac_files(self.temp_dir)
        blocking_findings = [f for f in findings if f["severity"] == "blocking"]
        self.assertEqual(len(blocking_findings), 0)

    def test_k8s_privileged_container_blocked(self):
        k8s_dir = os.path.join(self.temp_dir, "k8s")
        os.makedirs(k8s_dir, exist_ok=True)
        manifest = os.path.join(k8s_dir, "deployment.yaml")
        with open(manifest, "w", encoding="utf-8") as f:
            f.write("apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n"
                    "      - name: app\n        securityContext:\n          privileged: true\n")

        findings = scan_iac_files(self.temp_dir)
        rule_ids = [f["rule"] for f in findings]
        self.assertIn("IAC-K8S-PRIVILEGED-CONTAINER", rule_ids)


class TestSloValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_slo_passes(self):
        slo_path = os.path.join(self.temp_dir, "service.slo.yaml")
        with open(slo_path, "w", encoding="utf-8") as f:
            f.write("""service: "order-service"
tier: "tier-1"
owner_team: "order-squad"
slos:
  - id: "availability"
    name: "Success Rate"
    target: 0.999
    window: "30d"
    sli:
      metric_type: "ratio"
""")
        with open(slo_path, "r", encoding="utf-8") as f:
            data = parse_slo_yaml(f.read())
        errors = validate_slo_dict(data, slo_path)
        self.assertEqual(len(errors), 0, f"Errors: {errors}")

    def test_invalid_slo_tier_and_target_fails(self):
        slo_path = os.path.join(self.temp_dir, "bad.slo.yaml")
        with open(slo_path, "w", encoding="utf-8") as f:
            f.write("""service: "bad-service"
tier: "tier-99"
slos:
  - id: "latency"
    target: 1.5
    sli:
      metric_type: "histogram"
""")
        with open(slo_path, "r", encoding="utf-8") as f:
            data = parse_slo_yaml(f.read())
        errors = validate_slo_dict(data, slo_path)
        self.assertTrue(any("Invalid tier" in e for e in errors))
        self.assertTrue(any("must be a float between 0.0 and 1.0" in e for e in errors))


class TestCodeownersAndDora(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_codeowners_audit_unassigned_fails(self):
        service_dir = os.path.join(self.temp_dir, "services", "unowned-svc")
        os.makedirs(service_dir, exist_ok=True)
        # No AGENT.md, no CODEOWNERS
        args = argparse.Namespace(root=self.temp_dir)
        code = cmd_codeowners(args)
        self.assertEqual(code, 1)

    def test_codeowners_audit_assigned_via_manifest_passes(self):
        service_dir = os.path.join(self.temp_dir, "services", "owned-svc")
        os.makedirs(service_dir, exist_ok=True)
        with open(os.path.join(service_dir, "AGENT.md"), "w", encoding="utf-8") as f:
            f.write("---\nowner: '@core-team'\n---\n")

        args = argparse.Namespace(root=self.temp_dir)
        code = cmd_codeowners(args)
        self.assertEqual(code, 0)

    def test_dora_runs_cleanly(self):
        args = argparse.Namespace(days=30)
        code = cmd_dora(args)
        self.assertEqual(code, 0)

    def test_perf_dry_run_passes(self):
        script_path = os.path.join(str(REPO_ROOT), "templates", "perf-test.k6.js")
        args = argparse.Namespace(script=script_path, target_url="http://localhost:8080", vus=5, duration="5s", dry_run=True)
        code = cmd_perf(args)
        self.assertEqual(code, 0)


class TestAgentManifestResilienceFields(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_manifest_with_dr_slo_resources_parses_cleanly(self):
        content = """---
project_name: "payment-service"
profile: "A"
stack: "node-ts-20"
scope: "backend"
owner: "finance-team"
dr:
  rto: "30m"
  rpo: "5m"
slo:
  tier: "tier-1"
  availability_target: "0.999"
resources:
  cpu_limit: "2000m"
  memory_limit: "2Gi"
tier_overrides: []
---

# Project Agent Manifest: payment-service

## 1. Scope & Business Intent
Handles card captures.

## 2. Architectural Profile & Boundaries
- **Profile**: A
- **Primary Inputs**: Inbound webhook
- **Allowed Outbound Dependencies**: `libs/core`
- **Forbidden Dependencies**: None

## 3. Local Nx Target Delegations
- `nx lint payment-service` -> `eslint`
- `nx test payment-service` -> `vitest`
- `nx build payment-service` -> `tsc`
- `nx audit payment-service` -> `audit`

## 4. Test & Verification Rules
Real containers only.
"""
        manifest_file = os.path.join(self.temp_dir, "AGENT.md")
        with open(manifest_file, "w", encoding="utf-8") as f:
            f.write(content)

        data, body = parse_agent_yaml(content)
        self.assertIn("dr", data)
        self.assertEqual(data["dr"].get("rto"), "30m")
        self.assertEqual(data["dr"].get("rpo"), "5m")
        self.assertIn("slo", data)
        self.assertEqual(data["slo"].get("tier"), "tier-1")
        self.assertIn("resources", data)
        self.assertEqual(data["resources"].get("memory_limit"), "2Gi")

        valid, errors = verify_agent_manifest(manifest_file, root_dir=self.temp_dir, check_adrs=False)
        self.assertTrue(valid, f"Verification failed with errors: {errors}")


if __name__ == "__main__":
    unittest.main()
