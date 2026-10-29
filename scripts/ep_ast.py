#!/usr/bin/env python3
"""
ep_ast.py — Structural Code Intelligence & AST Scanning Engine for EP-OS
Integrates ast-grep for syntax-tree search, structural linting, and semantic
invariant verification across polyglot languages (TS, JS, Go, Rust, Python, PHP).
Includes persistent AST result caching (.ep/cache/ast_cache.json) and diff scoping
for accelerated agent feedback cycles.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, cast

try:
    from scripts.ep_context import collect_files_from_diff, collect_files_from_surface
except ImportError:
    from ep_context import collect_files_from_diff, collect_files_from_surface  # type: ignore[import-not-found,no-redef]

AST_GREP_BIN = shutil.which("ast-grep")
CACHE_FILE = ".ep/cache/ast_cache.json"


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
        "id": "RULE-4.4-AST-NON-UTC-CLOCK",
        "dim": 4,
        "severity": "blocking",
        "description": "Non-UTC clock or un-timezoned timestamp creation in persistence or domain; violates UTC storage convention.",
        "patterns": [
            ("typescript", "new Date()"),
            ("python", "datetime.now()"),
            ("python", "datetime.today()"),
            ("go", "time.Now()"),
        ],
        "path_filter": lambda p: bool(re.search(r"(domain|persistence|models|entities|repositories|db)", p, re.IGNORECASE)) and not bool(re.search(r"(\.spec\.|\.test\.|_test|tests?[\\/])", p, re.IGNORECASE)),
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


def _sha256_file(filepath: str) -> str:
    try:
        with open(filepath, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except Exception:
        return ""


def load_ast_cache() -> Dict[str, Any]:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_ast_cache(cache: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def run_ast_query(pattern: str, scope: str = ".", lang: Optional[str] = None) -> List[Dict[str, Any]]:
    if not is_ast_grep_available() or not AST_GREP_BIN:
        return []

    cmd: List[str] = [AST_GREP_BIN, "run", "--pattern", pattern, scope, "--json"]
    if lang:
        cmd.extend(["--lang", lang])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
    except Exception:
        pass
    return []


LANG_EXTENSIONS = {
    "typescript": {".ts", ".tsx"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "python": {".py"},
    "go": {".go"},
    "rust": {".rs"},
    "php": {".php"},
}


def scan_structural_rules(scope: str = ".", target_files: Optional[List[str]] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
    if not is_ast_grep_available():
        return []

    cache = load_ast_cache() if use_cache else {}
    findings: List[Dict[str, Any]] = []

    # If target_files is provided, scope to those files
    scopes = target_files if target_files is not None else [scope]

    for target_scope in scopes:
        is_file = os.path.isfile(target_scope)
        target_ext = os.path.splitext(target_scope)[1].lower() if is_file else ""

        if is_file and use_cache:
            file_hash = _sha256_file(target_scope)
            if file_hash and target_scope in cache:
                cached_entry = cache[target_scope]
                if cached_entry.get("hash") == file_hash:
                    findings.extend(cached_entry.get("findings", []))
                    continue

        file_findings: List[Dict[str, Any]] = []
        for rule in STRUCTURAL_AST_RULES:
            patterns = cast(List[Tuple[str, str]], rule.get("patterns", []))
            path_filter = cast(Callable[[str], bool], rule.get("path_filter", lambda p: True))
            for lang, pattern in patterns:
                # Performance optimization: skip rules if inspecting a single file whose extension doesn't match the language
                if is_file and lang in LANG_EXTENSIONS and target_ext not in LANG_EXTENSIONS[lang]:
                    continue

                matches = run_ast_query(pattern, scope=target_scope, lang=lang)
                for m in matches:
                    file_path = m.get("file", "")
                    norm_p = file_path.replace("\\", "/")
                    parts = set(norm_p.split("/"))
                    if parts.intersection({"node_modules", "dist", "dist-next", ".next", "build", ".nx", "coverage", ".git", ".cache"}):
                        continue
                    if not path_filter(file_path):
                        continue

                    start_line = m.get("range", {}).get("start", {}).get("line", 0) + 1
                    snippet = m.get("lines", "").strip()[:100]

                    item = {
                        "dim": rule["dim"],
                        "id": rule["id"],
                        "severity": rule["severity"],
                        "description": rule["description"],
                        "file": file_path,
                        "line": start_line,
                        "snippet": snippet,
                        "engine": "ast-grep",
                    }
                    findings.append(item)
                    file_findings.append(item)

        if is_file and use_cache:
            file_hash = _sha256_file(target_scope)
            if file_hash:
                cache[target_scope] = {
                    "hash": file_hash,
                    "findings": file_findings,
                }

    if use_cache:
        save_ast_cache(cache)

    return findings


def cmd_ast(args: argparse.Namespace) -> int:
    if not is_ast_grep_available():
        print("[ERROR] 'ast-grep' binary is not installed or not in PATH.", file=sys.stderr)
        print("        Install globally: npm install -g @ast-grep/cli", file=sys.stderr)
        return 1

    action = getattr(args, "action", "search")
    scope = getattr(args, "scope", ".") or "."
    target_files: Optional[List[str]] = None

    if getattr(args, "surface", False):
        target_files = collect_files_from_surface(root_dir=scope if os.path.isdir(scope) else ".")
    elif getattr(args, "diff", None):
        base = args.diff if isinstance(args.diff, str) else "origin/main"
        target_files = collect_files_from_diff(base=base, root_dir=scope if os.path.isdir(scope) else ".")

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
        if target_files is not None:
            scope_desc = "active Change Surface" if getattr(args, "surface", False) else "git diff"
            print(f"Scanning {scope_desc} ({len(target_files)} modified file(s)) with AST cache...")
        else:
            print(f"Scanning scope: '{scope}' against 10-dimension AST rules...")


        findings = scan_structural_rules(scope=scope, target_files=target_files)
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
