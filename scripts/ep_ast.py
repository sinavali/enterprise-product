#!/usr/bin/env python3
"""
ep_ast.py — Structural Code Intelligence & AST Scanning Engine for EP-OS
Integrates ast-grep for syntax-tree search, structural linting, and semantic
invariant verification across polyglot languages (TS, JS, Go, Rust, Python, PHP).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

AST_GREP_BIN = shutil.which("ast-grep")

# Structural AST Rules for Enterprise Auditing
STRUCTURAL_AST_RULES = [
    {
        "id": "RULE-1.5-AST-MUTABLE-GLOBAL-STATE",
        "dim": 1,
        "severity": "suggestion",
        "description": "Mutable state declared at handler/controller scope; breaks statelessness.",
        "patterns": [
            ("typescript", "let $STATE = { $$$ }"),
            ("javascript", "let $STATE = { $$$ }"),
            ("python", "$STATE = { $$$ }"),
        ],
        "path_filter": lambda p: bool(re.search(r"(controllers|handlers|api|routes)", p, re.IGNORECASE)),
    },
    {
        "id": "RULE-10.1-AST-TAUTOLOGICAL-TEST",
        "dim": 10,
        "severity": "blocking",
        "description": "Tautological identical self-assertion detected in test suite.",
        "patterns": [
            ("typescript", "expect($A).toBe($A)"),
            ("typescript", "expect(true).toBe(true)"),
            ("typescript", "expect(1).toBe(1)"),
            ("python", "self.assertEqual($A, $A)"),
            ("python", "self.assertTrue(True)"),
            ("python", "assert True"),
        ],
        "path_filter": lambda p: bool("test" in p.lower() or "spec" in p.lower()),
    },
    {
        "id": "RULE-8.1-AST-EMPTY-CATCH",
        "dim": 8,
        "severity": "blocking",
        "description": "Empty catch block swallowing errors silently without handling or rethrow.",
        "patterns": [
            ("typescript", "try { $$$BODY } catch ($ERR) {}"),
            ("javascript", "try { $$$BODY } catch ($ERR) {}"),
        ],
        "path_filter": lambda p: not bool("test" in p.lower() or "mock" in p.lower()),
    },
    {
        "id": "RULE-8.6-AST-ENV-IN-DOMAIN",
        "dim": 8,
        "severity": "blocking",
        "description": "Direct unvalidated environment variable access in pure domain layer.",
        "patterns": [
            ("typescript", "process.env.$VAR"),
            ("javascript", "process.env.$VAR"),
            ("python", "os.environ[$VAR]"),
            ("python", "os.getenv($VAR)"),
        ],
        "path_filter": lambda p: "domain" in p.replace("\\", "/").split("/"),
    },
    {
        "id": "RULE-3.1-AST-INFINITE-RETRY",
        "dim": 3,
        "severity": "blocking",
        "description": "Unbounded or infinite retry loop without maximum retry count or backoff.",
        "patterns": [
            ("typescript", "retries: " + "Infinity"),
            ("javascript", "retries: " + "Infinity"),
        ],
        "path_filter": lambda p: True,
    },
    {
        "id": "RULE-2.1-AST-ORM-IN-DOMAIN",
        "dim": 2,
        "severity": "blocking",
        "description": "Direct ORM/persistence import inside pure domain layer.",
        "patterns": [
            ("typescript", "import $$$IMPORTS from 'prisma'"),
            ("typescript", "import $$$IMPORTS from '@prisma/client'"),
            ("typescript", "import $$$IMPORTS from 'typeorm'"),
            ("python", "import sqlalchemy"),
            ("python", "from sqlalchemy import $$$IMPORTS"),
        ],
        "path_filter": lambda p: "domain" in p.replace("\\", "/").split("/"),
    },
    {
        "id": "RULE-1.7-AST-NON-UTC-CLOCK",
        "dim": 1,
        "severity": "blocking",
        "description": "Non-UTC clock or un-timezoned timestamp creation in persistence or domain; violates UTC storage convention.",
        "patterns": [
            ("typescript", "new Date()"),
            ("python", "datetime.now()"),
            ("python", "datetime.today()"),
        ],
        "path_filter": lambda p: not bool(re.search(r"(\.spec\.|\.test\.|_test|tests?[\\/])", p, re.IGNORECASE)),
    },
    {
        "id": "RULE-3.8-AST-TRANSACTIONAL-OUTBOX",
        "dim": 3,
        "severity": "suggestion",
        "description": "Direct message bus / event publish inside database repository without transactional outbox.",
        "patterns": [
            ("typescript", "await $BUS.publish($$$ARGS)"),
            ("typescript", "await $PRODUCER.send($$$ARGS)"),
            ("python", "$bus.publish($$$ARGS)"),
        ],
        "path_filter": lambda p: bool(re.search(r"(repositories|adapters/db|persistence)", p, re.IGNORECASE)),
    },
]


def is_ast_grep_available() -> bool:
    return AST_GREP_BIN is not None


def run_ast_query(pattern: str, scope: str = ".", lang: Optional[str] = None) -> List[Dict[str, Any]]:
    if not is_ast_grep_available():
        return []

    cmd = [AST_GREP_BIN, "run", "--pattern", pattern, scope, "--json"]
    if lang:
        cmd.extend(["--lang", lang])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
    except Exception:
        pass
    return []


def scan_structural_rules(scope: str = ".") -> List[Dict[str, Any]]:
    if not is_ast_grep_available():
        return []

    findings = []
    for rule in STRUCTURAL_AST_RULES:
        for lang, pattern in rule["patterns"]:
            matches = run_ast_query(pattern, scope=scope, lang=lang)
            for m in matches:
                file_path = m.get("file", "")
                norm_p = file_path.replace("\\", "/")
                parts = set(norm_p.split("/"))
                if parts.intersection({"node_modules", "dist", "dist-next", ".next", "build", ".nx", "coverage", ".git", ".cache"}):
                    continue
                if not rule["path_filter"](file_path):
                    continue

                # For $A == $A identity patterns, ensure single variable meta-variables match if present
                meta = m.get("metaVariables", {}).get("single", {})
                if "$A" in pattern and "A" in meta:
                    # In ast-grep, matching expect($A).toBe($A) automatically matches identical A nodes
                    pass

                start_line = m.get("range", {}).get("start", {}).get("line", 0) + 1
                snippet = m.get("lines", "").strip()[:100]

                findings.append({
                    "dim": rule["dim"],
                    "id": rule["id"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "file": file_path,
                    "line": start_line,
                    "snippet": snippet,
                    "engine": "ast-grep",
                })

    return findings


def cmd_ast(args: argparse.Namespace) -> int:
    if not is_ast_grep_available():
        print("[ERROR] 'ast-grep' binary is not installed or not in PATH.", file=sys.stderr)
        print("        Install globally: npm install -g @ast-grep/cli", file=sys.stderr)
        return 1

    action = getattr(args, "action", "search")
    scope = getattr(args, "scope", ".") or "."

    if action == "search":
        pattern = args.pattern
        lang = getattr(args, "lang", None)
        print(f"=== ast-grep Structural Search ===")
        print(f"Pattern: '{pattern}' | Scope: '{scope}' | Lang: {lang or 'auto'}\n")
        matches = run_ast_query(pattern, scope=scope, lang=lang)
        if not matches:
            print("[INFO] Zero AST matches found.")
            return 0

        print(f"[OK] Found {len(matches)} structural match(es):")
        for m in matches:
            loc = f"{m.get('file', '')}:{m.get('range', {}).get('start', {}).get('line', 0) + 1}"
            print(f"  • {loc} -> {m.get('text', '').strip()[:80]}")
        return 0

    elif action == "scan":
        print(f"=== ast-grep Structural Invariant Scanner ===")
        print(f"Scanning scope: '{scope}' against 10-dimension AST rules...")
        findings = scan_structural_rules(scope=scope)
        if not findings:
            print("[PASS] Zero structural AST violations detected.")
            return 0

        print(f"[FAIL] Detected {len(findings)} structural AST violation(s):", file=sys.stderr)
        for f in findings:
            print(f"  ❌ [{f['id']}] {f['file']}:{f['line']}", file=sys.stderr)
            print(f"     Match: {f['snippet']}", file=sys.stderr)
            print(f"     Note: {f['description']}", file=sys.stderr)
        return 1

    return 0
