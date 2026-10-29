#!/usr/bin/env python3
"""
Unit tests for ep_tooling.py (Tooling Guidance Extensions).
Tests ep chaos, ep contract, ep sbom, and ep perf (locust / k6).
"""

import argparse
import json
import os
import shutil
import tempfile
import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ep_tooling import (
    cmd_chaos,
    cmd_contract,
    cmd_sbom,
    collect_monorepo_components,
    validate_openapi_dict,
    validate_protobuf_content,
)
from scripts.ep_ops import cmd_perf




class TestEpTooling(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_chaos_scaffold_and_verify(self):
        # 1. Scaffold
        args_scaffold = argparse.Namespace(
            action="scaffold",
            name="cache-drop",
            root=self.temp_dir,
            service="orders-service",
            file=None,
        )
        rc = cmd_chaos(args_scaffold)
        self.assertEqual(rc, 0)
        expected_file = os.path.join(self.temp_dir, "docs", "chaos", "cache-drop.md")
        self.assertTrue(os.path.isfile(expected_file))

        # 2. Verify
        args_verify = argparse.Namespace(
            action="verify",
            root=self.temp_dir,
            name=None,
            file=expected_file,
        )
        rc_ver = cmd_chaos(args_verify)
        self.assertEqual(rc_ver, 0)

        # 3. Dry-run
        args_run = argparse.Namespace(
            action="run",
            root=self.temp_dir,
            name=None,
            file=expected_file,
            dry_run=True,
        )
        rc_run = cmd_chaos(args_run)
        self.assertEqual(rc_run, 0)

    def test_chaos_verify_defective_plan(self):
        bad_file = os.path.join(self.temp_dir, "bad-chaos.md")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("# Chaos Without Sections\nJust some notes.\n")

        args = argparse.Namespace(action="verify", root=self.temp_dir, name=None, file=bad_file)
        rc = cmd_chaos(args)
        self.assertEqual(rc, 1)

    def test_openapi_validator_logic(self):
        valid_schema = {
            "openapi": "3.0.3",
            "info": {"title": "Users API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "OK"}},
                    },
                    "post": {
                        "requestBody": {"content": {"application/json": {}}},
                        "responses": {"201": {"description": "Created"}},
                    },
                }
            },
        }
        errors = validate_openapi_dict(valid_schema, "valid.json")
        self.assertEqual(len(errors), 0)

        invalid_schema = {
            "paths": {
                "/items": {
                    "post": {},
                }
            }
        }
        errors_bad = validate_openapi_dict(invalid_schema, "bad.json")
        self.assertTrue(any("openapi" in e for e in errors_bad))
        self.assertTrue(any("info" in e for e in errors_bad))
        self.assertTrue(any("responses" in e for e in errors_bad))

    def test_contract_cli_execution(self):
        schema_file = os.path.join(self.temp_dir, "openapi.json")
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump({
                "openapi": "3.0.0",
                "info": {"title": "Test", "version": "1.0"},
                "paths": {
                    "/ping": {
                        "get": {"responses": {"200": {}}}
                    }
                }
            }, f)

        args = argparse.Namespace(action="verify", root=self.temp_dir, dir=None, file=schema_file)
        rc = cmd_contract(args)
        self.assertEqual(rc, 0)

    def test_sbom_generate_and_verify(self):
        # Create a mock package.json
        pj_file = os.path.join(self.temp_dir, "package.json")
        with open(pj_file, "w", encoding="utf-8") as f:
            json.dump({
                "name": "mock-app",
                "version": "1.0.0",
                "dependencies": {
                    "express": "^4.18.2",
                    "zod": "~3.22.0",
                }
            }, f)

        # Generate CycloneDX
        out_cyclone = os.path.join(self.temp_dir, "sbom-cyclone.json")
        args_gen = argparse.Namespace(
            action="generate",
            root=self.temp_dir,
            output=out_cyclone,
            format="cyclonedx",
            file=None,
        )
        rc_gen = cmd_sbom(args_gen)
        self.assertEqual(rc_gen, 0)
        self.assertTrue(os.path.isfile(out_cyclone))

        with open(out_cyclone, "r", encoding="utf-8") as f:
            c_data = json.load(f)
        self.assertEqual(c_data["bomFormat"], "CycloneDX")
        self.assertEqual(len(c_data["components"]), 2)

        # Verify CycloneDX
        args_ver = argparse.Namespace(action="verify", root=self.temp_dir, file=out_cyclone, output=None, format=None)
        rc_ver = cmd_sbom(args_ver)
        self.assertEqual(rc_ver, 0)

        # Generate SPDX
        out_spdx = os.path.join(self.temp_dir, "sbom-spdx.json")
        args_spdx = argparse.Namespace(
            action="generate",
            root=self.temp_dir,
            output=out_spdx,
            format="spdx",
            file=None,
        )
        self.assertEqual(cmd_sbom(args_spdx), 0)
        with open(out_spdx, "r", encoding="utf-8") as f:
            spdx_data = json.load(f)
        self.assertEqual(spdx_data["spdxVersion"], "SPDX-2.3")

    def test_perf_locust_and_k6_dry_run(self):
        # Test Locust dry-run
        locust_script = os.path.join(self.temp_dir, "test.locust.py")
        with open(locust_script, "w", encoding="utf-8") as f:
            f.write("# locust test\n")
        args_locust = argparse.Namespace(
            tool="locust",
            script=locust_script,
            target_url="http://localhost:8080",
            vus=5,
            duration="5s",
            dry_run=True,
        )
        rc_locust = cmd_perf(args_locust)
        self.assertEqual(rc_locust, 0)

    def test_protobuf_contract_validation(self):
        valid_proto = """
syntax = "proto3";
package orders.v1;

message OrderRequest {
  string idempotency_key = 1;
  int64 amount = 2;
}

message OrderResponse {
  string order_id = 1;
}

service OrderService {
  rpc CreateOrder(OrderRequest) returns (OrderResponse);
}
"""
        errs = validate_protobuf_content(valid_proto, "order.proto")
        self.assertEqual(len(errs), 0)

        # Invalid proto: missing syntax, duplicate field numbers, and empty service
        invalid_proto = """
package billing.v1;

message BadMessage {
  string a = 1;
  string b = 1;
  string c = 19001;
}

service EmptyService {
}
"""
        errs_bad = validate_protobuf_content(invalid_proto, "bad.proto")
        self.assertTrue(any("syntax" in e for e in errs_bad))
        self.assertTrue(any("duplicate field number 1" in e for e in errs_bad))
        self.assertTrue(any("reserved Protobuf field number 19001" in e for e in errs_bad))
        self.assertTrue(any("without any RPC methods" in e for e in errs_bad))

    def test_contract_cli_with_proto_file(self):
        proto_file = os.path.join(self.temp_dir, "service.proto")
        with open(proto_file, "w", encoding="utf-8") as f:
            f.write("""
syntax = "proto3";
package users.v1;

message User {
  string id = 1;
  string email = 2;
}

service UserService {
  rpc GetUser(User) returns (User);
}
""")
        args = argparse.Namespace(action="verify", root=self.temp_dir, dir=None, file=proto_file, diff=None)
        rc = cmd_contract(args)
        self.assertEqual(rc, 0)

    def test_contract_cli_invalid_yaml_syntax_handled(self):
        bad_yaml = os.path.join(self.temp_dir, "broken-contract.yaml")
        with open(bad_yaml, "w", encoding="utf-8") as f:
            f.write("openapi: 3.0.0\n  bad indentation:\n [unclosed bracket\n")

        args = argparse.Namespace(action="verify", root=self.temp_dir, dir=None, file=bad_yaml, diff=None)
        rc = cmd_contract(args)
        self.assertEqual(rc, 1)

    def test_sbom_go_mod_and_pyproject_toml(self):
        # Create a go.mod
        go_dir = os.path.join(self.temp_dir, "services", "gateway")
        os.makedirs(go_dir, exist_ok=True)
        with open(os.path.join(go_dir, "go.mod"), "w", encoding="utf-8") as f:
            f.write("""
module github.com/enterprise/gateway

go 1.22

require (
    github.com/gin-gonic/gin v1.9.1
    google.golang.org/grpc v1.62.0
)
""")

        # Create a pyproject.toml
        py_dir = os.path.join(self.temp_dir, "services", "ml")
        os.makedirs(py_dir, exist_ok=True)
        with open(os.path.join(py_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("""
[project]
name = "ml-service"
dependencies = [
    "torch>=2.1.0",
    "numpy==1.26.0",
]
""")

        comps = collect_monorepo_components(self.temp_dir)
        names = {c["name"] for c in comps}
        self.assertIn("github.com/gin-gonic/gin", names)
        self.assertIn("google.golang.org/grpc", names)
        self.assertIn("torch", names)
        self.assertIn("numpy", names)


if __name__ == "__main__":
    unittest.main()

