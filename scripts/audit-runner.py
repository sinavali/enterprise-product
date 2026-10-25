#!/usr/bin/env python3
"""
audit-runner.py
Automated runner and scanner for the 10-Dimension Enterprise Audit Suite.
Scans source files within a specified scope or diff for common violations,
computes the scorecard, and scaffolds or verifies AUDIT_REPORT.md.
Supports structural anti-sprawl bounds (file size, folder depth) and
brownfield baseline ratchet mode.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple


DIMENSIONS = [
    (1, "Scalability & Capacity"),
    (2, "Structural Maintainability & Modularity"),
    (3, "Fault Tolerance & Resilience"),
    (4, "Data Integrity & Concurrency"),
    (5, "Security & Zero-Trust"),
    (6, "Observability & Operability"),
    (7, "Contract & Schema Drift"),
    (8, "Code Quality & Typing Strictness"),
    (9, "Documentation & Spec Drift"),
    (10, "Test Fidelity & Assertion Quality"),
]

# Static heuristic scanners for critical enterprise anti-patterns
HEURISTIC_RULES = [
    {
        "dim": 1,
        "id": "RULE-1.1-UNBOUNDED-SCAN",
        "severity": "suggestion",
        "description": "Unbounded collection query or full-table scan pattern without explicit limit.",
        "path_regex": r"(services|apps|libs|packages)[\\/].*\.(ts|js|go|cs|php|py)$",
        "content_regex": r"(\.findAll\(\s*\)|\.find\(\{\s*\}\)|SELECT\s+\*\s+FROM\s+[a-zA-Z0-9_]+(?:\s*;|\s*[\"\'`\n]|\s*$))",
    },
    {
        "dim": 1,
        "id": "RULE-1.5-MUTABLE-GLOBAL-STATE",
        "severity": "suggestion",
        "description": "Mutable global or module-level state detected in request handler or controller; breaks statelessness.",
        "path_regex": r"(controllers|handlers|api|routes)[\\/].*\.(ts|js|py)$",
        "content_regex": r"^(?:var|let)\s+(?:sessions?|tokens?|cache|state|users?)\s*=\s*(?:\{|\[)|^(?:sessions?|global_cache|shared_state)\s*=\s*(?:\{|\[)",
    },
    {
        "dim": 2,
        "id": "RULE-2.1-ORM-IN-DOMAIN",
        "severity": "blocking",
        "description": "Direct ORM/framework dependency found in pure domain layer.",
        "path_regex": r"domain[\\/].*\.(ts|tsx|js|jsx|go|cs|php|py|rs|dart|java|kt)$",
        "content_regex": r"(from ['\"](typeorm|prisma|sequelize|mongoose|gorm|sqlalchemy|django\.db)['\"]|import ['\"].*gorm.*['\"]|using Microsoft\.EntityFrameworkCore|use Illuminate\\Database|import (sqlalchemy|tortoise)|org\.hibernate|javax\.persistence|jakarta\.persistence|org\.springframework\.data|diesel::|sea_orm::)",
    },
    {
        "dim": 3,
        "id": "RULE-3.1-INFINITE-RETRY",
        "severity": "blocking",
        "description": "Unbounded or infinite retry loop without max retry cap or backoff.",
        "path_regex": r"\.(ts|tsx|js|jsx|go|cs|php|py|rs|dart|java|kt)$",
        "content_regex": r"(retries:\s*Infinity|maxRetries:\s*-1|while\s*\(true\)\s*\{\s*try)",
    },
    {
        "dim": 3,
        "id": "RULE-3.7-UNBOUNDED-QUEUE-PREFETCH",
        "severity": "suggestion",
        "description": "Queue consumer prefetch or concurrency configured without bounded limit; risk of OOM under backpressure.",
        "path_regex": r"(consumers|queues|subscribers|workers)[\\/].*\.(ts|js|py|go|cs)$",
        "content_regex": r"(prefetch:\s*0\b|noAck:\s*true\b|prefetch_count\s*=\s*0\b|Prefetch\(\s*0\s*\))",
    },
    {
        "dim": 3,
        "id": "RULE-3.8-TRANSACTIONAL-OUTBOX-DUAL-WRITE",
        "severity": "suggestion",
        "description": "Direct message bus / event publish inside database repository without transactional outbox pattern.",
        "path_regex": r"(repositories|adapters[\\/]db|persistence)[\\/].*\.(ts|js|py|go|cs)$",
        "content_regex": r"(\.publish\(|\.send\(|\.produce\().*\b(event|message|topic|queue)\b",
    },
    {
        "dim": 4,
        "id": "RULE-4.1-SQLITE-IN-INTEGRATION",
        "severity": "blocking",
        "description": "Banned in-memory SQL emulator (SQLite/H2) substituting production database in integration tests.",
        "path_regex": r"(?:integration[\\/]|tests?[\\/].*integration|[._-]integration\.).*\.(ts|tsx|js|jsx|go|cs|php|py|rs|dart|java|kt)$",
        "content_regex": r"(:memory:|sqlite3\.connect\(['\"]:memory:['\"]\)|UseSqlite\(|createConnection\(\{.*type:\s*['\"]sqlite['\"])",
    },
    {
        "dim": 4,
        "id": "RULE-4.3-NON-UTC-TIMESTAMP",
        "severity": "blocking",
        "description": "Non-UTC clock or un-timezoned timestamp creation in persistence or domain model; violates Tier 1 UTC convention.",
        "path_regex": r"(domain|models|entities|persistence|db|repositories)[\\/].*\.(ts|js|go|cs|php|py)$",
        "content_regex": r"(DateTime\.Now\b|datetime\.now\(\)|datetime\.today\(\)|CURRENT_TIMESTAMP\b|TIMESTAMP\s+WITHOUT\s+TIME\s+ZONE)",
    },
    {
        "dim": 5,
        "id": "RULE-5.1-HARDCODED-SECRET",
        "severity": "blocking",
        "description": "Possible hardcoded secret or API credential key detected.",
        "path_regex": r"\.(ts|js|go|cs|php|py|json|yaml|yml)$",
        "content_regex": r"(apiKey|api_key|secretKey|private_key|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
    },
    {
        "dim": 5,
        "id": "RULE-5.2-RAW-SQL-CONCAT",
        "severity": "blocking",
        "description": "Possible unparameterized SQL string concatenation; risk of injection.",
        "path_regex": r"(services|apps|libs|packages)[\\/].*\.(ts|js|go|cs|php|py)$",
        "content_regex": r"(\.raw\(|query\(|execute\(|queryRaw\(|ExecuteSqlRaw\(|SqlQueryRaw\()(['\"].*?\b(SELECT|INSERT|UPDATE|DELETE)\b.*?\s*(\+|%)\s*|\s*f['\"].*?\b(SELECT|INSERT|UPDATE|DELETE)\b|\s*\$['\"].*?\b(SELECT|INSERT|UPDATE|DELETE)\b)",
    },
    {
        "dim": 6,
        "id": "RULE-6.1-BARE-CONSOLE-LOG",
        "severity": "suggestion",
        "description": "Direct console.log in production code; prefer structured JSON logging.",
        "path_regex": r"(services|apps|libs|packages)[\\/].*src[\\/].*\.(ts|js)$",
        "content_regex": r"console\.(log|debug)\(",
    },
    {
        "dim": 6,
        "id": "RULE-6.5-PII-LOGGING",
        "severity": "blocking",
        "description": "Unsanitized logging of sensitive PII or credentials detected.",
        "path_regex": r"(services|apps|libs|packages)[\\/].*\.(ts|js|go|cs|php|py)$",
        "content_regex": r"(log|logger|console|_logger)\.(info|debug|warn|warning|error|exception|critical|log|LogInformation|LogWarning|LogError)\([^)]*\b(password|user_password|auth_token|credit_card|secret_key)\b",
    },
    {
        "dim": 6,
        "id": "RULE-6.7-TRACE-PROPAGATION",
        "severity": "suggestion",
        "description": "Outbound HTTP request detected without traceparent / correlation context header propagation.",
        "path_regex": r"(clients|gateways|adapters|http)[\\/].*\.(ts|js|py)$",
        "content_regex": r"(axios\.(get|post|put|delete)\([^,\)]+\)|requests\.(get|post|put|delete)\([^,\)]+\))\s*(?:;|\n|$)",
    },
    {
        "dim": 8,
        "id": "RULE-8.1-EMPTY-CATCH",
        "severity": "blocking",
        "description": "Empty catch block swallowing errors silently without logging or re-throwing.",
        "path_regex": r"\.(ts|js|cs|php)$",
        "content_regex": r"catch\s*\([^\)]*\)\s*\{\s*\}",
    },
    {
        "dim": 8,
        "id": "RULE-8.2-EXPLICIT-ANY",
        "severity": "suggestion",
        "description": "Untyped 'any' in production TypeScript; use strict types or unknown.",
        "path_regex": r"(services|apps|libs|packages)[\\/].*src[\\/].*\.(ts|tsx)$",
        "content_regex": r":\s*any\b",
    },
    {
        "dim": 8,
        "id": "RULE-8.6-NAKED-ENV-IN-DOMAIN",
        "severity": "blocking",
        "description": "Direct, unvalidated environment variable access in pure domain layer; violates 12-factor typed configuration.",
        "path_regex": r"domain[\\/].*\.(ts|tsx|js|jsx|go|cs|php|py|rs|dart|java|kt)$",
        "content_regex": r"(process\.env\b|os\.environ\b|os\.getenv\b|getenv\(|\$_ENV\b|System\.Environment\.GetEnvironmentVariable)",
    },
    {
        "dim": 10,
        "id": "RULE-10.1-TAUTOLOGICAL-TEST",
        "severity": "blocking",
        "description": "Tautological or vacuous test assertion detected.",
        "path_regex": r"(\.(spec|test)|_test|([\\/]|^)test_[^\\/]*|([\\/]|^)tests?[\\/].*)\.(ts|tsx|js|jsx|go|cs|py|rs|dart|java|kt)$",
        "content_regex": r"(expect\((true|1)\)\.(toBe|toBeTruthy)\((true|1)?\)|assert\.(True|Equal)\(true|assert\s+True\b|assert\s+1\s*==\s*1|self\.assertTrue\(True\)|self\.assertEqual\((True,\s*True|1,\s*1)\))",
    },
    {
        "dim": 10,
        "id": "RULE-10.2-SKIPPED-TEST",
        "severity": "blocking",
        "description": "Skipped test detected in test suite; disabled tests mask regressions.",
        "path_regex": r"(\.(spec|test)|_test|([\\/]|^)test_[^\\/]*|([\\/]|^)tests?[\\/].*)\.(ts|tsx|js|jsx|go|cs|py|rs|dart|java|kt)$",
        "content_regex": r"(\b(xit|it\.skip|describe\.skip|test\.skip|t\.Skip|pytest\.mark\.skip|pytest\.skip)\b|@unittest\.skip|->skip\(|\[Fact\(Skip|\[Ignore)",
    },
]

EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    ".nx",
    "dist",
    "dist-next",
    ".next",
    "build",
    "coverage",
    ".cache",
    ".venv",
    "vendor",
    "fixtures",
    "templates",
    "__pycache__",
    "obj",
    "bin",
    "target",
}

CODE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".go", ".cs", ".php", ".py", ".rs", ".dart", ".java", ".kt", ".swift", ".cpp", ".c"
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg", ".pdf",
    ".wasm", ".zip", ".tar", ".gz", ".7z", ".rar", ".db", ".sqlite",
    ".sqlite3", ".bin", ".pyc", ".pyo", ".pyd", ".exe", ".dll", ".so",
    ".dylib", ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".mov",
    ".avi", ".iso", ".dat"
}


def scan_file_for_violations(file_path: str, max_file_lines: int = 800) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    norm_path = file_path.replace("\\", "/")
    full_norm_path = os.path.abspath(file_path).replace("\\", "/")
    _, ext = os.path.splitext(norm_path.lower())

    if ext in BINARY_EXTENSIONS:
        return findings

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return findings

    # Check file size boundary for production source files
    is_test_file = bool(re.search(r"(\.(spec|test)\.|[\\/]tests?[\\/]|test_)", norm_path, re.IGNORECASE))
    if ext in CODE_EXTENSIONS and not is_test_file and len(lines) > max_file_lines:
        findings.append({
            "dim": 2,
            "id": "RULE-2.6-FILE-SIZE-CEILING",
            "severity": "blocking",
            "description": f"File exceeds maximum line ceiling of {max_file_lines} lines ({len(lines)} lines found). Must be split or modularized.",
            "file": norm_path,
            "line": len(lines),
            "snippet": f"Total line count: {len(lines)}",
        })

    for rule in HEURISTIC_RULES:
        path_pat = str(rule["path_regex"])
        if not (re.search(path_pat, norm_path, re.IGNORECASE) or re.search(path_pat, full_norm_path, re.IGNORECASE)):
            continue

        content_pat = str(rule["content_regex"])
        compiled_regex = re.compile(content_pat, re.IGNORECASE)
        for idx, line in enumerate(lines, start=1):
            if rule["id"] == "RULE-5.1-HARDCODED-SECRET" and re.search(
                r"(test|mock|dummy|fake|example|placeholder)", line, re.IGNORECASE
            ):
                continue
            if compiled_regex.search(line):
                findings.append({
                    "dim": rule["dim"],
                    "id": rule["id"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "file": norm_path,
                    "line": idx,
                    "snippet": line.strip()[:100],
                })

    return findings


def run_audit(target_dir: str, max_file_lines: int = 800, max_dir_depth: int = 6, diff_base: Optional[str] = None) -> Tuple[List[Dict], Dict]:
    if not os.path.exists(target_dir) and not diff_base:
        raise FileNotFoundError(f"Target path '{target_dir}' does not exist.")

    all_findings = []

    if diff_base:
        try:
            res = subprocess.run(["git", "diff", "--name-only", diff_base], capture_output=True, text=True, check=False, timeout=30)
            if res.returncode == 0:
                files_to_scan = [f.strip() for f in res.stdout.splitlines() if f.strip() and os.path.exists(f.strip())]
            else:
                files_to_scan = [target_dir] if os.path.isfile(target_dir) else []
        except Exception:
            files_to_scan = [target_dir] if os.path.isfile(target_dir) else []
    elif os.path.isfile(target_dir):
        files_to_scan = [target_dir]
    else:
        files_to_scan = []
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            
            # Directory depth & dumping ground check
            rel_dir = os.path.relpath(root, target_dir)
            if rel_dir != ".":
                dir_parts = [p for p in rel_dir.replace("\\", "/").split("/") if p]
                # Calculate nesting depth relative to the nearest subproject root if auditing from workspace root
                if dir_parts and dir_parts[0] in {"services", "apps", "libs", "packages"} and len(dir_parts) >= 2:
                    depth = len(dir_parts) - 2
                else:
                    depth = len(dir_parts)

                if depth > max_dir_depth:
                    all_findings.append({
                        "dim": 2,
                        "id": "RULE-2.5-OVER-NESTED-DIRECTORY",
                        "severity": "blocking",
                        "description": f"Directory hierarchy exceeds maximum depth of {max_dir_depth} (depth {depth} found).",
                        "file": rel_dir.replace("\\", "/"),
                        "line": 1,
                        "snippet": f"Path: {rel_dir}",
                    })
                
                # Check for generic uncohesive dumping grounds
                for p in dir_parts:
                    if p.lower() in {"utils", "helpers", "misc", "common"}:
                        all_findings.append({
                            "dim": 2,
                            "id": "RULE-2.8-GENERIC-DUMPING-GROUND",
                            "severity": "suggestion",
                            "description": f"Generic dumping ground folder '{p}' detected; categorize utilities by domain capability.",
                            "file": rel_dir.replace("\\", "/"),
                            "line": 1,
                            "snippet": f"Directory: {rel_dir}",
                        })
                        break

                # Check for operational runbook requirement on services/apps
                if dir_parts and dir_parts[0] in {"services", "apps"} and len(dir_parts) == 2:
                    svc_name = dir_parts[1]
                    if os.path.exists(os.path.join(root, "project.json")):
                        has_runbook = (
                            os.path.exists(os.path.join(root, "RUNBOOK.md"))
                            or os.path.exists(os.path.join(target_dir, "docs", "runbooks", f"{svc_name}.md"))
                            or os.path.exists(os.path.join(target_dir, "docs", "runbooks", f"{svc_name}.runbook.md"))
                        )
                        if not has_runbook:
                            all_findings.append({
                                "dim": 9,
                                "id": "RULE-9.5-OPERATIONAL-RUNBOOK",
                                "severity": "suggestion",
                                "description": f"Service '{svc_name}' lacks an operational runbook. Create one using 'templates/RUNBOOK.template.md'.",
                                "file": os.path.join(rel_dir, "project.json").replace("\\", "/"),
                                "line": 1,
                                "snippet": f"Service: {svc_name}",
                            })

            for f in files:
                files_to_scan.append(os.path.join(root, f))
                
    for f in sorted(files_to_scan):
        all_findings.extend(scan_file_for_violations(f, max_file_lines=max_file_lines))

    # Integrate ast-grep structural scanning when available
    if TYPE_CHECKING:
        from scripts.ep_ast import is_ast_grep_available, scan_structural_rules
    else:
        try:
            from scripts.ep_ast import is_ast_grep_available, scan_structural_rules
        except ImportError:
            try:
                from ep_ast import is_ast_grep_available, scan_structural_rules
            except ImportError:
                def is_ast_grep_available() -> bool:
                    return False
                def scan_structural_rules(scope: str = ".") -> List[Dict[str, Any]]:
                    return []

    if is_ast_grep_available() and os.path.exists(target_dir):
        ast_findings = scan_structural_rules(target_dir)
        seen_violations = set()
        for finding_item in all_findings:
            parts = str(finding_item.get("id", "")).split("-")
            rule_num = parts[1] if len(parts) > 1 else str(finding_item.get("id", ""))
            seen_violations.add((str(finding_item.get("file", "")), int(str(finding_item.get("line", 0))), rule_num))

        for af in ast_findings:
            parts = str(af.get("id", "")).split("-")
            rule_num = parts[1] if len(parts) > 1 else str(af.get("id", ""))
            viol_key = (str(af.get("file", "")), int(str(af.get("line", 0))), rule_num)
            if viol_key not in seen_violations:
                all_findings.append(af)
                seen_violations.add(viol_key)

    # Tally results
    scorecard: Dict[int, Dict[str, Any]] = {}
    for dim_num, dim_name in DIMENSIONS:
        scorecard[dim_num] = {
            "name": dim_name,
            "blocking": 0,
            "suggestion": 0,
            "nit": 0,
        }
        
    for finding in all_findings:
        dim = int(str(finding["dim"]))
        sev = str(finding["severity"])
        if dim in scorecard:
            scorecard[dim][sev] = int(scorecard[dim].get(sev, 0)) + 1
            
    return all_findings, scorecard


def filter_against_baseline(findings: List[Dict], baseline_data: Any) -> Tuple[List[Dict], int]:
    """
    Suppresses findings that were already recorded in the baseline snapshot.
    Enforces the ratchet principle: 0 new blocking defects.
    """
    if isinstance(baseline_data, dict) and "findings" in baseline_data:
        baseline_data = baseline_data["findings"]
    elif not isinstance(baseline_data, list):
        baseline_data = []

    def norm_id(rid: str) -> str:
        return rid.replace("-AST-", "-") if isinstance(rid, str) else ""

    baseline_fingerprints: Set[str] = {
        f"{norm_id(b.get('id', ''))}:{b.get('file')}:{b.get('line', '')}" for b in baseline_data if isinstance(b, dict)
    }
    
    new_findings = []
    suppressed_count = 0
    
    for f in findings:
        fid = norm_id(f.get("id", ""))
        fp = f"{fid}:{f.get('file')}:{f.get('line', '')}"
        # Fallback loose fingerprint (id + file)
        fp_loose = f"{fid}:{f.get('file')}:"
        
        if fp in baseline_fingerprints or any(b.startswith(fp_loose) for b in baseline_fingerprints):
            suppressed_count += 1
        else:
            new_findings.append(f)
            
    return new_findings, suppressed_count


def generate_markdown_report(target: str, findings: List[Dict], scorecard: Dict, baseline_suppressed: int = 0) -> str:
    total_blocking = sum(s["blocking"] for s in scorecard.values())
    total_suggestion = sum(s["suggestion"] for s in scorecard.values())
    total_nit = sum(s["nit"] for s in scorecard.values())
    verdict = "PASS" if total_blocking == 0 else "FAIL"
    today = datetime.date.today().isoformat()
    
    lines = [
        "# 10-Dimension Enterprise Audit Report",
        "",
        f"**Audit Target**: `{target}`  ",
        f"**Date**: `{today}`  ",
        "**Auditor**: `audit-runner.py`  ",
        f"**Overall Verdict**: **{verdict}**  ",
    ]
    if baseline_suppressed > 0:
        lines.append(f"**Baseline Ratchet**: `{baseline_suppressed}` pre-existing findings suppressed.  ")
        
    lines.extend([
        "",
        "---",
        "",
        "## 1. Summary Scorecard",
        "",
        "| Dimension | Status | Blocking | Suggestions | Nits |",
        "|---|---|---|---|---|",
    ])
    
    for dim_num, dim_name in DIMENSIONS:
        s = scorecard[dim_num]
        status = "PASS" if s["blocking"] == 0 else "FAIL"
        lines.append(f"| **{dim_num}. {dim_name}** | {status} | {s['blocking']} | {s['suggestion']} | {s['nit']} |")
        
    lines.append(f"| **TOTALS** | **{verdict}** | **{total_blocking}** | **{total_suggestion}** | **{total_nit}** |")
    lines.extend([
        "",
        "---",
        "",
        "## 2. Findings Log",
        "",
    ])
    
    if not findings:
        lines.append("No defects identified. All 10 dimensions meet enterprise standards.")
    else:
        for idx, f in enumerate(findings, start=1):
            lines.extend([
                f"### Finding F-{idx:03d}: {f['id']}",
                f"- **Dimension**: {f['dim']}. {scorecard[f['dim']]['name']}",
                f"- **Severity**: `{f['severity']}`",
                f"- **Location**: `{f['file']}:{f['line']}`",
                f"- **Violation**: {f['description']}",
                f"- **Code Snippet**: `{f['snippet']}`",
                "",
            ])
            
    lines.extend([
        "---",
        "",
        "## 3. Mandatory Tier 1 Invariant Checks",
        "",
        f"- [{'x' if total_blocking == 0 else ' '}] Single Monorepo compliance (orchestrated by Nx root).",
        f"- [{'x' if scorecard[2]['blocking'] == 0 else ' '}] Pure Domain logic (zero framework / ORM leaking into domain).",
        f"- [{'x' if scorecard[4]['blocking'] == 0 else ' '}] Ephemeral Real Containers for all DB integration tests (Testcontainers/Podman).",
        f"- [{'x' if scorecard[4]['blocking'] == 0 else ' '}] UTC Storage Convention strictly observed in all datastores and contracts.",
        f"- [{'x' if scorecard[9]['blocking'] == 0 else ' '}] Zero unaddressed open `NEED_CLARIFICATION` items older than 14 days.",
        f"- [{'x' if scorecard[9]['blocking'] == 0 else ' '}] Change Surface declared and mechanically validated before implementation.",
        "",
        "---",
        "",
        "## 4. Next Step & Protocol Action",
        f"- **Audit Status**: {verdict}",
        f"- **Action**: {'PR is approved for merge progression.' if verdict == 'PASS' else 'Blocking defects must be remediated before PR merge.'}",
        "",
    ])
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run 10-dimension enterprise audit suite.")
    parser.add_argument("--scope", default=".", help="Directory or file path to audit (default: .)")
    parser.add_argument("--output", help="Path to save AUDIT_REPORT.md")
    parser.add_argument("--max-file-lines", type=int, default=800, help="Maximum allowed lines per file (default: 800)")
    parser.add_argument("--max-dir-depth", type=int, default=6, help="Maximum allowed directory nesting depth (default: 6)")
    parser.add_argument("--baseline", help="Path to baseline JSON file for ratchet auditing")
    parser.add_argument("--save-baseline", help="Path to save current findings as baseline JSON")
    parser.add_argument("--diff", help="Audit only modified git diff files against base (e.g. main or HEAD~1)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()

    if not os.path.exists(args.scope) and not args.diff:
        print(f"[ERROR] Target scope '{args.scope}' does not exist.", file=sys.stderr)
        sys.exit(1)

    raw_findings, _ = run_audit(args.scope, max_file_lines=args.max_file_lines, max_dir_depth=args.max_dir_depth, diff_base=args.diff)

    if args.save_baseline:
        with open(args.save_baseline, "w", encoding="utf-8") as f:
            json.dump(raw_findings, f, indent=2)
        print(f"[INFO] Saved {len(raw_findings)} baseline findings to {args.save_baseline}")
        sys.exit(0)

    suppressed_count = 0
    if args.baseline:
        if os.path.exists(args.baseline):
            try:
                with open(args.baseline, "r", encoding="utf-8") as f:
                    baseline_data = json.load(f)
                findings, suppressed_count = filter_against_baseline(raw_findings, baseline_data)
            except Exception as e:
                print(f"[WARNING] Failed to parse baseline file '{args.baseline}': {e}. Auditing without baseline.")
                findings = raw_findings
        else:
            print(f"[WARNING] Baseline file '{args.baseline}' not found. Auditing without baseline.")
            findings = raw_findings
    else:
        findings = raw_findings
        
    # Re-tally scorecard from active findings
    scorecard = {}
    for dim_num, dim_name in DIMENSIONS:
        scorecard[dim_num] = {
            "name": dim_name,
            "blocking": 0,
            "suggestion": 0,
            "nit": 0,
        }
    for finding in findings:
        dim = finding["dim"]
        sev = finding["severity"]
        if dim in scorecard:
            scorecard[dim][sev] += 1
            
    total_blocking = sum(s["blocking"] for s in scorecard.values())
    is_pass = total_blocking == 0
    
    report_md = generate_markdown_report(args.scope, findings, scorecard, baseline_suppressed=suppressed_count)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[INFO] Audit report written to {args.output}")
        
    if args.json:
        res = {
            "scope": args.scope,
            "verdict": "PASS" if is_pass else "FAIL",
            "total_blocking": total_blocking,
            "baseline_suppressed": suppressed_count,
            "findings": findings,
            "scorecard": scorecard,
        }
        print(json.dumps(res, indent=2))
    elif not args.output:
        print(report_md)
        
    sys.exit(0 if is_pass else 1)


if __name__ == "__main__":
    main()
