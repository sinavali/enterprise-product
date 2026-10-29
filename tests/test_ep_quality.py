#!/usr/bin/env python3
"""
Unit tests for ep_quality.py (Enterprise Production-Readiness Quality Gates).
Tests mutating route idempotency, graceful shutdown / drain, service runbook existence,
ephemeral integration test invariants, and architectural layer purity.
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

from scripts.ep_quality import (
    check_mutating_route_idempotency,
    check_graceful_shutdown,
    check_service_runbooks,
    check_ephemeral_integration_tests,
    check_layer_coverage,
    cmd_quality,
)



class TestEpQuality(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_idempotency_clean(self):
        ctrl_dir = os.path.join(self.temp_dir, "controllers")
        os.makedirs(ctrl_dir, exist_ok=True)
        safe_file = os.path.join(ctrl_dir, "order.controller.ts")
        with open(safe_file, "w", encoding="utf-8") as f:
            f.write("""
import { Controller, Post, Headers, UseInterceptors } from '@nestjs/common';
import { IdempotencyInterceptor } from './idempotency';

@Controller('orders')
@UseInterceptors(IdempotencyInterceptor)
export class OrderController {
    @Post()
    async createOrder(@Headers('Idempotency-Key') key: string) {
        return { success: true };
    }
}
""")
        findings = check_mutating_route_idempotency(self.temp_dir)
        self.assertEqual(len(findings), 0)

    def test_idempotency_violation(self):
        ctrl_dir = os.path.join(self.temp_dir, "controllers")
        os.makedirs(ctrl_dir, exist_ok=True)
        unsafe_file = os.path.join(ctrl_dir, "payment.controller.ts")
        with open(unsafe_file, "w", encoding="utf-8") as f:
            f.write("""
import { Controller, Post } from '@nestjs/common';

@Controller('payments')
export class PaymentController {
    @Post('/charge')
    async chargePayment() {
        return { status: 'charged' };
    }
}
""")
        findings = check_mutating_route_idempotency(self.temp_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "QUALITY-MUTATING-ROUTE-IDEMPOTENCY")
        self.assertIn("payment.controller.ts", findings[0]["file"])

    def test_idempotency_python_fastapi_clean_and_violation(self):
        api_dir = os.path.join(self.temp_dir, "api", "routes")
        os.makedirs(api_dir, exist_ok=True)

        safe_py = os.path.join(api_dir, "users.py")
        with open(safe_py, "w", encoding="utf-8") as f:
            f.write("""
from fastapi import APIRouter, Header

router = APIRouter()

@router.post("/users")
def create_user(idempotency_key: str = Header(...)):
    return {"id": 1}
""")
        self.assertEqual(len(check_mutating_route_idempotency(self.temp_dir)), 0)

        unsafe_py = os.path.join(api_dir, "tokens.py")
        with open(unsafe_py, "w", encoding="utf-8") as f:
            f.write("""
from fastapi import APIRouter

router = APIRouter()

@router.post("/tokens")
def issue_token():
    return {"token": "xyz"}
""")
        findings = check_mutating_route_idempotency(self.temp_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "QUALITY-MUTATING-ROUTE-IDEMPOTENCY")

    def test_graceful_shutdown_clean(self):
        entry_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(entry_dir, exist_ok=True)
        safe_entry = os.path.join(entry_dir, "server.ts")
        with open(safe_entry, "w", encoding="utf-8") as f:
            f.write("""
import express from 'express';
const app = express();
const server = app.listen(3000);

process.on('SIGTERM', () => {
    console.log('SIGTERM received; shutting down');
    server.close(() => process.exit(0));
});
""")
        findings = check_graceful_shutdown(self.temp_dir)
        self.assertEqual(len(findings), 0)

    def test_graceful_shutdown_violation(self):
        entry_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(entry_dir, exist_ok=True)
        unsafe_entry = os.path.join(entry_dir, "main.ts")
        with open(unsafe_entry, "w", encoding="utf-8") as f:
            f.write("""
import express from 'express';
const app = express();
app.listen(8080);
""")
        findings = check_graceful_shutdown(self.temp_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "QUALITY-GRACEFUL-SHUTDOWN-DRAIN")

    def test_service_runbook_clean_and_violation(self):
        svc_dir = os.path.join(self.temp_dir, "services", "billing")
        os.makedirs(svc_dir, exist_ok=True)
        with open(os.path.join(svc_dir, "project.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "billing", "tags": ["profile:a"]}, f)

        # Initially missing runbook
        findings = check_service_runbooks(self.temp_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "QUALITY-SERVICE-RUNBOOK-MISSING")

        # Create runbook in docs/runbooks/billing.md
        rb_dir = os.path.join(self.temp_dir, "docs", "runbooks")
        os.makedirs(rb_dir, exist_ok=True)
        with open(os.path.join(rb_dir, "billing.md"), "w", encoding="utf-8") as f:
            f.write("# Billing Service Runbook\n...")

        findings_after = check_service_runbooks(self.temp_dir)
        self.assertEqual(len(findings_after), 0)

    def test_ephemeral_integration_test_banned_fakes(self):
        test_dir = os.path.join(self.temp_dir, "tests", "integration")
        os.makedirs(test_dir, exist_ok=True)

        bad_test = os.path.join(test_dir, "database.test.ts")
        with open(bad_test, "w", encoding="utf-8") as f:
            f.write("""
import sqlite3 from 'sqlite3';
const db = sqlite3.connect(':memory:');
""")
        findings = check_ephemeral_integration_tests(self.temp_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "QUALITY-EPHEMERAL-TEST-FAKE-DB")

    def test_layer_coverage_purity_and_tests(self):
        # 1. Purity violation
        dom_dir = os.path.join(self.temp_dir, "services", "core", "domain")
        os.makedirs(dom_dir, exist_ok=True)
        entity_file = os.path.join(dom_dir, "user.ts")
        with open(entity_file, "w", encoding="utf-8") as f:
            f.write("import { PrismaClient } from 'prisma';\nexport class User {}\n")

        findings = check_layer_coverage(self.temp_dir)
        rules = [f["rule"] for f in findings]
        self.assertIn("QUALITY-DOMAIN-LAYER-PURITY", rules)

        # 2. Fix purity but missing test
        with open(entity_file, "w", encoding="utf-8") as f:
            f.write("export class User { id: string; name: string; }\n")

        findings2 = check_layer_coverage(self.temp_dir)
        rules2 = [f["rule"] for f in findings2]
        self.assertIn("QUALITY-DOMAIN-TEST-MISSING", rules2)

        # 3. Add unit test
        unit_dir = os.path.join(self.temp_dir, "services", "core", "tests", "unit")
        os.makedirs(unit_dir, exist_ok=True)
        with open(os.path.join(unit_dir, "user.spec.ts"), "w", encoding="utf-8") as f:
            f.write("describe('User', () => { it('works', () => {}); });\n")

        findings3 = check_layer_coverage(self.temp_dir)
        self.assertEqual(len(findings3), 0)

    def test_idempotency_multi_route_controller_detects_unannotated_route(self):
        ctrl_dir = os.path.join(self.temp_dir, "controllers")
        os.makedirs(ctrl_dir, exist_ok=True)
        mixed_file = os.path.join(ctrl_dir, "orders.controller.ts")
        with open(mixed_file, "w", encoding="utf-8") as f:
            f.write("""
import { Controller, Post } from '@nestjs/common';
import { Idempotent } from './idempotency';

@Controller('orders')
export class OrderController {
    @Post('/safe')
    @Idempotent()
    async createSafe() {
        return { ok: true };
    }

    @Post('/unsafe')
    async createUnsafe() {
        return { ok: false };
    }
}
""")
        findings = check_mutating_route_idempotency(self.temp_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "QUALITY-MUTATING-ROUTE-IDEMPOTENCY")
        self.assertIn("/unsafe", findings[0]["snippet"])

    def test_layer_coverage_python_orm_purity_violation(self):
        dom_dir = os.path.join(self.temp_dir, "services", "billing", "domain")
        os.makedirs(dom_dir, exist_ok=True)
        py_entity = os.path.join(dom_dir, "invoice.py")
        with open(py_entity, "w", encoding="utf-8") as f:
            f.write("from sqlalchemy import Column, Integer, String\n\nclass Invoice:\n    pass\n")

        findings = check_layer_coverage(self.temp_dir)
        rules = [f["rule"] for f in findings]
        self.assertIn("QUALITY-DOMAIN-LAYER-PURITY", rules)

    def test_layer_coverage_colocated_test_accepted(self):
        dom_dir = os.path.join(self.temp_dir, "services", "catalog", "domain")
        os.makedirs(dom_dir, exist_ok=True)
        entity_file = os.path.join(dom_dir, "product.ts")
        with open(entity_file, "w", encoding="utf-8") as f:
            f.write("export class Product { id: string; }\n")

        # Co-located test next to domain entity
        spec_file = os.path.join(dom_dir, "product.spec.ts")
        with open(spec_file, "w", encoding="utf-8") as f:
            f.write("describe('Product', () => { it('passes', () => {}); });\n")

        findings = check_layer_coverage(self.temp_dir)
        self.assertEqual(len(findings), 0)

    def test_graceful_shutdown_file_close_not_accepted(self):
        entry_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(entry_dir, exist_ok=True)
        py_server = os.path.join(entry_dir, "main.py")
        with open(py_server, "w", encoding="utf-8") as f:
            f.write("""
import uvicorn
f = open('log.txt', 'w')
f.write('starting')
f.close()
uvicorn.run('app:app', port=8000)
""")
        findings = check_graceful_shutdown(self.temp_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "QUALITY-GRACEFUL-SHUTDOWN-DRAIN")

    def test_ephemeral_integration_efcore_in_memory(self):
        test_dir = os.path.join(self.temp_dir, "tests", "integration")
        os.makedirs(test_dir, exist_ok=True)
        test_cs = os.path.join(test_dir, "DatabaseTests.cs")
        with open(test_cs, "w", encoding="utf-8") as f:
            f.write("""
var options = new DbContextOptionsBuilder<AppDbContext>()
    .UseInMemoryDatabase("TestDb")
    .Options;
""")
        findings = check_ephemeral_integration_tests(self.temp_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "QUALITY-EPHEMERAL-TEST-FAKE-DB")

    def test_cmd_quality_cli(self):
        args = argparse.Namespace(root=self.temp_dir, diff=None, surface=False, json=True)
        rc = cmd_quality(args)
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

