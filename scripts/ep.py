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
    from scripts.ep_context import cmd_pack
    from scripts.ep_doctor import cmd_ci, cmd_doctor, cmd_skill, run_doctor
    from scripts.ep_hooks import cmd_hooks
    from scripts.ep_ops import cmd_codeowners, cmd_container, cmd_dora, cmd_finops, cmd_perf, cmd_slo, cmd_telemetry
    from scripts.ep_quality import cmd_quality, run_enterprise_verify
    from scripts.ep_runner import cmd_graph, cmd_run, cmd_run_many
    from scripts.ep_scaffold import archive_change_surface, cmd_init, cmd_manifest, cmd_preflight, cmd_worktree, is_surface_unpopulated
    from scripts.ep_security import cmd_iac, cmd_license, cmd_policy, cmd_security
    from scripts.ep_session import cmd_session
    from scripts.ep_stack import STACK_DEFINITIONS, detect_stack
    from scripts.ep_sync import cmd_sync_skill
    from scripts.ep_tooling import cmd_chaos, cmd_contract, cmd_sbom
    from scripts.ep_vcs import BaseGitProvider, GitHubProvider, GitLabProvider, LocalGitProvider, cmd_pr, cmd_vcs, get_git_provider
except ImportError:
    from ep_adopt import cmd_adopt  # type: ignore[import-not-found,no-redef]
    from ep_ast import cmd_ast  # type: ignore[import-not-found,no-redef]
    from ep_context import cmd_pack  # type: ignore[import-not-found,no-redef]
    from ep_doctor import cmd_ci, cmd_doctor, cmd_skill, run_doctor  # type: ignore[import-not-found,no-redef]
    from ep_hooks import cmd_hooks  # type: ignore[import-not-found,no-redef]
    from ep_ops import cmd_codeowners, cmd_container, cmd_dora, cmd_finops, cmd_perf, cmd_slo, cmd_telemetry  # type: ignore[import-not-found,no-redef]
    from ep_quality import cmd_quality, run_enterprise_verify  # type: ignore[import-not-found,no-redef]
    from ep_runner import cmd_graph, cmd_run, cmd_run_many  # type: ignore[import-not-found,no-redef]
    from ep_scaffold import archive_change_surface, cmd_init, cmd_manifest, cmd_preflight, cmd_worktree, is_surface_unpopulated  # type: ignore[import-not-found,no-redef]
    from ep_security import cmd_iac, cmd_license, cmd_policy, cmd_security  # type: ignore[import-not-found,no-redef]
    from ep_session import cmd_session  # type: ignore[import-not-found,no-redef]
    from ep_stack import STACK_DEFINITIONS, detect_stack  # type: ignore[import-not-found,no-redef]
    from ep_sync import cmd_sync_skill  # type: ignore[import-not-found,no-redef]
    from ep_tooling import cmd_chaos, cmd_contract, cmd_sbom  # type: ignore[import-not-found,no-redef]
    from ep_vcs import BaseGitProvider, GitHubProvider, GitLabProvider, LocalGitProvider, cmd_pr, cmd_vcs, get_git_provider  # type: ignore[import-not-found,no-redef]

def _resolve_change_surface(target_file: str) -> str:
    needs_fallback = False
    if not os.path.exists(target_file):
        needs_fallback = True
    elif target_file == "CHANGE_SURFACE.md" or os.path.basename(target_file) == "CHANGE_SURFACE.md":
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                c = f.read()
            if is_surface_unpopulated(c):
                needs_fallback = True
        except Exception:
            needs_fallback = True
    if needs_fallback and os.path.exists("docs/changes"):
        changes = sorted(
            [os.path.join("docs/changes", f) for f in os.listdir("docs/changes") if f.endswith(".md")],
            key=lambda p: (os.path.getmtime(p), p),
        )
        if changes:
            return changes[-1]
    return target_file


# --- Subcommand: surface (Change Surface Validator & Blast-Radius Gate) ---
def cmd_surface(args: argparse.Namespace) -> int:
    if args.action == "validate":
        target_file = _resolve_change_surface(getattr(args, "output", None) or getattr(args, "surface_file", None) or args.file or "CHANGE_SURFACE.md")
        if not os.path.exists(target_file):
            print(f"[ERROR] Change Surface file '{target_file}' not found.", file=sys.stderr)
            return 1
        cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "validate-change-surface.py"), target_file]
        if args.strict:
            cmd.append("--strict")
        return subprocess.run(cmd, timeout=30).returncode

    elif args.action == "check-diff":
        base_branch = args.base or "origin/main"
        target_file = _resolve_change_surface(getattr(args, "output", None) or getattr(args, "surface_file", None) or args.file or "CHANGE_SURFACE.md")

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
        declared_paths = set(re.findall(r"[`']([a-zA-Z0-9_\-./\[\]]+)[`']", surface_text))
        if os.path.exists("docs/changes"):
            for arc in os.listdir("docs/changes"):
                if arc.endswith(".md"):
                    try:
                        with open(os.path.join("docs/changes", arc), "r", encoding="utf-8") as af:
                            m = re.search(r"## 3\.\s*Code Surface.*?(?=## 4\.\s*Test Surface|\Z)", af.read(), re.DOTALL | re.IGNORECASE)
                            if m:
                                declared_paths.update(re.findall(r"[`']([a-zA-Z0-9_\-./\[\]]+)[`']", m.group(0)))
                    except Exception:
                        pass

        try:
            if "..." in base_branch or base_branch in ("HEAD", "HEAD~1"):
                diff_cmd = ["git", "diff", "--name-only", base_branch]
            else:
                diff_cmd = ["git", "diff", "--name-only", f"{base_branch}...HEAD"]
            res = subprocess.run(diff_cmd, capture_output=True, text=True, check=False, timeout=30)
            if res.returncode != 0:
                print(f"[ERROR] git diff failed on target '{' '.join(diff_cmd)}': {res.stderr.strip()}", file=sys.stderr)
                return 1
            modified_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            res_staged = subprocess.run(["git", "diff", "--name-only", "--cached"], capture_output=True, text=True, check=False, timeout=30)
            modified_files.extend([line.strip() for line in res_staged.stdout.splitlines() if line.strip()])

            res_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False, timeout=30)
            if res_status.returncode == 0:
                for line in res_status.stdout.splitlines():
                    if len(line) >= 4:
                        raw_path = line[3:].strip()
                        if " -> " in raw_path:
                            raw_path = raw_path.split(" -> ")[1].strip()
                        modified_files.append(raw_path)

            modified_files = sorted(list(set(modified_files)))
        except Exception as e:
            print(f"[ERROR] Failed to query git status/diff: {e}", file=sys.stderr)
            return 1

        exempt_suffixes = (".md", ".jsonl", ".log", "pnpm-lock.yaml", "Cargo.lock", "package-lock.json")
        out_of_bounds = []

        for m_file in modified_files:
            if m_file.endswith(exempt_suffixes) or m_file.startswith(("docs/", ".ep/", ".git/")) or m_file in ("CHANGE_SURFACE.md", ".gitignore"):
                continue

            covered = False
            for d_path in declared_paths:
                if m_file == d_path or m_file.startswith(d_path.rstrip("/") + "/") or (m_file.endswith("/") and d_path.startswith(m_file)):
                    covered = True
                    break
            if not covered:
                out_of_bounds.append(m_file)

        if out_of_bounds:
            print("[FAIL] MECHANICAL BLAST-RADIUS VIOLATION!", file=sys.stderr)
            print("The following modified files were NOT declared in the Change Surface:", file=sys.stderr)
            for oob_file in out_of_bounds:
                print(f"  ❌ {oob_file}", file=sys.stderr)
            print("\nRemediation: Update '## 3. Code Surface' in your Change Surface or revert out-of-scope edits.", file=sys.stderr)
            return 1

        print(f"[OK] Blast-Radius Clean: All {len(modified_files)} modified files are strictly within declared Change Surface.")
        return 0

    elif args.action == "archive":
        target_file = getattr(args, "output", None) or getattr(args, "surface_file", None) or args.file or "CHANGE_SURFACE.md"
        changes_dir = getattr(args, "changes_dir", "docs/changes") or "docs/changes"
        no_reset = getattr(args, "no_reset", False)
        ok, arc_res = archive_change_surface(target_file, changes_dir=changes_dir, reset_root=not no_reset)
        if not ok:
            print(f"[WARN] Change Surface archival: {arc_res}")
            return 0
        print(f"[OK] Change Surface archived to '{arc_res}' and active surface reset.")
        return 0

    elif args.action == "init":
        target_file = getattr(args, "output", None) or getattr(args, "surface_file", None) or args.file or "CHANGE_SURFACE.md"
        base_branch = getattr(args, "base", "origin/main") or "origin/main"

        if os.path.exists(target_file):
            ok_arc, arc_path = archive_change_surface(target_file, reset_root=False)
            if ok_arc:
                print(f"[INFO] Auto-archived previous populated surface to '{arc_path}'.")

        diff_target = base_branch if ("..." in base_branch or base_branch in ("HEAD", "HEAD~1")) else f"{base_branch}...HEAD"
        res_diff = subprocess.run(["git", "diff", "--name-only", diff_target], capture_output=True, text=True, check=False, timeout=30)
        mod_files = [line.strip() for line in res_diff.stdout.splitlines() if line.strip()]
        res_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False, timeout=30)
        if res_status.returncode == 0:
            for line in res_status.stdout.splitlines():
                if len(line) >= 4:
                    raw_f = line[3:].strip()
                    if " -> " in raw_f:
                        raw_f = raw_f.split(" -> ")[1].strip()
                    mod_files.append(raw_f)
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

        author = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, check=False, timeout=10).stdout.strip() or "Enterprise Agent"
        current_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False, timeout=10).stdout.strip() or "feat/core-service"

        affected_list = "\n".join([f'  - "{a}"' for a in sorted(affected)])
        affected_bullets = "\n".join([f'- `{a}`' for a in sorted(affected)])

        content = (
            f'---\ntitle: "Change Surface: Automated Update"\nauthor: "{author}"\ncreated_date: "{datetime.date.today().isoformat()}"\n'
            f'target_branch: "{current_branch}"\nrisk_level: "LOW"\naffected_projects:\n{affected_list}\n---\n\n'
            f"# Change Surface\n\n## 1. Intent & Business Rationale\nAutomated implementation surface generated by EP-OS CLI.\n\n"
            f"## 2. Affected Monorepo Projects\n{affected_bullets}\n\n## 3. Code Surface\n### Modified Files\n{code_lines}\n\n"
            f"## 4. Test Surface\n### Unit & Integration Suites\n{test_lines}\n\n## 5. Invariants\n"
            "- UTC timestamps preserved across all persistence models.\n- DDD domain isolation strictly preserved without framework leakage.\n"
            "- Real ephemeral containers for integration test assertions.\n\n## 6. Risk Matrix\n"
            "- Rollback: Revert commits via standard git rollback.\n- Blast radius bounded strictly to declared Code Surface.\n"
        )
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Initialized Change Surface at '{target_file}'.")
        cmd_validate = [sys.executable, os.path.join(SCRIPTS_DIR, "validate-change-surface.py"), target_file]
        return subprocess.run(cmd_validate, timeout=30).returncode

    return 0

# --- Subcommand: migration (Expand/Contract Static DDL Scanner) ---
DESTRUCTIVE_DDL_PATTERNS = [
    (r"\bDROP\s+COLUMN\b", "DROP COLUMN detected. Breaking schema alteration violates Expand/Contract (Phase 1-4)."),
    (r"\bRENAME\s+COLUMN\b", "RENAME COLUMN detected. Instant rename breaks rolling deployments. Use dual-write Expand/Contract."),
    (r"\bALTER\s+COLUMN\s+.*?\bSET\s+NOT\s+NULL\b", "SET NOT NULL on existing column without phased backfill causes deployment failure."),
    (r"\bADD\s+COLUMN\s+.*?\bNOT\s+NULL\b(?!\s+DEFAULT\b)", "ADD COLUMN NOT NULL without DEFAULT breaks concurrent insert versions."),
    (r"\bDROP\s+TABLE\b", "DROP TABLE detected without phased deprecation period."),
]

def cmd_migration(args: argparse.Namespace) -> int:
    scan_dir = getattr(args, "dir", None) or "."
    target_files = []

    if getattr(args, "diff", False):
        base = getattr(args, "base", "origin/main") or "origin/main"
        diff_target = base if ("..." in base or base in ("HEAD", "HEAD~1")) else f"{base}...HEAD"
        try:
            res = subprocess.run(["git", "diff", "--name-only", diff_target], capture_output=True, text=True, check=False, timeout=30)
            if res.returncode == 0:
                diff_files = res.stdout.splitlines()
                target_files = [f for f in diff_files if f.endswith(".sql") and os.path.exists(f)]
                if not target_files:
                    print("[OK] Expand/Contract Verified: 0 migration files modified in diff.")
                    return 0
        except Exception:
            pass
    else:
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

        adr_match = re.search(r"--\s*adr-ref:\s*(\S+)", content, re.IGNORECASE)
        if adr_match:
            adr_path = adr_match.group(1).lstrip("/\\")
            if os.path.isfile(adr_path):
                continue
            else:
                violations.append((file_path, 1, f"ADR reference '{adr_path}' does not exist on disk.", adr_match.group(0)))

        for pattern, desc in DESTRUCTIVE_DDL_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_no = content[:match.start()].count("\n") + 1
                violations.append((file_path, line_no, desc, match.group(0)))

    if violations:
        print("[FAIL] EXPAND/CONTRACT MIGRATION GATE VIOLATION!", file=sys.stderr)
        print("Destructive database operations detected that break rolling zero-downtime deployments:\n", file=sys.stderr)
        for v_file, v_line, v_desc, v_match in violations:
            print(f"  ❌ {v_file}:{v_line} -> Found '{v_match}'", file=sys.stderr)
            print(f"     Reason: {v_desc}", file=sys.stderr)
        print("\nRemediation: Follow Expand/Contract phased lifecycle (see references/core-directives.md).", file=sys.stderr)
        print("If this is Phase 5 (Contract cleanup), add an approved ADR comment: '-- adr-ref: docs/adr/NNNN-contract.md'.", file=sys.stderr)
        return 1

    print(f"[OK] Expand/Contract Verified: {len(target_files)} migration files checked. 0 destructive operations.")
    return 0


# --- Subcommand: release & milestone (SemVer & Release Governance) ---
def cmd_release(args: argparse.Namespace) -> int:
    action = args.action
    version = getattr(args, "version", None) or getattr(args, "version_flag", None)

    if action == "create":
        if not version or not re.match(r"^v?\d+\.\d+\.\d+", version):
            print(f"[ERROR] Version '{version}' does not match SemVer format (vMAJOR.MINOR.PATCH).", file=sys.stderr)
            return 1
        formatted_version = f"v{version.lstrip('v')}"
        tag_res = subprocess.run(["git", "tag", "-s", formatted_version, "-m", f"Release {formatted_version}"], check=False, timeout=30)
        if tag_res.returncode != 0:
            res = subprocess.run(["git", "tag", "-a", formatted_version, "-m", f"Release {formatted_version}"], check=False, timeout=30)
            if res.returncode != 0:
                return res.returncode
        print(f"[OK] Created release tag '{formatted_version}'.")
        return 0
    elif action == "finalize":
        cur_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False, timeout=10).stdout.strip()
        is_prod = getattr(args, "prod", False) or cur_branch == "prod"
        version_label = version
        today_str = datetime.date.today().isoformat()
        rel_dir = "docs/releases"
        os.makedirs(rel_dir, exist_ok=True)
        rel_filename = f"RELEASE_{version_label}.md" if version_label else f"RELEASE_{today_str}.md"
        rel_file = os.path.join(rel_dir, rel_filename)
        changes_dir = "docs/changes"
        summaries = []

        # Scope changes to files in docs/changes/ created since previous git tag
        res_tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True, check=False, timeout=10)
        prev_tag = res_tag.stdout.strip() if res_tag.returncode == 0 else None

        scoped_files = set()
        if prev_tag:
            res_diff = subprocess.run(["git", "diff", "--name-only", "--diff-filter=AM", f"{prev_tag}..HEAD", "--", changes_dir], capture_output=True, text=True, check=False, timeout=10)
            if res_diff.returncode == 0:
                for f in res_diff.stdout.splitlines():
                    if f.strip().endswith(".md"):
                        scoped_files.add(os.path.basename(f.strip()))
            res_status = subprocess.run(["git", "status", "--porcelain", "--", changes_dir], capture_output=True, text=True, check=False, timeout=10)
            if res_status.returncode == 0:
                for line in res_status.stdout.splitlines():
                    if len(line) >= 4:
                        p = line[3:].strip()
                        if " -> " in p:
                            p = p.split(" -> ")[1].strip()
                        if p.endswith(".md"):
                            scoped_files.add(os.path.basename(p))

        if os.path.exists(changes_dir):
            for cf in sorted(os.listdir(changes_dir)):
                if cf.endswith(".md"):
                    if not prev_tag or (scoped_files and cf in scoped_files):
                        with open(os.path.join(changes_dir, cf), "r", encoding="utf-8", errors="ignore") as fh:
                            summaries.append(f"### {cf}\n\n" + fh.read())

        header_title = f"Production Release Notes: {version_label or today_str}" if is_prod else f"Release Notes: {version_label or today_str}"
        rel_content = (
            f"# {header_title}\n\n- **Date**: `{today_str}`\n- **Branch**: `{cur_branch}`\n"
            f"- **Production**: `{is_prod}`\n"
            f"- **Change Surfaces Included**: `{len(summaries)}`\n\n## Change Summaries\n\n"
            + ("\n\n---\n\n".join(summaries) if summaries else "_No individual Change Surface files recorded._\n")
        )
        with open(rel_file, "w", encoding="utf-8") as fh:
            fh.write(rel_content)
        print(f"[OK] Generated release notes at '{rel_file}'.")
        print(f"[OK] Finalized release progression on branch '{cur_branch}'.")
        return 0
    return 0


def cmd_milestone(args: argparse.Namespace) -> int:
    action = args.action
    name = getattr(args, "name", None)
    ms_dir = "docs/milestones"
    os.makedirs(ms_dir, exist_ok=True)

    if action == "create":
        if not name:
            print("[ERROR] Milestone name required for create.", file=sys.stderr)
            return 1
        ms_file = os.path.join(ms_dir, f"{name}.md")
        if os.path.exists(ms_file):
            print(f"[INFO] Milestone '{name}' already exists at '{ms_file}'.")
            return 0
        with open(ms_file, "w", encoding="utf-8") as f:
            f.write(
                f"# Milestone: {name}\n\n- **Created**: `{datetime.date.today().isoformat()}`\n"
                f"- **Target Due Date**: `{getattr(args, 'due', None) or 'TBD'}`\n- **Status**: `IN_PROGRESS`\n"
                "- **Associated Subprojects**:\n  - `TBD`\n\n## Delivery Objectives\n"
                "- [ ] Implement core features\n- [ ] 10-Dimension Audit clean\n- [ ] Ephemeral container tests passing\n"
            )
        print(f"[OK] Created milestone manifest at '{ms_file}'.")
        return 0
    elif action in ("status", "check"):
        ms_files = [os.path.join(ms_dir, f) for f in os.listdir(ms_dir) if f.endswith(".md")] if os.path.exists(ms_dir) else []
        if name:
            ms_files = [f for f in ms_files if os.path.basename(f) == f"{name}.md" or os.path.basename(f).startswith(name)]
        if not ms_files:
            print("[INFO] No matching milestones found.")
            return 0
        print(f"=== EP-OS Milestone {action.upper()} ({len(ms_files)} milestone(s)) ===")
        all_completed = True
        for mf in ms_files:
            with open(mf, "r", encoding="utf-8", errors="ignore") as fh:
                c = fh.read()
            total_items = len(re.findall(r"-\s*\[[ xX]\]", c))
            done_items = len(re.findall(r"-\s*\[[xX]\]", c))
            is_done = total_items > 0 and total_items == done_items
            if not is_done and total_items > 0:
                all_completed = False
            status = "COMPLETED" if is_done else "IN_PROGRESS"
            pct = f"({done_items}/{total_items} items)" if total_items else ""
            print(f"  • {os.path.basename(mf)[:-3]}: [{status}] {pct}")
        if action == "check" and not all_completed:
            print("[WARN] Some milestones have incomplete checklist items.", file=sys.stderr)
        return 0
    return 0

# --- Subcommand: main dispatcher ---
def main():
    parser = argparse.ArgumentParser(
        prog="ep",
        description="Unified Mechanical CLI for Enterprise-Product Engineering OS (EP-OS)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Operational subcommands")

    # surface
    p_surface = subparsers.add_parser("surface", help="Change Surface validation, blast-radius bounding, and archival")
    p_surface.add_argument("action", choices=["validate", "check-diff", "init", "archive"], help="Action to perform")
    p_surface.add_argument("file", nargs="?", default=None, help="Path to CHANGE_SURFACE markdown file")
    p_surface.add_argument("--surface-file", dest="surface_file", default=None, help="Path to CHANGE_SURFACE markdown file")
    p_surface.add_argument("--output", dest="output", default=None, help="Path to CHANGE_SURFACE markdown file (alias)")
    p_surface.add_argument("--base", default="origin/main", help="Base git branch for diff check")
    p_surface.add_argument("--strict", action="store_true", help="Disallow template placeholders")
    p_surface.add_argument("--scope", default=None, help="Project scope hint")
    p_surface.add_argument("--title", default=None, help="Change Surface title")
    p_surface.add_argument("--changes-dir", default="docs/changes", help="Directory for archived Change Surfaces")
    p_surface.add_argument("--no-reset", action="store_true", help="Do not reset active Change Surface to template")

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
    p_vcs.add_argument("action", choices=["sync-check", "init-branches"], help="VCS action")
    p_vcs.add_argument("--base", default="main", help="Base trunk branch")
    p_vcs.add_argument("--push", action="store_true", default=True, help="Push initialized branches to remote origin")
    p_vcs.add_argument("--no-push", dest="push", action="store_false", help="Do not push to remote origin")

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
    p_rel.add_argument("--version", dest="version_flag", default=None, help="Target release version (alias)")
    p_rel.add_argument("--prod", action="store_true", help="Finalize production release")

    # milestone
    p_ms = subparsers.add_parser("milestone", help="Milestone tracking and objectives")
    p_ms.add_argument("action", choices=["create", "status", "check"], help="Milestone action")
    p_ms.add_argument("name", nargs="?", default=None, help="Milestone name")
    p_ms.add_argument("--due", default=None, help="Target due date")

    # delegate to existing scripts: audit, verify, nc
    p_audit = subparsers.add_parser("audit", help="Run 10-Dimension Enterprise Audit Suite")
    p_audit.add_argument("--scope", default=".", help="Directory or file path to audit")
    p_audit.add_argument("--diff", nargs="?", const="origin/main...HEAD", default=None, help="Audit only modified git diff lines")
    p_audit.add_argument("--output", default=None, help="Path to save AUDIT_REPORT.md")
    p_audit.add_argument("--baseline", default=None, help="Path to baseline JSON file for ratchet auditing")
    p_audit.add_argument("--json", action="store_true", help="Output results in JSON")

    p_verify = subparsers.add_parser("verify", help="Run parallel mechanical gatekeeper suite")
    p_verify.add_argument("--root", default=".", help="Root directory to scan")
    p_verify.add_argument("--heal", action="store_true", help="Autonomously heal missing prerequisites before verifying")
    p_verify.add_argument("--diff", nargs="?", const="origin/main", help="Run verification scoped to git diff (fast-path)")
    p_verify.add_argument("--surface", action="store_true", help="Run verification scoped to active Change Surface (fast-path)")

    p_nc = subparsers.add_parser("nc", help="Audit NEED_CLARIFICATION items for expiration")
    p_nc.add_argument("action", choices=["check"], help="Action to perform")
    p_nc.add_argument("--max-age", type=int, default=14, help="Max allowed age in days before blocking")

    # hooks
    p_hooks = subparsers.add_parser("hooks", help="Manage zero-dependency native git hooks")
    p_hooks.add_argument("action", choices=["install", "uninstall", "run"], help="Hook action")
    p_hooks.add_argument("hook_name", nargs="?", default=None, help="Specific hook name to run (e.g. pre-commit, pre-push)")
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
    p_lic.add_argument("--package-json", dest="package_json", default=None, help="Path to package.json (alias for --root)")
    p_lic.add_argument("--sbom", action="store_true", help="Generate .ep/sbom.json")

    # adopt
    p_adopt = subparsers.add_parser("adopt", help="Brownfield monorepo onboarding and baseline ratcheting")
    p_adopt.add_argument("--root", default=".", help="Monorepo root directory")
    p_adopt.add_argument("--scope", dest="scope", default=None, help="Scope directory to adopt (alias for --root)")
    p_adopt.add_argument("--apply", action="store_true", help="Apply adoption changes to monorepo (default: True)")
    p_adopt.add_argument("--profile", default="B", choices=["A", "B", "C", "D", "a", "b", "c", "d"], help="Target Architectural Profile")
    p_adopt.add_argument("--dry-run", action="store_true", help="Simulate adoption without writing files")

    # telemetry
    p_tel = subparsers.add_parser("telemetry", help="Zero-dependency observability & telemetry verification")
    p_tel.add_argument("action", choices=["verify"], default="verify", nargs="?", help="Telemetry action")
    p_tel.add_argument("--root", default=".", help="Root directory to verify")

    # finops
    p_fin = subparsers.add_parser("finops", help="Resource bounds & FinOps cost threshold compliance")
    p_fin.add_argument("action", choices=["check"], default="check", nargs="?", help="FinOps action")
    p_fin.add_argument("--root", default=".", help="Root directory to check")

    # policy
    p_pol = subparsers.add_parser("policy", help="Enterprise policy engine & compliance validation")
    p_pol.add_argument("action", choices=["test"], default="test", nargs="?", help="Policy action")
    p_pol.add_argument("--root", default=".", help="Root directory to test")

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
    p_ast.add_argument("--diff", nargs="?", const="origin/main", help="Scan git diff files")
    p_ast.add_argument("--surface", action="store_true", help="Scan active Change Surface files")

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
    p_iac.add_argument("action", nargs="?", default="verify", choices=["verify", "scan"], help="IaC action")
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
    p_perf = subparsers.add_parser("perf", help="Run standard k6 or locust performance and stress tests")
    p_perf.add_argument("--tool", default=None, choices=["k6", "locust"], help="Performance test engine")
    p_perf.add_argument("--script", default=None, help="Path to test script")
    p_perf.add_argument("--target-url", default=None, help="Base target URL")
    p_perf.add_argument("--vus", type=int, default=10, help="Virtual users")
    p_perf.add_argument("--duration", default="10s", help="Duration string")
    p_perf.add_argument("--dry-run", action="store_true", help="Validate script and execution engine without invoking HTTP requests")

    # container
    p_container = subparsers.add_parser("container", help="Smart OCI container engine detector and liveness resolver")
    p_container.add_argument("action", nargs="?", default="status", choices=["status", "detect", "info"], help="Container action")
    p_container.add_argument("--json", action="store_true", help="Output container engine status as JSON")

    # pack (context bundling & anti-slowness)
    p_pack = subparsers.add_parser("pack", help="Batch-pack codebase context into a single LLM-optimized bundle (anti-slowness)")
    p_pack.add_argument("--surface", action="store_true", help="Pack files from active Change Surface")
    p_pack.add_argument("--diff", nargs="?", const="origin/main", help="Pack files from git diff")
    p_pack.add_argument("--files", nargs="+", help="Specific files to pack")
    p_pack.add_argument("--scope", help="Directory scope to pack")
    p_pack.add_argument("--output", help="Output file path (default stdout)")
    p_pack.add_argument("--max-lines", type=int, default=800, help="Max lines per file")
    p_pack.add_argument("--summary", action="store_true", help="Include task context summary at top of bundle")
    p_pack.add_argument("--root", default=".", help="Monorepo root")

    # doctor (prerequisite audit and autonomous healing)
    p_doc = subparsers.add_parser("doctor", help="Enterprise OS prerequisite audit and autonomous healing")
    p_doc.add_argument("--heal", action="store_true", help="Autonomously configure missing prerequisites")
    p_doc.add_argument("--root", default=".", help="Monorepo root")

    # skill (product-specific tailored skill generator)
    p_sk = subparsers.add_parser("skill", help="Generate compact, product-specific tailored skill manifest")
    p_sk.add_argument("action", nargs="?", default="generate", choices=["generate"], help="Skill action")
    p_sk.add_argument("--output", default=None, help="Output file path (default PRODUCT_SKILL.md)")
    p_sk.add_argument("--root", default=".", help="Monorepo root")

    # ci (CI/CD pipeline workflow scaffolding)
    p_ci = subparsers.add_parser("ci", help="CI/CD pipeline workflow scaffolding")
    p_ci.add_argument("action", nargs="?", default="init", choices=["init"], help="CI action")
    p_ci.add_argument("--platform", default="github", choices=["github", "gitlab"], help="CI platform")
    p_ci.add_argument("--root", default=".", help="Monorepo root")

    # quality (production-readiness quality gates)
    p_qual = subparsers.add_parser("quality", help="Enterprise production quality & idempotency gates")
    p_qual.add_argument("action", nargs="?", default="check", choices=["check"], help="Quality action")
    p_qual.add_argument("--diff", nargs="?", const="origin/main", help="Scope checks to git diff")
    p_qual.add_argument("--surface", action="store_true", help="Scope checks to active Change Surface")
    p_qual.add_argument("--root", default=".", help="Monorepo root")
    p_qual.add_argument("--json", action="store_true", help="Output findings as JSON")

    # chaos (chaos engineering experiment runner)
    p_chaos = subparsers.add_parser("chaos", help="Chaos engineering experiment management & verification")
    p_chaos.add_argument("action", nargs="?", default="verify", choices=["scaffold", "verify", "run"], help="Chaos action")
    p_chaos.add_argument("name", nargs="?", default=None, help="Experiment name")
    p_chaos.add_argument("--file", default=None, help="Chaos experiment plan file")
    p_chaos.add_argument("--service", default=None, help="Target service name")
    p_chaos.add_argument("--dry-run", action="store_true", help="Dry run simulation")

    # contract (API & schema contract verification)
    p_contract = subparsers.add_parser("contract", help="API and schema contract testing & compatibility verification")
    p_contract.add_argument("action", nargs="?", default="verify", choices=["verify", "lint"], help="Contract action")
    p_contract.add_argument("--dir", default=None, help="Directory containing schemas")
    p_contract.add_argument("--file", default=None, help="Specific schema file")
    p_contract.add_argument("--diff", nargs="?", const="origin/main", help="Verify contract changes against base")

    # sbom (Software Bill of Materials)
    p_sbom = subparsers.add_parser("sbom", help="Software Bill of Materials (SBOM) generator and validator")
    p_sbom.add_argument("action", nargs="?", default="generate", choices=["generate", "verify"], help="SBOM action")
    p_sbom.add_argument("--output", default="sbom.json", help="Output SBOM file path")
    p_sbom.add_argument("--format", choices=["cyclonedx", "spdx"], default="cyclonedx", help="SBOM format")
    p_sbom.add_argument("--file", default=None, help="SBOM file to verify")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    def run_audit(a: argparse.Namespace) -> int:
        cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "audit-runner.py")]
        if a.scope:
            cmd.extend(["--scope", a.scope])
        if a.output:
            cmd.extend(["--output", a.output])
        if a.diff:
            cmd.extend(["--diff", a.diff])
        baseline_file = getattr(a, "baseline", None)
        if not baseline_file and os.path.exists(".ep/baseline.json"):
            baseline_file = ".ep/baseline.json"
        if baseline_file:
            cmd.extend(["--baseline", baseline_file])
        if a.json:
            cmd.append("--json")
        return subprocess.run(cmd, timeout=300).returncode

    dispatch = {
        "surface": cmd_surface, "migration": cmd_migration, "graph": cmd_graph,
        "init": cmd_init, "worktree": cmd_worktree, "vcs": cmd_vcs, "pr": cmd_pr,
        "session": cmd_session, "manifest": cmd_manifest, "preflight": cmd_preflight,
        "release": cmd_release, "milestone": cmd_milestone, "audit": run_audit,
        "verify": run_enterprise_verify,
        "nc": lambda a: subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "check-nc-items.py"), "--max-age", str(a.max_age)], timeout=30).returncode,
        "hooks": cmd_hooks, "security": cmd_security, "license": cmd_license, "adopt": cmd_adopt,
        "telemetry": cmd_telemetry, "finops": cmd_finops, "policy": cmd_policy,
        "sync-skill": cmd_sync_skill, "ast": cmd_ast, "run": cmd_run, "run-many": cmd_run_many,
        "iac": cmd_iac, "slo": cmd_slo, "codeowners": cmd_codeowners, "dora": cmd_dora,
        "perf": cmd_perf, "container": cmd_container, "pack": cmd_pack, "context": cmd_pack,
        "doctor": cmd_doctor, "skill": cmd_skill, "ci": cmd_ci, "quality": cmd_quality,
        "chaos": cmd_chaos, "contract": cmd_contract, "sbom": cmd_sbom,
    }
    if args.subcommand in dispatch:
        sys.exit(dispatch[args.subcommand](args))


if __name__ == "__main__":
    main()
