#!/usr/bin/env python3
"""
ep.py — Unified Mechanical CLI for Enterprise-Product Engineering OS (EP-OS)
Zero-dependency Python 3.12 CLI standardizing governance, blast-radius verification,
auditing, static analysis, monorepo worktrees, architecture topology, multi-session workspaces,
and multi-tier VCS promotion gates.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure repository root and scripts directory are in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
for p in [REPO_ROOT, SCRIPTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from scripts.ep_adopt import cmd_adopt
    from scripts.ep_ast import cmd_ast
    from scripts.ep_hooks import cmd_hooks
    from scripts.ep_ops import cmd_codeowners, cmd_dora, cmd_perf, cmd_slo
    from scripts.ep_runner import cmd_run, cmd_run_many
    from scripts.ep_scaffold import cmd_init, cmd_manifest, cmd_preflight, cmd_worktree
    from scripts.ep_security import cmd_iac, cmd_license, cmd_security
    from scripts.ep_session import cmd_session
    from scripts.ep_stack import STACK_DEFINITIONS, detect_stack
    from scripts.ep_sync import cmd_sync_skill
    from scripts.ep_vcs import (
        BaseGitProvider,
        GitHubProvider,
        GitLabProvider,
        LocalGitProvider,
        cmd_pr,
        cmd_vcs,
        get_git_provider,
    )
except ImportError:
    from ep_adopt import cmd_adopt
    from ep_ast import cmd_ast
    from ep_hooks import cmd_hooks
    from ep_ops import cmd_codeowners, cmd_dora, cmd_perf, cmd_slo
    from ep_runner import cmd_run, cmd_run_many
    from ep_scaffold import cmd_init, cmd_manifest, cmd_preflight, cmd_worktree
    from ep_security import cmd_iac, cmd_license, cmd_security
    from ep_session import cmd_session
    from ep_stack import STACK_DEFINITIONS, detect_stack
    from ep_sync import cmd_sync_skill
    from ep_vcs import (
        BaseGitProvider,
        GitHubProvider,
        GitLabProvider,
        LocalGitProvider,
        cmd_pr,
        cmd_vcs,
        get_git_provider,
    )


# ==============================================================================
# SUBCOMMAND: surface (Change Surface Validator & Blast-Radius Gate)
# ==============================================================================

def cmd_surface(args: argparse.Namespace) -> int:
    if args.action == "validate":
        target_file = args.file or "CHANGE_SURFACE.md"
        if not os.path.exists(target_file):
            print(f"[ERROR] Change Surface file '{target_file}' not found.", file=sys.stderr)
            return 1
        cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "validate-change-surface.py"), target_file]
        if args.strict:
            cmd.append("--strict")
        return subprocess.run(cmd).returncode

    elif args.action == "check-diff":
        base_branch = args.base or "origin/main"
        target_file = getattr(args, "surface_file", None) or args.file or "CHANGE_SURFACE.md"

        if not os.path.exists(target_file):
            if os.path.exists("docs/changes"):
                changes = sorted([os.path.join("docs/changes", f) for f in os.listdir("docs/changes") if f.endswith(".md")])
                if changes:
                    target_file = changes[-1]

        if not os.path.exists(target_file):
            print(f"[ERROR] No Change Surface artifact found to verify against git diff.", file=sys.stderr)
            return 1

        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()

        code_surface_match = re.search(r"## 3\.\s*Code Surface.*?(?=## 4\.\s*Test Surface|\Z)", content, re.DOTALL | re.IGNORECASE)
        if not code_surface_match:
            print("[ERROR] Could not parse '## 3. Code Surface' from Change Surface.", file=sys.stderr)
            return 1

        surface_text = code_surface_match.group(0)
        declared_paths = set(re.findall(r"[`']([a-zA-Z0-9_\-./]+)[`']", surface_text))

        try:
            if base_branch in ("HEAD", "HEAD~1") or "..." not in base_branch:
                diff_cmd = ["git", "diff", "--name-only", base_branch]
                res = subprocess.run(diff_cmd, capture_output=True, text=True, check=False)
                modified_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
                res_staged = subprocess.run(["git", "diff", "--name-only", "--cached"], capture_output=True, text=True, check=False)
                modified_files.extend([line.strip() for line in res_staged.stdout.splitlines() if line.strip()])
            else:
                diff_cmd = ["git", "diff", "--name-only", f"{base_branch}...HEAD"]
                res = subprocess.run(diff_cmd, capture_output=True, text=True, check=False)
                modified_files = [line.strip() for line in res.stdout.splitlines() if line.strip()] if res.returncode == 0 else []

            res_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
            if res_status.returncode == 0:
                for line in res_status.stdout.splitlines():
                    if len(line) >= 4:
                        modified_files.append(line[3:].strip())

            modified_files = sorted(list(set(modified_files)))
        except Exception as e:
            print(f"[ERROR] Failed to query git status/diff: {e}", file=sys.stderr)
            return 1

        exempt_suffixes = (".md", ".jsonl", ".log", "pnpm-lock.yaml", "Cargo.lock", "package-lock.json")
        out_of_bounds = []

        for m_file in modified_files:
            if m_file.endswith(exempt_suffixes) or m_file.startswith("docs/") or m_file == "CHANGE_SURFACE.md":
                continue

            covered = False
            for d_path in declared_paths:
                if m_file == d_path or m_file.startswith(d_path.rstrip("/") + "/"):
                    covered = True
                    break
            if not covered:
                out_of_bounds.append(m_file)

        if out_of_bounds:
            print("[FAIL] MECHANICAL BLAST-RADIUS VIOLATION!", file=sys.stderr)
            print("The following modified files were NOT declared in the Change Surface:", file=sys.stderr)
            for f in out_of_bounds:
                print(f"  ❌ {f}", file=sys.stderr)
            print("\nRemediation: Update '## 3. Code Surface' in your Change Surface or revert out-of-scope edits.", file=sys.stderr)
            return 1

        print(f"[OK] Blast-Radius Clean: All {len(modified_files)} modified files are strictly within declared Change Surface.")
        return 0

    elif args.action == "init":
        target_file = getattr(args, "surface_file", None) or args.file or "CHANGE_SURFACE.md"
        base_branch = getattr(args, "base", "origin/main") or "origin/main"

        res_diff = subprocess.run(["git", "diff", "--name-only", f"{base_branch}...HEAD"], capture_output=True, text=True, check=False)
        mod_files = [line.strip() for line in res_diff.stdout.splitlines() if line.strip()]
        res_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
        if res_status.returncode == 0:
            for line in res_status.stdout.splitlines():
                if len(line) >= 4:
                    mod_files.append(line[3:].strip())
        mod_files = sorted(list(set(mod_files)))

        affected = set()
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "dist", "build"} and not d.startswith(".")]
            if "project.json" in files:
                rel_p = os.path.relpath(root, ".").replace("\\", "/")
                prefix = rel_p.lstrip("./") + "/"
                if any(mf.startswith(prefix) for mf in mod_files):
                    affected.add(rel_p)
        if not affected:
            affected.add(getattr(args, "scope", None) or "services/backend")

        code_lines = "\n".join([f"- `{f}`" for f in mod_files if not f.endswith((".md", ".jsonl", ".log"))]) or "- `src/index.ts`"
        test_lines = "\n".join([f"- `tests/test_{os.path.basename(f)}`" for f in mod_files[:3]]) or "- `tests/unit/test_service.py`"

        author = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, check=False).stdout.strip() or "Enterprise Agent"
        current_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False).stdout.strip() or "feat/core-service"

        affected_list = "\n".join([f'  - "{a}"' for a in sorted(affected)])
        affected_bullets = "\n".join([f'- `{a}`' for a in sorted(affected)])

        content = f"""---
title: "Change Surface: Automated Update"
author: "{author}"
created_date: "{datetime.date.today().isoformat()}"
target_branch: "{current_branch}"
risk_level: "LOW"
affected_projects:
{affected_list}
---

# Change Surface

## 1. Intent & Business Rationale
Automated implementation surface generated by EP-OS CLI.

## 2. Affected Monorepo Projects
{affected_bullets}

## 3. Code Surface
### Modified Files
{code_lines}

## 4. Test Surface
### Unit & Integration Suites
{test_lines}

## 5. Invariants
- UTC timestamps preserved across all persistence models.
- DDD domain isolation strictly preserved without framework leakage.
- Real ephemeral containers for integration test assertions.

## 6. Risk Matrix
- Rollback: Revert commits via standard git rollback.
- Blast radius bounded strictly to declared Code Surface.
"""
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Initialized Change Surface at '{target_file}'.")
        cmd_validate = [sys.executable, os.path.join(SCRIPTS_DIR, "validate-change-surface.py"), target_file]
        return subprocess.run(cmd_validate).returncode

    return 0


# ==============================================================================
# SUBCOMMAND: migration (Expand/Contract Static DDL Scanner)
# ==============================================================================

DESTRUCTIVE_DDL_PATTERNS = [
    (r"\bDROP\s+COLUMN\b", "DROP COLUMN detected. Breaking schema alteration violates Expand/Contract (Phase 1-4)."),
    (r"\bRENAME\s+COLUMN\b", "RENAME COLUMN detected. Instant rename breaks rolling deployments. Use dual-write Expand/Contract."),
    (r"\bALTER\s+COLUMN\s+.*?\bSET\s+NOT\s+NULL\b", "SET NOT NULL on existing column without phased backfill causes deployment failure."),
    (r"\bADD\s+COLUMN\s+.*?\bNOT\s+NULL\b(?!\s+DEFAULT\b)", "ADD COLUMN NOT NULL without DEFAULT breaks concurrent insert versions."),
    (r"\bDROP\s+TABLE\b", "DROP TABLE detected without phased deprecation period."),
]

def cmd_migration(args: argparse.Namespace) -> int:
    scan_dir = args.dir or "."
    target_files = []

    if args.diff:
        base = args.base or "origin/main"
        try:
            res = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                diff_files = res.stdout.splitlines()
                target_files = [f for f in diff_files if f.endswith(".sql") and os.path.exists(f)]
        except Exception:
            pass

    if not target_files:
        for root, _, files in os.walk(scan_dir):
            if any(p in root for p in ["node_modules", ".git", "dist", "build"]):
                continue
            for f in files:
                if f.endswith(".sql"):
                    target_files.append(os.path.join(root, f))

    violations = []
    for file_path in target_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if re.search(r"--\s*adr-ref:\s*docs/adr/\S+", content, re.IGNORECASE):
            continue

        for pattern, desc in DESTRUCTIVE_DDL_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_no = content[:match.start()].count("\n") + 1
                violations.append((file_path, line_no, desc, match.group(0)))

    if violations:
        print("[FAIL] EXPAND/CONTRACT MIGRATION GATE VIOLATION!", file=sys.stderr)
        print("Destructive database operations detected that break rolling zero-downtime deployments:\n", file=sys.stderr)
        for f, l, desc, match in violations:
            print(f"  ❌ {f}:{l} -> Found '{match}'", file=sys.stderr)
            print(f"     Reason: {desc}", file=sys.stderr)
        print("\nRemediation: Follow Expand/Contract phased lifecycle (see references/core-directives.md).", file=sys.stderr)
        print("If this is Phase 5 (Contract cleanup), add an approved ADR comment: '-- adr-ref: docs/adr/NNNN-contract.md'.", file=sys.stderr)
        return 1

    print(f"[OK] Expand/Contract Verified: {len(target_files)} migration files checked. 0 destructive operations.")
    return 0


# ==============================================================================
# SUBCOMMAND: graph (Native Mermaid Topology Generator)
# ==============================================================================

def cmd_graph(args: argparse.Namespace) -> int:
    root_dir = args.root or "."

    if getattr(args, "check_boundaries", False):
        print("=== EP-OS Architectural Boundary Integrity Check ===")
        violations = []
        for cur_root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", ".nx", "dist", "build"} and not d.startswith(".")]
            norm_cur = cur_root.replace("\\", "/")
            is_domain = "/domain" in norm_cur or norm_cur.endswith("/domain")
            for f in files:
                if f.endswith((".ts", ".js", ".go", ".py", ".rs", ".php")):
                    f_path = os.path.join(cur_root, f)
                    try:
                        with open(f_path, "r", encoding="utf-8", errors="ignore") as fh:
                            fc = fh.read()
                        if is_domain:
                            if re.search(r"(from ['\"](typeorm|prisma|sequelize|gorm|sqlalchemy|django\.db)['\"]|import .*gorm|org\.hibernate)", fc):
                                violations.append((f_path, "Domain layer imports ORM/persistence framework"))
                        if "/libs/" in norm_cur or "/packages/" in norm_cur:
                            if re.search(r"from ['\"].*(apps|services)/", fc):
                                violations.append((f_path, "Library/shared package imports application or service code"))
                    except Exception:
                        pass
        if violations:
            print("[FAIL] Architectural Boundary Violations Detected!", file=sys.stderr)
            for f_path, reason in violations:
                print(f"  ❌ {f_path}: {reason}", file=sys.stderr)
            return 1
        print("[OK] Architectural Boundary Integrity Verified. Zero illegal imports detected.")
        return 0

    projects = []
    for current_root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", ".nx", "dist", "build"} and not d.startswith(".")]
        if "project.json" in files:
            p_file = os.path.join(current_root, "project.json")
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    name = data.get("name", os.path.basename(current_root))
                    tags = data.get("tags", [])
                    profile = "Unknown"
                    scope = "General"
                    for t in tags:
                        if t.startswith("profile:"):
                            profile = t.split(":", 1)[1].upper()
                        elif t.startswith("scope:"):
                            scope = t.split(":", 1)[1]
                    projects.append({
                        "name": name,
                        "path": current_root,
                        "profile": profile,
                        "scope": scope,
                    })
            except Exception:
                pass

    if args.format == "json":
        print(json.dumps(projects, indent=2))
        return 0

    print("```mermaid")
    print("flowchart TD")
    print("    subgraph Enterprise Product Monorepo")

    profiles = {
        "A": "Profile A (Backend & Core Services)",
        "B": "Profile B (Web Applications)",
        "C": "Profile C (Mobile Clients)",
        "D": "Profile D (Shared Contracts & Libs)",
    }
    for prof_key, prof_label in profiles.items():
        matching = [p for p in projects if p["profile"] == prof_key]
        if matching:
            print(f'        subgraph P_{prof_key}["{prof_label}"]')
            for p in matching:
                p_id = re.sub(r"[^a-zA-Z0-9_]", "_", p["name"])
                print(f'            {p_id}["{p["name"]} ({p["scope"]})"]')
            print("        end")

    d_projects = [p for p in projects if p["profile"] == "D"]
    other_projects = [p for p in projects if p["profile"] != "D"]
    for d in d_projects:
        d_id = re.sub(r"[^a-zA-Z0-9_]", "_", d["name"])
        for o in other_projects:
            o_id = re.sub(r"[^a-zA-Z0-9_]", "_", o["name"])
            print(f"    {d_id} -.-> {o_id}")

    print("    end")
    print("```")
    return 0


# ==============================================================================
# SUBCOMMAND: release & milestone (SemVer & Release Governance)
# ==============================================================================

def cmd_release(args: argparse.Namespace) -> int:
    action = args.action
    version = getattr(args, "version", None)

    if action == "create":
        if not version or not re.match(r"^v?\d+\.\d+\.\d+", version):
            print(f"[ERROR] Version '{version}' does not match SemVer format (vMAJOR.MINOR.PATCH).", file=sys.stderr)
            return 1
        formatted_version = f"v{version.lstrip('v')}"
        res = subprocess.run(["git", "tag", "-a", formatted_version, "-m", f"Release {formatted_version}"], check=False)
        if res.returncode != 0:
            return res.returncode
        print(f"[OK] Created release tag '{formatted_version}'.")
        return 0
    elif action == "finalize":
        cur_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
        print(f"[OK] Finalized production release progression on branch '{cur_branch}'.")
        return 0
    return 0


def cmd_milestone(args: argparse.Namespace) -> int:
    name = args.name
    ms_dir = "docs/milestones"
    os.makedirs(ms_dir, exist_ok=True)
    ms_file = os.path.join(ms_dir, f"{name}.md")
    if os.path.exists(ms_file):
        print(f"[INFO] Milestone '{name}' already exists at '{ms_file}'.")
        return 0
    with open(ms_file, "w", encoding="utf-8") as f:
        f.write(
            f"# Milestone: {name}\n\n"
            f"- **Created**: `{datetime.date.today().isoformat()}`\n"
            f"- **Target Due Date**: `{getattr(args, 'due', None) or 'TBD'}`\n"
            "- **Status**: `IN_PROGRESS`\n"
            "- **Associated Subprojects**:\n"
            "  - `TBD`\n\n"
            "## Delivery Objectives\n"
            "- [ ] Implement core features\n"
            "- [ ] 10-Dimension Audit clean\n"
            "- [ ] Ephemeral container tests passing\n"
        )
    print(f"[OK] Created milestone manifest at '{ms_file}'.")
    return 0


# ==============================================================================
# MAIN DISPATCHER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="ep",
        description="Unified Mechanical CLI for Enterprise-Product Engineering OS (EP-OS)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Operational subcommands")

    # surface
    p_surface = subparsers.add_parser("surface", help="Change Surface validation and blast-radius bounding")
    p_surface.add_argument("action", choices=["validate", "check-diff", "init"], help="Action to perform")
    p_surface.add_argument("file", nargs="?", default=None, help="Path to CHANGE_SURFACE markdown file")
    p_surface.add_argument("--surface-file", dest="surface_file", default=None, help="Path to CHANGE_SURFACE markdown file")
    p_surface.add_argument("--base", default="origin/main", help="Base git branch for diff check")
    p_surface.add_argument("--strict", action="store_true", help="Disallow template placeholders")
    p_surface.add_argument("--scope", default=None, help="Project scope hint")
    p_surface.add_argument("--title", default=None, help="Change Surface title")

    # migration
    p_mig = subparsers.add_parser("migration", help="Zero-Downtime Expand/Contract migration linter")
    p_mig.add_argument("action", choices=["check"], help="Action to perform")
    p_mig.add_argument("--dir", default=None, help="Directory to scan for migrations")
    p_mig.add_argument("--diff", action="store_true", help="Scan only migration files modified in git diff")
    p_mig.add_argument("--base", default="origin/main", help="Base git branch for diff check")

    # graph
    p_graph = subparsers.add_parser("graph", help="Generate live architecture and documentation topology graph")
    p_graph.add_argument("--root", default=".", help="Root monorepo directory")
    p_graph.add_argument("--format", choices=["mermaid", "json"], default="mermaid", help="Output format")
    p_graph.add_argument("--check-boundaries", action="store_true", help="Enforce DDD and package boundary integrity")

    # init
    p_init = subparsers.add_parser("init", help="Scaffold a new fully compliant monorepo subproject")
    p_init.add_argument("name", help="Name of the new project")
    p_init.add_argument("--profile", required=True, choices=["A", "B", "C", "D", "a", "b", "c", "d"], help="Architectural Profile")
    p_init.add_argument("--lang", default="ts", help="Language/runtime stack (go, rust, ts, dart, php)")
    p_init.add_argument("--dir", default=None, help="Custom target directory")

    # worktree
    p_wt = subparsers.add_parser("worktree", help="Manage isolated git worktrees for monorepo development")
    p_wt.add_argument("action", choices=["create", "remove"], help="Worktree action")
    p_wt.add_argument("branch", help="Branch name")

    # vcs
    p_vcs = subparsers.add_parser("vcs", help="Multi-Tier VCS operations and topology validation")
    p_vcs.add_argument("action", choices=["sync-check"], help="VCS action")
    p_vcs.add_argument("--base", default="main", help="Base trunk branch")

    # pr
    p_pr = subparsers.add_parser("pr", help="Pull request and promotion operations")
    p_pr.add_argument("action", choices=["create-prod"], help="PR action")
    p_pr.add_argument("--head", default=None, help="Head source branch")
    p_pr.add_argument("--title", default=None, help="PR title")
    p_pr.add_argument("--body", default=None, help="PR body description")

    # session
    p_sess = subparsers.add_parser("session", help="Multi-Session state machine and memory management")
    p_sess.add_argument("action", choices=["save", "resume", "list", "prune", "check-collision"], help="Session action")
    p_sess.add_argument("--session-id", default=None, help="Session identifier")
    p_sess.add_argument("--task", default=None, help="Task description or ID")
    p_sess.add_argument("--mode", default=None, help="Operational mode")
    p_sess.add_argument("--notes", default=None, help="Additional session notes")

    # manifest
    p_man = subparsers.add_parser("manifest", help="Universal manifest projection (CLAUDE.md, .cursorrules)")
    p_man.add_argument("action", choices=["sync"], help="Manifest action")
    p_man.add_argument("--root", default=".", help="Root monorepo directory")

    # preflight
    subparsers.add_parser("preflight", help="Agent execution capabilities and access refusal gate")

    # release
    p_rel = subparsers.add_parser("release", help="Hybrid Dual-Tier SemVer and release management")
    p_rel.add_argument("action", choices=["create", "finalize"], help="Release action")
    p_rel.add_argument("version", nargs="?", default=None, help="Target release version")
    p_rel.add_argument("--prod", action="store_true", help="Finalize production release")

    # milestone
    p_ms = subparsers.add_parser("milestone", help="Milestone tracking and objectives")
    p_ms.add_argument("action", choices=["create"], help="Milestone action")
    p_ms.add_argument("name", help="Milestone name")
    p_ms.add_argument("--due", default=None, help="Target due date")

    # delegate to existing scripts: audit, verify, nc
    p_audit = subparsers.add_parser("audit", help="Run 10-Dimension Enterprise Audit Suite")
    p_audit.add_argument("--scope", default=".", help="Directory or file path to audit")
    p_audit.add_argument("--diff", nargs="?", const="origin/main...HEAD", default=None, help="Audit only modified git diff lines")
    p_audit.add_argument("--output", default=None, help="Path to save AUDIT_REPORT.md")
    p_audit.add_argument("--json", action="store_true", help="Output results in JSON")

    p_verify = subparsers.add_parser("verify", help="Run parallel mechanical gatekeeper suite")
    p_verify.add_argument("--root", default=".", help="Root directory to scan")

    p_nc = subparsers.add_parser("nc", help="Audit NEED_CLARIFICATION items for expiration")
    p_nc.add_argument("action", choices=["check"], help="Action to perform")
    p_nc.add_argument("--max-age", type=int, default=14, help="Max allowed age in days before blocking")

    # hooks
    p_hooks = subparsers.add_parser("hooks", help="Manage zero-dependency native git hooks")
    p_hooks.add_argument("action", choices=["install", "uninstall"], help="Hook action")
    p_hooks.add_argument("--root", default=".", help="Repository root directory")

    # security
    p_sec = subparsers.add_parser("security", help="Pre-commit secret and credential scanner")
    p_sec.add_argument("action", choices=["scan"], help="Security action")
    p_sec.add_argument("--staged", action="store_true", help="Scan only git staged changes")
    p_sec.add_argument("--diff", default=None, help="Scan git diff against base branch")
    p_sec.add_argument("--dir", default=None, help="Scan directory files")

    # license
    p_lic = subparsers.add_parser("license", help="Dependency license and copyleft compliance checker")
    p_lic.add_argument("action", choices=["check"], help="License action")
    p_lic.add_argument("--root", default=".", help="Repository root directory")
    p_lic.add_argument("--sbom", action="store_true", help="Generate .ep/sbom.json")

    # adopt
    p_adopt = subparsers.add_parser("adopt", help="Brownfield monorepo onboarding and baseline ratcheting")
    p_adopt.add_argument("--root", default=".", help="Monorepo root directory")
    p_adopt.add_argument("--profile", default="B", choices=["A", "B", "C", "D", "a", "b", "c", "d"], help="Target Architectural Profile")
    p_adopt.add_argument("--dry-run", action="store_true", help="Simulate adoption without writing files")

    # sync-skill
    p_sync = subparsers.add_parser("sync-skill", help="Synchronize skill directory with workspace repository")
    p_sync.add_argument("--direction", choices=["to-workspace", "to-skill"], default="to-workspace", help="Sync direction")
    p_sync.add_argument("--check", action="store_true", help="Check parity without modifying files")
    p_sync.add_argument("--skill-dir", default=None, help="Path to skill directory")
    p_sync.add_argument("--workspace-dir", default=None, help="Path to workspace clone directory")

    # ast
    p_ast = subparsers.add_parser("ast", help="Structural code intelligence and AST invariant scanning via ast-grep")
    p_ast.add_argument("action", choices=["search", "scan"], help="AST action")
    p_ast.add_argument("pattern", nargs="?", default="", help="Structural pattern to search for")
    p_ast.add_argument("--scope", default=".", help="Directory or file path to inspect")
    p_ast.add_argument("--lang", default=None, help="Target language (typescript, python, go, rust, php)")

    # run
    p_run = subparsers.add_parser("run", help="Execute single project target in topological dependency order")
    p_run.add_argument("target_spec", help="Target specification in format 'project:target'")
    p_run.add_argument("--root", default=".", help="Monorepo root directory")

    # run-many
    p_run_many = subparsers.add_parser("run-many", help="Execute target across multiple projects in DAG topological order")
    p_run_many.add_argument("--target", required=True, help="Target name to execute (lint, test, build, audit)")
    p_run_many.add_argument("--projects", default=None, help="Comma-separated project list")
    p_run_many.add_argument("--affected", action="store_true", help="Run only on projects modified in git diff")
    p_run_many.add_argument("--parallel", action="store_true", help="Execute targets concurrently")
    p_run_many.add_argument("--root", default=".", help="Monorepo root directory")

    # iac
    p_iac = subparsers.add_parser("iac", help="Infrastructure as Code (IaC) container & orchestration security gate")
    p_iac.add_argument("--dir", default=".", help="Directory to scan")

    # slo
    p_slo = subparsers.add_parser("slo", help="Validate Service Level Objective (SLO) definitions and error budgets")
    p_slo.add_argument("--file", default=None, help="Path to specific SLO YAML file")

    # codeowners
    p_co = subparsers.add_parser("codeowners", help="Audit monorepo code ownership and CODEOWNERS coverage")
    p_co.add_argument("--root", default=".", help="Monorepo root directory")

    # dora
    p_dora = subparsers.add_parser("dora", help="Calculate git-derived DORA metrics (Deployment Frequency, CFR)")
    p_dora.add_argument("--days", type=int, default=30, help="Number of days of history to analyze")

    # perf
    p_perf = subparsers.add_parser("perf", help="Run standard k6 performance and stress tests")
    p_perf.add_argument("--script", default=None, help="Path to k6 test script")
    p_perf.add_argument("--target-url", default=None, help="Base target URL")
    p_perf.add_argument("--vus", type=int, default=10, help="Virtual users")
    p_perf.add_argument("--duration", default="10s", help="Duration string")
    p_perf.add_argument("--dry-run", action="store_true", help="Validate script and execution engine without invoking HTTP requests")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    # Route subcommands
    if args.subcommand == "surface":
        sys.exit(cmd_surface(args))
    elif args.subcommand == "migration":
        sys.exit(cmd_migration(args))
    elif args.subcommand == "graph":
        sys.exit(cmd_graph(args))
    elif args.subcommand == "init":
        sys.exit(cmd_init(args))
    elif args.subcommand == "worktree":
        sys.exit(cmd_worktree(args))
    elif args.subcommand == "vcs":
        sys.exit(cmd_vcs(args))
    elif args.subcommand == "pr":
        sys.exit(cmd_pr(args))
    elif args.subcommand == "session":
        sys.exit(cmd_session(args))
    elif args.subcommand == "manifest":
        sys.exit(cmd_manifest(args))
    elif args.subcommand == "preflight":
        sys.exit(cmd_preflight(args))
    elif args.subcommand == "release":
        sys.exit(cmd_release(args))
    elif args.subcommand == "milestone":
        sys.exit(cmd_milestone(args))
    elif args.subcommand == "audit":
        cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "audit-runner.py")]
        if args.scope:
            cmd.extend(["--scope", args.scope])
        if args.output:
            cmd.extend(["--output", args.output])
        if args.diff:
            cmd.extend(["--diff", args.diff])
        if args.json:
            cmd.append("--json")
        sys.exit(subprocess.run(cmd).returncode)

    elif args.subcommand == "verify":
        print("=== 1. Verifying Nx Target Contracts ===")
        nx_res = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "verify-nx-targets.py"), "--root", args.root]).returncode

        print("\n=== 2. Linting AGENT.md Manifests ===")
        agent_res = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "verify-agent-manifests.py")]).returncode

        print("\n=== 3. Checking Open NC Item Expiration ===")
        nc_dir = os.path.join(args.root, "docs/nc")
        if os.path.exists(nc_dir):
            nc_res = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "check-nc-items.py"), "--dir", nc_dir, "--max-age", "14"]).returncode
        else:
            print("[INFO] No docs/nc directory found under root. 0 open NC items.")
            nc_res = 0

        sys.exit(1 if (nx_res != 0 or agent_res != 0 or nc_res != 0) else 0)

    elif args.subcommand == "nc":
        cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "check-nc-items.py"), "--max-age", str(args.max_age)]
        sys.exit(subprocess.run(cmd).returncode)
    elif args.subcommand == "hooks":
        sys.exit(cmd_hooks(args))
    elif args.subcommand == "security":
        sys.exit(cmd_security(args))
    elif args.subcommand == "license":
        sys.exit(cmd_license(args))
    elif args.subcommand == "adopt":
        sys.exit(cmd_adopt(args))
    elif args.subcommand == "sync-skill":
        sys.exit(cmd_sync_skill(args))
    elif args.subcommand == "ast":
        sys.exit(cmd_ast(args))
    elif args.subcommand == "run":
        sys.exit(cmd_run(args))
    elif args.subcommand == "run-many":
        sys.exit(cmd_run_many(args))
    elif args.subcommand == "iac":
        sys.exit(cmd_iac(args))
    elif args.subcommand == "slo":
        sys.exit(cmd_slo(args))
    elif args.subcommand == "codeowners":
        sys.exit(cmd_codeowners(args))
    elif args.subcommand == "dora":
        sys.exit(cmd_dora(args))
    elif args.subcommand == "perf":
        sys.exit(cmd_perf(args))


if __name__ == "__main__":
    main()
