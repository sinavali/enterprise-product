#!/usr/bin/env python3
"""
ep_quality.py — Enterprise Production-Readiness Quality Gate for EP-OS
Enforces mechanical quality invariants across monorepo codebases:
1. Mutating route idempotency (POST/PUT/PATCH endpoints require idempotency handling)
2. Graceful shutdown / drain linter (server entrypoints require SIGTERM/SIGINT handling & bounded drain)
3. Service runbook existence (deployable services require docs/runbooks/<service>.md)
4. Ephemeral integration test verification (banning SQLite in-memory fakes when real DB adapters required)
5. Architectural layer purity & test coverage (domain layer isolation & matching unit tests)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure repository root and scripts directory are on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in [REPO_ROOT, SCRIPTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from scripts.ep_runner import cmd_graph
    from scripts.ep_security import cmd_iac, cmd_license, cmd_security
    from scripts.ep_ops import cmd_slo
    from scripts.ep_doctor import run_doctor
    from scripts.ep_context import collect_files_from_diff, collect_files_from_surface
except ImportError:
    from ep_runner import cmd_graph  # type: ignore[import-not-found,no-redef]
    from ep_security import cmd_iac, cmd_license, cmd_security  # type: ignore[import-not-found,no-redef]
    from ep_ops import cmd_slo  # type: ignore[import-not-found,no-redef]
    from ep_doctor import run_doctor  # type: ignore[import-not-found,no-redef]
    from ep_context import collect_files_from_diff, collect_files_from_surface  # type: ignore[import-not-found,no-redef]



EXCLUDED_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", ".cache",
    ".venv", ".nx", "coverage", "__pycache__", ".ep", "templates",
}

CODE_EXTS = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".cs", ".php", ".java", ".kt"}


def _is_excluded(path: str) -> bool:
    norm = path.replace("\\", "/")
    parts = set(norm.split("/"))
    return bool(parts.intersection(EXCLUDED_DIRS))


# ------------------------------------------------------------------------------
# 1. Mutating Route Idempotency Checker
# ------------------------------------------------------------------------------

MUTATING_ROUTE_PATTERNS = [
    # TypeScript / JavaScript (Express, Nest, Fastify)
    (r"@(?:Post|Put|Patch)\s*\(", "NestJS / TS decorator"),
    (r"\b(?:router|app)\.(?:post|put|patch)\s*\(", "Express / Koa / Fastify route"),
    # Python (FastAPI, Flask)
    (r"@(?:router|app)\.(?:post|put|patch)\s*\(", "FastAPI route decorator"),
    (r"methods\s*=\s*\[[^\]]*['\"](?:POST|PUT|PATCH)['\"][^\]]*\]", "Flask mutating method"),
    # Go (Gin, Echo, Chi)
    (r"\.(?:POST|PUT|PATCH)\s*\(", "Go Gin/Echo mutating route"),
    # C# / ASP.NET
    (r"\[Http(?:Post|Put|Patch)(?:\([^)]*\))?\]", "ASP.NET Core HTTP attribute"),
    # Java / Kotlin Spring
    (r"@(?:Post|Put|Patch)Mapping\s*\(", "Spring MVC mapping annotation"),
]

IDEMPOTENCY_INDICATORS = [
    r"idempotent",
    r"idempotency",
    r"idempotency[-_]?key",
    r"x-idempotency-key",
    r"UseInterceptors\s*\([^)]*Idempotenc",
    r"IdempotencyMiddleware",
    r"RequireIdempotency",
    r"ep-idempotency-exempt",
]


def check_mutating_route_idempotency(root_dir: str = ".", files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    target_files = []

    if files is not None:
        target_files = [f for f in files if any(f.endswith(ext) for ext in CODE_EXTS) and os.path.isfile(os.path.join(root_dir, f))]
    else:
        for root, dirs, fnames in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            for fn in fnames:
                _, ext = os.path.splitext(fn)
                if ext in CODE_EXTS:
                    rel_p = os.path.relpath(os.path.join(root, fn), root_dir).replace("\\", "/")
                    target_files.append(rel_p)

    route_path_re = re.compile(r"(?:controllers?|handlers?|routes?|api|endpoints?)(?:[\\/]|[._\-])", re.IGNORECASE)
    idempotency_re = re.compile("|".join(IDEMPOTENCY_INDICATORS), re.IGNORECASE)
    class_idempotency_re = re.compile(r"(?:UseInterceptors\s*\([^)]*Idempotenc|@IdempotentController)", re.IGNORECASE)

    for rel_path in target_files:
        if _is_excluded(rel_path) or "test" in rel_path.lower() or "spec" in rel_path.lower():
            continue
        if not route_path_re.search(rel_path):
            continue

        full_path = os.path.join(root_dir, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue

        if "ep-idempotency-exempt" in content or class_idempotency_re.search(content):
            continue

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            for pat, desc in MUTATING_ROUTE_PATTERNS:
                if re.search(pat, line):
                    # Look backwards for decorators immediately preceding this route
                    prev_lines = []
                    for i in range(idx - 2, -1, -1):
                        l_strip = lines[i].strip()
                        if not l_strip:
                            continue
                        if l_strip.startswith("@"):
                            prev_lines.append(l_strip)
                        else:
                            break

                    # Look forward through the route header and start of handler
                    forward_lines = [lines[idx - 1].strip()]
                    for i in range(idx, min(len(lines), idx + 15)):
                        l_strip = lines[i].strip()
                        if not l_strip:
                            continue
                        if any(re.search(p, l_strip) for p, _ in MUTATING_ROUTE_PATTERNS) or re.search(r"@(?:Get|Delete|Options|Head|router\.(?:get|delete)|app\.(?:get|delete))\b", l_strip, re.IGNORECASE):
                            break
                        forward_lines.append(l_strip)
                        if l_strip == "}" or l_strip.startswith("return "):
                            break

                    route_ctx = "\n".join(prev_lines + forward_lines)
                    if not idempotency_re.search(route_ctx):
                        findings.append({
                            "rule": "QUALITY-MUTATING-ROUTE-IDEMPOTENCY",
                            "severity": "blocking",
                            "file": rel_path,
                            "line": idx,
                            "snippet": line.strip()[:100],
                            "description": f"Mutating endpoint without idempotency key handling or @Idempotent decorator ({desc}).",
                        })
                    break

    return findings




# ------------------------------------------------------------------------------
# 2. Graceful Shutdown & Drain Linter
# ------------------------------------------------------------------------------

SERVER_LISTEN_PATTERNS = [
    r"\.listen\s*\(",
    r"uvicorn\.run\s*\(",
    r"http\.ListenAndServe(?:TLS)?\s*\(",
    r"HttpServer::new\s*\(",
    r"app\.run\s*\(",
    r"WebApplication\.CreateBuilder\s*\(",
]

SHUTDOWN_SIGNAL_PATTERNS = [
    r"SIGTERM",
    r"SIGINT",
    r"signal\.Notify",
    r"signal\.signal",
    r"tokio::signal",
    r"ctrl_c\s*\(",
    r"lifespan\b",
    r"@asynccontextmanager",
    r"app\.on_event\s*\(\s*['\"]shutdown['\"]\s*\)",
    r"GracefulStop\s*\(",
    r"GracefulShutdown\b",
    r"graceful_shutdown\b",
    r"enableShutdownHooks\s*\(",
    r"IHostApplicationLifetime\b",
    r"registerShutdownHook\s*\(",
    r"(?:server|http_server|listener|app)\.close\s*\(",
    r"(?:server|http_server|listener|app)\.stop\s*\(",
    r"drain\s*\(",
    r"ep-shutdown-exempt",
]


def check_graceful_shutdown(root_dir: str = ".", files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    target_files = []

    entrypoint_re = re.compile(r"(?:^|[\\/])(main|server|index|app|Program)\.(?:ts|js|py|go|rs|cs)$", re.IGNORECASE)

    if files is not None:
        target_files = [f for f in files if entrypoint_re.search(f.replace("\\", "/")) and os.path.isfile(os.path.join(root_dir, f))]
    else:
        for root, dirs, fnames in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            for fn in fnames:
                full_p = os.path.join(root, fn)
                rel_p = os.path.relpath(full_p, root_dir).replace("\\", "/")
                if entrypoint_re.search(rel_p):
                    target_files.append(rel_p)

    listen_re = re.compile("|".join(SERVER_LISTEN_PATTERNS))
    shutdown_re = re.compile("|".join(SHUTDOWN_SIGNAL_PATTERNS))

    for rel_path in target_files:
        if _is_excluded(rel_path) or "test" in rel_path.lower():
            continue
        full_path = os.path.join(root_dir, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue

        if not listen_re.search(content):
            continue

        if not shutdown_re.search(content):
            lines = content.splitlines()
            listen_line = 1
            snippet = "server listen"
            for idx, line in enumerate(lines, start=1):
                if listen_re.search(line):
                    listen_line = idx
                    snippet = line.strip()[:100]
                    break
            findings.append({
                "rule": "QUALITY-GRACEFUL-SHUTDOWN-DRAIN",
                "severity": "blocking",
                "file": rel_path,
                "line": listen_line,
                "snippet": snippet,
                "description": "Server entrypoint listens for network traffic without handling SIGTERM/SIGINT signals or drain logic.",
            })

    return findings


# ------------------------------------------------------------------------------
# 3. Deployable Service Runbook Existence Checker
# ------------------------------------------------------------------------------

def check_service_runbooks(root_dir: str = ".", services: Optional[List[str]] = None, files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    deployable_roots = []
    for root, dirs, fnames in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        if "project.json" in fnames:
            rel_p = os.path.relpath(root, root_dir).replace("\\", "/")
            norm_parts = [p for p in rel_p.split("/") if p]
            if norm_parts and norm_parts[0] in {"services", "apps"}:
                pj_path = os.path.join(root, "project.json")
                try:
                    with open(pj_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    name = data.get("name", norm_parts[-1])
                    deployable_roots.append((name, rel_p, root))
                except Exception:
                    pass

    if files is not None:
        scoped_roots = []
        for name, rel_p, root in deployable_roots:
            prefix = rel_p.rstrip("/") + "/"
            if any(f.startswith(prefix) or f == rel_p for f in files):
                scoped_roots.append((name, rel_p, root))
        deployable_roots = scoped_roots
    elif services is not None:
        deployable_roots = [d for d in deployable_roots if d[0] in services or d[1] in services]

    for svc_name, rel_dir, full_dir in deployable_roots:
        runbook_candidates = [
            os.path.join(root_dir, "docs", "runbooks", f"{svc_name}.md"),
            os.path.join(root_dir, "docs", "runbooks", f"{svc_name}.runbook.md"),
            os.path.join(full_dir, "RUNBOOK.md"),
        ]
        if not any(os.path.isfile(c) for c in runbook_candidates):
            findings.append({
                "rule": "QUALITY-SERVICE-RUNBOOK-MISSING",
                "severity": "blocking",
                "file": f"{rel_dir}/project.json",
                "line": 1,
                "snippet": f"Service: {svc_name}",
                "description": f"Deployable service '{svc_name}' lacks an operational runbook in 'docs/runbooks/{svc_name}.md'.",
            })

    return findings


# ------------------------------------------------------------------------------
# 4. Ephemeral Integration Test Verification
# ------------------------------------------------------------------------------

BANNED_INTEGRATION_EMULATORS = [
    (r":memory:", "In-memory database (:memory:) banned for integration testing"),
    (r"sqlite3\.connect\(['\"]:memory:['\"]\)", "In-memory SQLite connection"),
    (r"UseSqlite\s*\(\s*['\"][^'\"]*['\"]\s*\)", "EF Core SQLite substitute"),
    (r"UseInMemoryDatabase\s*\(", "In-memory EF Core substitute banned for integration testing"),
    (r"createConnection\(\{[^}]*type:\s*['\"]sqlite['\"]", "TypeORM SQLite substitute"),
    (r"jdbc:h2:mem:", "In-memory H2 database emulator"),
]


def check_ephemeral_integration_tests(root_dir: str = ".", files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    target_files = []

    if files is not None:
        target_files = [f for f in files if "integration" in f.lower() and os.path.isfile(os.path.join(root_dir, f))]
    else:
        for root, dirs, fnames in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            for fn in fnames:
                full_p = os.path.join(root, fn)
                rel_p = os.path.relpath(full_p, root_dir).replace("\\", "/")
                if "integration" in rel_p.lower() and any(fn.endswith(ext) for ext in CODE_EXTS):
                    target_files.append(rel_p)

    for rel_path in target_files:
        if _is_excluded(rel_path):
            continue
        full_path = os.path.join(root_dir, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue

        if "ep-integration-exempt" in content:
            continue

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            for pat, desc in BANNED_INTEGRATION_EMULATORS:
                if re.search(pat, line):
                    findings.append({
                        "rule": "QUALITY-EPHEMERAL-TEST-FAKE-DB",
                        "severity": "blocking",
                        "file": rel_path,
                        "line": idx,
                        "snippet": line.strip()[:100],
                        "description": f"{desc}. Tier 1 requires real ephemeral containers (Testcontainers/Podman).",
                    })
                    break

    return findings


# ------------------------------------------------------------------------------
# 5. Architectural Layer Purity & Test Coverage Validator
# ------------------------------------------------------------------------------

DOMAIN_ORM_PATTERNS = [
    # Python ORMs
    r"(?:from|import)\s+(?:sqlalchemy|django\.db|peewee|tortoise)\b",
    # TypeScript / JavaScript ORMs
    r"from\s+['\"](?:typeorm|@prisma\/client|prisma|sequelize|mongoose|mikro-orm)['\"]",
    r"require\s*\(\s*['\"](?:typeorm|@prisma\/client|prisma|sequelize|mongoose|mikro-orm)['\"]\s*\)",
    # Go ORMs
    r"(?:gorm\.io\/gorm|github\.com\/jinzhu\/gorm|entgo\.io\/ent)",
    # Java / Kotlin JPA & Hibernate
    r"(?:org\.hibernate|javax\.persistence|jakarta\.persistence|org\.springframework\.data)",
    # C# EF Core & ADO
    r"(?:Microsoft\.EntityFrameworkCore|System\.Data\.SqlClient)",
    # Rust ORMs
    r"(?:diesel::|sea_orm::)",
]


def check_layer_coverage(root_dir: str = ".", files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    domain_files = []

    if files is not None:
        domain_files = [f for f in files if "/domain/" in f.replace("\\", "/") and any(f.endswith(ext) for ext in CODE_EXTS) and os.path.isfile(os.path.join(root_dir, f))]
    else:
        for root, dirs, fnames in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            norm_root = root.replace("\\", "/")
            if "/domain/" in norm_root or norm_root.endswith("/domain"):
                for fn in fnames:
                    _, ext = os.path.splitext(fn)
                    if ext in CODE_EXTS:
                        rel_p = os.path.relpath(os.path.join(root, fn), root_dir).replace("\\", "/")
                        domain_files.append(rel_p)

    for rel_path in domain_files:
        if _is_excluded(rel_path) or "test" in rel_path.lower() or "spec" in rel_path.lower():
            continue

        full_path = os.path.join(root_dir, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue

        # Check purity
        for pat in DOMAIN_ORM_PATTERNS:
            for idx, line in enumerate(content.splitlines(), start=1):
                if re.search(pat, line):
                    findings.append({
                        "rule": "QUALITY-DOMAIN-LAYER-PURITY",
                        "severity": "blocking",
                        "file": rel_path,
                        "line": idx,
                        "snippet": line.strip()[:100],
                        "description": "Domain layer imports ORM or persistence framework; violates DDD hexagonal purity.",
                    })
                    break

        # Check corresponding unit test existence
        base_name, _ = os.path.splitext(os.path.basename(rel_path))
        if base_name in {"index", "types", "__init__", "mod"}:
            continue

        dir_path = os.path.dirname(full_path)
        dir_name = os.path.dirname(rel_path)

        # Check co-located unit test candidates in the same directory
        co_located_patterns = [
            f"{base_name}.spec.",
            f"{base_name}.test.",
            f"{base_name}_test.",
            f"test_{base_name}.",
            f"{base_name}Test.",
            f"{base_name}Tests.",
        ]
        has_test = False
        try:
            for sibling in os.listdir(dir_path):
                if any(sibling.startswith(pat) for pat in co_located_patterns) and any(sibling.endswith(ext) for ext in CODE_EXTS):
                    has_test = True
                    break
        except Exception:
            pass

        if not has_test:
            # Search for test file in nearby tests directory
            search_dirs: List[str] = []
            cur = os.path.join(root_dir, dir_name)
            abs_root = os.path.abspath(root_dir)
            while cur and os.path.abspath(cur) != abs_root and os.path.abspath(cur) != os.path.dirname(abs_root):
                for cand_name in ["tests", "test", "spec"]:
                    cand = os.path.join(cur, cand_name)
                    if os.path.isdir(cand):
                        search_dirs.append(cand)
                    cand_sibling = os.path.join(os.path.dirname(cur), cand_name)
                    if os.path.isdir(cand_sibling):
                        search_dirs.append(cand_sibling)
                cur = os.path.dirname(cur)
            search_dirs.append(os.path.join(root_dir, "tests"))
            search_dirs.append(os.path.join(root_dir, "test"))

            for s_dir in search_dirs:
                if os.path.isdir(s_dir):
                    for t_root, _, t_files in os.walk(s_dir):
                        for tf in t_files:
                            if base_name in tf and any(tf.endswith(ext) for ext in CODE_EXTS):
                                has_test = True
                                break
                        if has_test:
                            break
                if has_test:
                    break

        if not has_test:
            findings.append({
                "rule": "QUALITY-DOMAIN-TEST-MISSING",
                "severity": "blocking",
                "file": rel_path,
                "line": 1,
                "snippet": f"Entity/Domain file: {base_name}",
                "description": f"Domain entity '{base_name}' lacks a corresponding unit test in tests/unit/.",
            })

    return findings


# ------------------------------------------------------------------------------
# Combined Quality Gate Execution & Verification Orchestrator
# ------------------------------------------------------------------------------

def run_all_quality_checks(root_dir: str = ".", files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    findings.extend(check_mutating_route_idempotency(root_dir, files=files))
    findings.extend(check_graceful_shutdown(root_dir, files=files))
    findings.extend(check_service_runbooks(root_dir, files=files))
    findings.extend(check_ephemeral_integration_tests(root_dir, files=files))
    findings.extend(check_layer_coverage(root_dir, files=files))
    return findings



def cmd_quality(args: argparse.Namespace) -> int:
    root_dir = getattr(args, "root", ".") or "."
    scoped_files: Optional[List[str]] = None

    if getattr(args, "surface", False):
        scoped_files = collect_files_from_surface(root_dir=root_dir)
    elif getattr(args, "diff", None):
        base = args.diff if isinstance(args.diff, str) else "origin/main"
        scoped_files = collect_files_from_diff(base=base, root_dir=root_dir)

    print("=== EP-OS Production-Readiness Quality Gate ===")
    if scoped_files is not None:
        mode_label = "Change Surface" if getattr(args, "surface", False) else "Git Diff"
        print(f"Scope: {mode_label} ({len(scoped_files)} scoped files)")
    else:
        print(f"Scope: Monorepo Root ({root_dir})")

    findings = run_all_quality_checks(root_dir, files=scoped_files)

    if getattr(args, "json", False):
        print(json.dumps(findings, indent=2))
        return 0 if not findings else 1

    if not findings:
        print("\n[PASS] Quality Gate: 100% compliant. All production-readiness invariants satisfied.")
        return 0

    print(f"\n[FAIL] Detected {len(findings)} quality invariant defect(s):", file=sys.stderr)
    for f in findings:
        print(f"  ❌ [{f['rule']}] {f['file']}:{f['line']}", file=sys.stderr)
        print(f"     Snippet: {f['snippet']}", file=sys.stderr)
        print(f"     Note: {f['description']}", file=sys.stderr)

    return 1


def run_enterprise_verify(a: argparse.Namespace) -> int:
    """Unified 12-Step Enterprise Gate Orchestrator for `ep verify`."""
    root_dir = getattr(a, "root", ".") or "."
    if getattr(a, "heal", False):
        run_doctor(root_dir=root_dir, heal=True)

    diff_mode = getattr(a, "diff", None)
    surface_mode = getattr(a, "surface", False)
    fast_base = "origin/main"
    if isinstance(diff_mode, str):
        fast_base = diff_mode

    print("=== 1. Verifying Nx Target Contracts ===")
    nx_res = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "verify-nx-targets.py"), "--root", root_dir], timeout=30).returncode

    print("\n=== 2. Linting AGENT.md Manifests ===")
    agent_res = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "verify-agent-manifests.py"), "--root", root_dir], timeout=30).returncode

    print("\n=== 3. Checking Open NC Item Expiration ===")
    nc_dir = os.path.join(root_dir, "docs/nc")
    if os.path.exists(nc_dir):
        nc_res = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "check-nc-items.py"), "--dir", nc_dir, "--max-age", "14"], timeout=30).returncode
    else:
        print("[INFO] No docs/nc directory found under root. 0 open NC items.")
        nc_res = 0

    print("\n=== 4. Checking Expand/Contract Database Migrations ===")
    try:
        from scripts.ep import cmd_migration, cmd_surface
    except ImportError:
        from ep import cmd_migration, cmd_surface  # type: ignore[import-not-found,no-redef]
    mig_res = cmd_migration(argparse.Namespace(dir=root_dir, diff=bool(diff_mode or surface_mode), base=fast_base))

    print("\n=== 5. Scanning for Hardcoded Secrets ===")
    sec_res = cmd_security(argparse.Namespace(action="scan", dir=root_dir, staged=False, diff=fast_base if diff_mode else None))

    print("\n=== 6. Checking Change Surface Compliance ===")
    surf_res = cmd_surface(argparse.Namespace(action="check-diff", file=None, surface_file=None, output=None, base=fast_base, strict=False))

    print("\n=== 7. Verifying Architectural Boundary Integrity ===")
    bound_res = cmd_graph(argparse.Namespace(root=root_dir, check_boundaries=True))

    print("\n=== 8. Scanning Dependency Licenses & Copyleft Contagion ===")
    lic_res = cmd_license(argparse.Namespace(action="check", root=root_dir))

    print("\n=== 9. Scanning Infrastructure as Code (IaC) Security ===")
    iac_res = cmd_iac(argparse.Namespace(action="verify", dir=root_dir))

    print("\n=== 10. Validating Service Level Objectives (SLO) Schema ===")
    slo_res = cmd_slo(argparse.Namespace(file=None, root=root_dir))

    print("\n=== 11. Verifying Enterprise Quality & Idempotency Invariants ===")
    qual_res = cmd_quality(argparse.Namespace(action="check", root=root_dir, diff=fast_base if diff_mode else None, surface=surface_mode, json=False))

    print("\n=== 12. Running Audit Diff Gate ===")
    audit_cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "audit-runner.py"), "--scope", root_dir, "--diff", fast_base]
    audit_res = subprocess.run(audit_cmd, timeout=300).returncode

    audit_res = subprocess.run(audit_cmd, timeout=300).returncode

    all_passed = (
        nx_res == 0 and agent_res == 0 and nc_res == 0 and mig_res == 0 and
        sec_res == 0 and surf_res == 0 and bound_res == 0 and lic_res == 0 and
        iac_res == 0 and slo_res == 0 and qual_res == 0 and audit_res == 0
    )
    if all_passed:
        print("\n[VERIFIED] All 12 Enterprise Verification Gates PASSED. Repository is production-ready.")
        return 0
    else:
        print("\n[FAILED] One or more enterprise verification gates failed.", file=sys.stderr)
        return 1
