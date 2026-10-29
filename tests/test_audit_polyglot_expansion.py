#!/usr/bin/env python3
"""
tests/test_audit_polyglot_expansion.py
Comprehensive unit tests for polyglot heuristic expansions across Dimensions 1, 3, 5, 6, 7, 8, and 10,
including edge cases: Go slices, C# parameterless catch, multi-level cross-project imports, and AST UTC clock.
"""

import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Dynamic import of audit-runner.py
spec_ar = importlib.util.spec_from_file_location("audit_runner", str(REPO_ROOT / "scripts" / "audit-runner.py"))
assert spec_ar and spec_ar.loader
audit_runner = importlib.util.module_from_spec(spec_ar)
spec_ar.loader.exec_module(audit_runner)
scan_file_for_violations = audit_runner.scan_file_for_violations

# Dynamic import of ep_ast.py
spec_ast = importlib.util.spec_from_file_location("ep_ast", str(REPO_ROOT / "scripts" / "ep_ast.py"))
assert spec_ast and spec_ast.loader
ep_ast = importlib.util.module_from_spec(spec_ast)
spec_ast.loader.exec_module(ep_ast)


class TestAuditPolyglotExpansion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # 1. Dimension 1: Go & Rust Mutable Global State (RULE-1.5)
    # --------------------------------------------------------------------------
    def test_go_mutable_global_state_detected(self):
        handler_dir = os.path.join(self.temp_dir, "handlers")
        os.makedirs(handler_dir, exist_ok=True)
        bad_go_map = os.path.join(handler_dir, "auth_handler.go")
        with open(bad_go_map, "w", encoding="utf-8") as f:
            f.write("package handlers\n\nvar sessionCache = make(map[string]string)\n")

        bad_go_literal = os.path.join(handler_dir, "tokens_handler.go")
        with open(bad_go_literal, "w", encoding="utf-8") as f:
            f.write("package handlers\n\nvar activeTokens = map[string]int{}\n")

        bad_go_slice_make = os.path.join(handler_dir, "slice_make_handler.go")
        with open(bad_go_slice_make, "w", encoding="utf-8") as f:
            f.write("package handlers\n\nvar activeSessions = make([]string, 0)\n")

        bad_go_slice_lit = os.path.join(handler_dir, "slice_lit_handler.go")
        with open(bad_go_slice_lit, "w", encoding="utf-8") as f:
            f.write("package handlers\n\nvar sessionIds = []string{}\n")

        clean_go = os.path.join(handler_dir, "clean_handler.go")
        with open(clean_go, "w", encoding="utf-8") as f:
            f.write("package handlers\n\nfunc HandleRequest() {\n    localMap := make(map[string]string)\n    localSlice := []string{}\n}\n")

        for bad_f in [bad_go_map, bad_go_literal, bad_go_slice_make, bad_go_slice_lit]:
            findings = scan_file_for_violations(bad_f)
            self.assertTrue(
                any(f["id"] == "RULE-1.5-MUTABLE-GLOBAL-STATE" for f in findings),
                f"Expected RULE-1.5 in {bad_f}",
            )

        f_clean = scan_file_for_violations(clean_go)
        self.assertFalse(any(f["id"] == "RULE-1.5-MUTABLE-GLOBAL-STATE" for f in f_clean))

    def test_rust_mutable_global_state_detected(self):
        ctrl_dir = os.path.join(self.temp_dir, "controllers")
        os.makedirs(ctrl_dir, exist_ok=True)
        bad_rs = os.path.join(ctrl_dir, "state_controller.rs")
        with open(bad_rs, "w", encoding="utf-8") as f:
            f.write("pub struct Handler;\nstatic mut GLOBAL_STATE: i32 = 0;\n")

        clean_rs = os.path.join(ctrl_dir, "clean_controller.rs")
        with open(clean_rs, "w", encoding="utf-8") as f:
            f.write("pub struct Handler;\nconst MAX_LIMIT: i32 = 100;\n")

        f_bad = scan_file_for_violations(bad_rs)
        self.assertTrue(any(f["id"] == "RULE-1.5-MUTABLE-GLOBAL-STATE" for f in f_bad))

        f_clean = scan_file_for_violations(clean_rs)
        self.assertFalse(any(f["id"] == "RULE-1.5-MUTABLE-GLOBAL-STATE" for f in f_clean))

    # --------------------------------------------------------------------------
    # 2. Dimension 3: Rust, PHP, Java Unbounded Queue Prefetch (RULE-3.7)
    # --------------------------------------------------------------------------
    def test_rust_and_php_and_java_queue_prefetch(self):
        cons_dir = os.path.join(self.temp_dir, "consumers")
        os.makedirs(cons_dir, exist_ok=True)

        bad_rs_lapin = os.path.join(cons_dir, "rabbit_consumer.rs")
        with open(bad_rs_lapin, "w", encoding="utf-8") as f:
            f.write("pub async fn consume(ch: &Channel) {\n    ch.basic_qos(0, BasicQosOptions::default()).await;\n}\n")

        bad_rs_rdkafka = os.path.join(cons_dir, "kafka_consumer.rs")
        with open(bad_rs_rdkafka, "w", encoding="utf-8") as f:
            f.write("let mut cfg = ClientConfig::new();\ncfg.set(\"queued.min.messages\", \"0\");\n")

        bad_php = os.path.join(cons_dir, "OrderWorker.php")
        with open(bad_php, "w", encoding="utf-8") as f:
            f.write("<?php\nclass OrderWorker {\n    public function run($ch) {\n        $ch->basic_qos(0, 0, false);\n    }\n}\n")

        bad_java_qos = os.path.join(cons_dir, "RabbitQueue.java")
        with open(bad_java_qos, "w", encoding="utf-8") as f:
            f.write("public class RabbitQueue {\n    public void setup(Channel ch) throws Exception {\n        ch.basicQos(0);\n    }\n}\n")

        bad_java_ack = os.path.join(cons_dir, "Listener.java")
        with open(bad_java_ack, "w", encoding="utf-8") as f:
            f.write("public class Listener {\n    public void start(Channel ch) throws Exception {\n        boolean autoAck = true;\n    }\n}\n")

        bad_ts_autoack = os.path.join(cons_dir, "listener.ts")
        with open(bad_ts_autoack, "w", encoding="utf-8") as f:
            f.write("channel.consume('orders', handleOrder, { autoAck: true });\n")

        clean_consumer = os.path.join(cons_dir, "CleanConsumer.java")
        with open(clean_consumer, "w", encoding="utf-8") as f:
            f.write("public class CleanConsumer {\n    public void setup(Channel ch) throws Exception {\n        ch.basicQos(50);\n        boolean autoAck = false;\n    }\n}\n")

        clean_rs_kafka = os.path.join(cons_dir, "clean_kafka.rs")
        with open(clean_rs_kafka, "w", encoding="utf-8") as f:
            f.write("let mut cfg = ClientConfig::new();\ncfg.set(\"queued.min.messages\", \"5000\");\n")

        clean_php = os.path.join(cons_dir, "CleanWorker.php")
        with open(clean_php, "w", encoding="utf-8") as f:
            f.write("<?php\nclass CleanWorker {\n    public function run($ch) {\n        $ch->basic_qos(0, 50, false);\n    }\n}\n")

        for bad_f in [bad_rs_lapin, bad_rs_rdkafka, bad_php, bad_java_qos, bad_java_ack, bad_ts_autoack]:
            findings = scan_file_for_violations(bad_f)
            self.assertTrue(
                any(f["id"] == "RULE-3.7-UNBOUNDED-QUEUE-PREFETCH" for f in findings),
                f"Expected RULE-3.7 violation in {bad_f}",
            )

        for clean_f in [clean_consumer, clean_rs_kafka, clean_php]:
            f_clean = scan_file_for_violations(clean_f)
            self.assertFalse(
                any(f["id"] == "RULE-3.7-UNBOUNDED-QUEUE-PREFETCH" for f in f_clean),
                f"Unexpected RULE-3.7 violation in {clean_f}",
            )

    # --------------------------------------------------------------------------
    # 3. Dimension 5: Rust & Java Raw SQL Concatenation (RULE-5.2)
    # --------------------------------------------------------------------------
    def test_rust_and_java_raw_sql_concatenation(self):
        services_dir = os.path.join(self.temp_dir, "services", "billing")
        os.makedirs(services_dir, exist_ok=True)

        bad_rs_sqlx = os.path.join(services_dir, "invoice_repo.rs")
        with open(bad_rs_sqlx, "w", encoding="utf-8") as f:
            f.write("pub async fn fetch(db: &Pool, id: &str) {\n    let q = sqlx::query(&format!(\"SELECT * FROM invoices WHERE id = '{}'\", id));\n}\n")

        bad_rs_sqlx_as = os.path.join(services_dir, "user_repo.rs")
        with open(bad_rs_sqlx_as, "w", encoding="utf-8") as f:
            f.write("pub async fn fetch_as(db: &Pool, id: &str) {\n    let q = sqlx::query_as(&format!(\"SELECT * FROM users WHERE id = '{}'\", id));\n}\n")

        bad_rs_format = os.path.join(services_dir, "query_builder.rs")
        with open(bad_rs_format, "w", encoding="utf-8") as f:
            f.write("let raw_sql = format!(\"DELETE FROM orders WHERE user_id = '{}'\", uid);\n")

        bad_java_jpa = os.path.join(services_dir, "InvoiceRepository.java")
        with open(bad_java_jpa, "w", encoding="utf-8") as f:
            f.write("public class InvoiceRepository {\n    public List<Invoice> find(EntityManager em, String id) {\n        return em.createNativeQuery(\"SELECT * FROM invoices WHERE id = \" + id).getResultList();\n    }\n}\n")

        clean_rs = os.path.join(services_dir, "clean_repo.rs")
        with open(clean_rs, "w", encoding="utf-8") as f:
            f.write("pub async fn fetch(db: &Pool, id: &str) {\n    let q = sqlx::query(\"SELECT * FROM invoices WHERE id = $1\").bind(id);\n}\n")

        clean_java = os.path.join(services_dir, "CleanRepository.java")
        with open(clean_java, "w", encoding="utf-8") as f:
            f.write("public class CleanRepository {\n    public List<Invoice> find(EntityManager em, String id) {\n        return em.createQuery(\"SELECT i FROM Invoice i WHERE i.id = :id\", Invoice.class).setParameter(\"id\", id).getResultList();\n    }\n}\n")

        for bad_f in [bad_rs_sqlx, bad_rs_sqlx_as, bad_rs_format, bad_java_jpa]:
            findings = scan_file_for_violations(bad_f)
            matching = [f for f in findings if f["id"] == "RULE-5.2-RAW-SQL-CONCAT"]
            self.assertTrue(bool(matching), f"Expected RULE-5.2 in {bad_f}")
            self.assertEqual(matching[0]["severity"], "blocking")

        for clean_f in [clean_rs, clean_java]:
            clean_findings = scan_file_for_violations(clean_f)
            self.assertFalse(any(f["id"] == "RULE-5.2-RAW-SQL-CONCAT" for f in clean_findings), f"Unexpected RULE-5.2 in {clean_f}")

    # --------------------------------------------------------------------------
    # 4. Dimension 6: Tracecontext Propagation (RULE-6.7)
    # --------------------------------------------------------------------------
    def test_polyglot_trace_propagation(self):
        clients_dir = os.path.join(self.temp_dir, "clients")
        os.makedirs(clients_dir, exist_ok=True)

        bad_go = os.path.join(clients_dir, "user_client.go")
        with open(bad_go, "w", encoding="utf-8") as f:
            f.write("package clients\nimport \"net/http\"\nfunc Fetch(url string) {\n    resp, err := http.Get(url)\n}\n")

        bad_go_form = os.path.join(clients_dir, "post_client.go")
        with open(bad_go_form, "w", encoding="utf-8") as f:
            f.write("package clients\nimport \"net/http\"\nfunc Submit(url string) {\n    resp, err := http.PostForm(url, nil)\n}\n")

        bad_rs = os.path.join(clients_dir, "auth_client.rs")
        with open(bad_rs, "w", encoding="utf-8") as f:
            f.write("pub async fn call(url: &str) {\n    let res = reqwest::get(url).await;\n}\n")

        bad_rs_sync = os.path.join(clients_dir, "sync_client.rs")
        with open(bad_rs_sync, "w", encoding="utf-8") as f:
            f.write("pub fn call_sync(url: &str) {\n    let res = reqwest::blocking::get(url);\n}\n")

        bad_php = os.path.join(clients_dir, "Gateway.php")
        with open(bad_php, "w", encoding="utf-8") as f:
            f.write("<?php\nclass Gateway {\n    public function execute() {\n        $c = new \\GuzzleHttp\\Client();\n    }\n}\n")

        bad_java_rt = os.path.join(clients_dir, "BillingAdapter.java")
        with open(bad_java_rt, "w", encoding="utf-8") as f:
            f.write("public class BillingAdapter {\n    private RestTemplate rest = new RestTemplate();\n}\n")

        bad_java_wc = os.path.join(clients_dir, "WebAdapter.java")
        with open(bad_java_wc, "w", encoding="utf-8") as f:
            f.write("public class WebAdapter {\n    private WebClient webClient = WebClient.builder().build();\n}\n")

        bad_cs = os.path.join(clients_dir, "OrderClient.cs")
        with open(bad_cs, "w", encoding="utf-8") as f:
            f.write("public class OrderClient {\n    public void Call() {\n        var client = new HttpClient();\n    }\n}\n")

        bad_cs_handler = os.path.join(clients_dir, "CustomOrderClient.cs")
        with open(bad_cs_handler, "w", encoding="utf-8") as f:
            f.write("public class CustomOrderClient {\n    public void Call(HttpMessageHandler handler) {\n        var client = new HttpClient(handler);\n    }\n}\n")

        clean_client = os.path.join(clients_dir, "InstrumentedClient.ts")
        with open(clean_client, "w", encoding="utf-8") as f:
            f.write("export async function callWithTrace(url: string, headers: Headers) {\n    return fetch(url, { headers });\n}\n")

        clean_go = os.path.join(clients_dir, "instrumented_client.go")
        with open(clean_go, "w", encoding="utf-8") as f:
            f.write("package clients\nimport \"net/http\"\nfunc Fetch(ctx context.Context, url string) {\n    req, _ := http.NewRequestWithContext(ctx, \"GET\", url, nil)\n}\n")

        for bad_f in [bad_go, bad_go_form, bad_rs, bad_rs_sync, bad_php, bad_java_rt, bad_java_wc, bad_cs, bad_cs_handler]:
            findings = scan_file_for_violations(bad_f)
            self.assertTrue(
                any(f["id"] == "RULE-6.7-TRACE-PROPAGATION" for f in findings),
                f"Expected RULE-6.7 in {bad_f}",
            )

        for clean_f in [clean_client, clean_go]:
            clean_findings = scan_file_for_violations(clean_f)
            self.assertFalse(any(f["id"] == "RULE-6.7-TRACE-PROPAGATION" for f in clean_findings), f"Unexpected RULE-6.7 in {clean_f}")

    # --------------------------------------------------------------------------
    # 5. Dimension 7: Cross-Project Imports & Contract Drift (RULE-7.1, RULE-7.2)
    # --------------------------------------------------------------------------
    def test_dimension_7_cross_service_relative_imports_and_schemas(self):
        services_dir = os.path.join(self.temp_dir, "services", "billing", "src")
        os.makedirs(services_dir, exist_ok=True)

        bad_ts_2levels = os.path.join(services_dir, "billing_service.ts")
        with open(bad_ts_2levels, "w", encoding="utf-8") as f:
            f.write("import { UserModel } from '../../services/users/src/user';\nexport class BillingService {}\n")

        bad_ts_3levels = os.path.join(services_dir, "deep_service.ts")
        with open(bad_ts_3levels, "w", encoding="utf-8") as f:
            f.write("import { OrderModel } from '../../../services/orders/src/order';\nexport class DeepService {}\n")

        bad_ts_export = os.path.join(services_dir, "export_service.ts")
        with open(bad_ts_export, "w", encoding="utf-8") as f:
            f.write("export * from '../../services/users/src/user';\n")

        bad_ts_app = os.path.join(services_dir, "app_import.ts")
        with open(bad_ts_app, "w", encoding="utf-8") as f:
            f.write("import { Shell } from '../../apps/web/src/shell';\n")

        bad_py = os.path.join(services_dir, "billing_worker.py")
        with open(bad_py, "w", encoding="utf-8") as f:
            f.write("from ...services.users import UserModel\nclass BillingWorker:\n    pass\n")

        clean_ts = os.path.join(services_dir, "valid_service.ts")
        with open(clean_ts, "w", encoding="utf-8") as f:
            f.write("import { UserContract } from '@monorepo/libs/core-contracts';\nexport class ValidService {}\n")

        for bad_f in [bad_ts_2levels, bad_ts_3levels, bad_ts_export, bad_ts_app, bad_py]:
            f_bad = scan_file_for_violations(bad_f)
            matching = [f for f in f_bad if f["id"] == "RULE-7.1-DIRECT-CROSS-PROJECT-IMPORT"]
            self.assertTrue(bool(matching), f"Expected RULE-7.1 in {bad_f}")
            self.assertEqual(matching[0]["severity"], "blocking")

        f_clean_ts = scan_file_for_violations(clean_ts)
        self.assertFalse(any(f["id"] == "RULE-7.1-DIRECT-CROSS-PROJECT-IMPORT" for f in f_clean_ts))

        # Test RULE-7.2 in schema directories
        schemas_dir = os.path.join(self.temp_dir, "schemas", "billing")
        os.makedirs(schemas_dir, exist_ok=True)
        bad_schema = os.path.join(schemas_dir, "api.yaml")
        with open(bad_schema, "w", encoding="utf-8") as f:
            f.write("DELETE /v1/invoices/{id}\n")

        clean_schema = os.path.join(schemas_dir, "clean_api.yaml")
        with open(clean_schema, "w", encoding="utf-8") as f:
            f.write("paths:\n  /v1/invoices:\n    get:\n      summary: Get invoices\n")

        f_bad_schema = scan_file_for_violations(bad_schema)
        schema_rule = [f for f in f_bad_schema if f["id"] == "RULE-7.2-UNVERSIONED-CONTRACT-MUTATION"]
        self.assertTrue(bool(schema_rule))
        self.assertEqual(schema_rule[0]["severity"], "suggestion")

        f_clean_schema = scan_file_for_violations(clean_schema)
        self.assertFalse(any(f["id"] == "RULE-7.2-UNVERSIONED-CONTRACT-MUTATION" for f in f_clean_schema))

    # --------------------------------------------------------------------------
    # 6. Dimension 8: Java, Kotlin & C# Empty Catches (RULE-8.1)
    # --------------------------------------------------------------------------
    def test_java_and_csharp_empty_catches(self):
        worker_dir = os.path.join(self.temp_dir, "services", "worker")
        os.makedirs(worker_dir, exist_ok=True)

        bad_java = os.path.join(worker_dir, "AppWorker.java")
        with open(bad_java, "w", encoding="utf-8") as f:
            f.write("public class AppWorker {\n    public void execute() {\n        try { process(); } " + "catch" + " (Exception e) {}\n    }\n}\n")

        bad_kt = os.path.join(worker_dir, "AppWorker.kt")
        with open(bad_kt, "w", encoding="utf-8") as f:
            f.write("class AppWorker {\n    fun execute() {\n        try { process() } " + "catch" + " (e: Exception) {}\n    }\n}\n")

        bad_cs = os.path.join(worker_dir, "AppWorker.cs")
        with open(bad_cs, "w", encoding="utf-8") as f:
            f.write("public class AppWorker {\n    public void Execute() {\n        try { Process(); } " + "catch" + " (Exception ex) {}\n    }\n}\n")

        bad_cs_paramless = os.path.join(worker_dir, "ParamlessWorker.cs")
        with open(bad_cs_paramless, "w", encoding="utf-8") as f:
            f.write("public class ParamlessWorker {\n    public void Execute() {\n        try { Process(); } " + "catch" + " {}\n    }\n}\n")

        bad_ts_paramless = os.path.join(worker_dir, "paramless.ts")
        with open(bad_ts_paramless, "w", encoding="utf-8") as f:
            f.write("export function run() {\n    try { doJob(); } " + "catch" + " {}\n}\n")

        clean_java = os.path.join(worker_dir, "CleanWorker.java")
        with open(clean_java, "w", encoding="utf-8") as f:
            f.write("public class CleanWorker {\n    public void execute() {\n        try { process(); } " + "catch" + " (Exception e) { log.error(e); throw e; }\n    }\n}\n")

        for bad_f in [bad_java, bad_kt, bad_cs, bad_cs_paramless, bad_ts_paramless]:
            findings = scan_file_for_violations(bad_f)
            matching = [f for f in findings if f["id"] == "RULE-8.1-EMPTY-CATCH"]
            self.assertTrue(bool(matching), f"Expected RULE-8.1 in {bad_f}")
            self.assertEqual(matching[0]["severity"], "blocking")

        clean_findings = scan_file_for_violations(clean_java)
        self.assertFalse(any(f["id"] == "RULE-8.1-EMPTY-CATCH" for f in clean_findings))

    # --------------------------------------------------------------------------
    # 7. Dimension 10: Go Testify Tautological Assertions (RULE-10.1)
    # --------------------------------------------------------------------------
    def test_go_testify_tautological_assertions(self):
        tests_dir = os.path.join(self.temp_dir, "services", "auth", "tests")
        os.makedirs(tests_dir, exist_ok=True)

        bad_go_true = os.path.join(tests_dir, "auth_true_test.go")
        with open(bad_go_true, "w", encoding="utf-8") as f:
            f.write("package auth_test\nfunc TestAuth(t *testing.T) {\n    " + "assert." + "True(t, true)\n}\n")

        bad_go_false = os.path.join(tests_dir, "auth_false_test.go")
        with open(bad_go_false, "w", encoding="utf-8") as f:
            f.write("package auth_test\nfunc TestToken(t *testing.T) {\n    " + "assert." + "False(t, false)\n}\n")

        bad_go_equal = os.path.join(tests_dir, "auth_equal_test.go")
        with open(bad_go_equal, "w", encoding="utf-8") as f:
            f.write("package auth_test\nfunc TestEqual(t *testing.T) {\n    " + "assert." + "Equal(t, 1, 1)\n}\n")

        bad_go_require = os.path.join(tests_dir, "auth_require_test.go")
        with open(bad_go_require, "w", encoding="utf-8") as f:
            f.write("package auth_test\nfunc TestRequire(t *testing.T) {\n    " + "require." + "True(t, true)\n}\n")

        clean_go = os.path.join(tests_dir, "clean_test.go")
        with open(clean_go, "w", encoding="utf-8") as f:
            f.write("package auth_test\nfunc TestValid(t *testing.T) {\n    " + "assert." + "Equal(t, expected, actual)\n}\n")

        for bad_f in [bad_go_true, bad_go_false, bad_go_equal, bad_go_require]:
            findings = scan_file_for_violations(bad_f)
            matching = [f for f in findings if f["id"] == "RULE-10.1-TAUTOLOGICAL-TEST"]
            self.assertTrue(bool(matching), f"Expected RULE-10.1 in {bad_f}")
            self.assertEqual(matching[0]["severity"], "blocking")

        clean_findings = scan_file_for_violations(clean_go)
        self.assertFalse(any(f["id"] == "RULE-10.1-TAUTOLOGICAL-TEST" for f in clean_findings))

    # --------------------------------------------------------------------------
    # 8. Dimension 4: Structural AST Non-UTC Clock Refinement (RULE-4.4)
    # --------------------------------------------------------------------------
    def test_structural_ast_clock_refinement(self):
        if not ep_ast.is_ast_grep_available():
            self.skipTest("ast-grep not installed")

        db_dir = os.path.join(self.temp_dir, "services", "billing", "repositories")
        os.makedirs(db_dir, exist_ok=True)
        bad_go_repo = os.path.join(db_dir, "invoice_repo.go")
        with open(bad_go_repo, "w", encoding="utf-8") as f:
            f.write("package repositories\nimport \"time\"\nfunc NewInvoice() {\n    createdAt := time.Now()\n}\n")

        tests_dir = os.path.join(self.temp_dir, "services", "billing", "tests")
        os.makedirs(tests_dir, exist_ok=True)
        test_go = os.path.join(tests_dir, "invoice_test.go")
        with open(test_go, "w", encoding="utf-8") as f:
            f.write("package tests\nimport \"time\"\nfunc TestTime() {\n    t := time.Now()\n}\n")

        findings = ep_ast.scan_structural_rules(scope=self.temp_dir)
        clock_violations = [f for f in findings if f["id"] == "RULE-4.4-AST-NON-UTC-CLOCK"]
        self.assertTrue(any("invoice_repo.go" in f["file"] for f in clock_violations))
        self.assertFalse(any("invoice_test.go" in f["file"] for f in clock_violations))


if __name__ == "__main__":
    unittest.main()
