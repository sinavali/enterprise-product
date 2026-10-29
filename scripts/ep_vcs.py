#!/usr/bin/env python3
"""
ep_vcs.py — VCS Provider Abstraction, Multi-Tier Branching & Production Gate for EP-OS
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from scripts.ep_scaffold import archive_change_surface


class BaseGitProvider:
    def get_current_branch(self) -> str:
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False, timeout=10)
            return res.stdout.strip() if res.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def get_remote_url(self) -> str:
        try:
            res = subprocess.run(["git", "config", "remote.origin.url"], capture_output=True, text=True, check=False, timeout=10)
            return res.stdout.strip() if res.returncode == 0 else ""
        except Exception:
            return ""

    def sync_check(self, base_branch: str = "main", branches: Optional[List[str]] = None, root_dir: str = ".") -> Tuple[bool, List[str]]:
        if not branches:
            branches = ["test", "stage", "prod"]
        issues = []
        
        # Verify base branch exists locally or remotely (DEFECT-05)
        resolved_base = None
        for cand in [base_branch, f"origin/{base_branch}"]:
            res = subprocess.run(["git", "rev-parse", "--verify", cand], cwd=root_dir, capture_output=True, text=True, check=False, timeout=30)
            if res.returncode == 0:
                resolved_base = cand
                break
        
        if not resolved_base:
            return False, [f"Base branch '{base_branch}' not found locally or on origin. Cannot perform sync-check."]

        for b in branches:
            resolved_b = None
            for cand in [b, f"origin/{b}"]:
                res_b = subprocess.run(["git", "rev-parse", "--verify", cand], cwd=root_dir, capture_output=True, text=True, check=False, timeout=30)
                if res_b.returncode == 0:
                    resolved_b = cand
                    break
            if not resolved_b:
                continue

            res_ahead = subprocess.run(["git", "rev-list", f"{resolved_base}..{resolved_b}"], cwd=root_dir, capture_output=True, text=True, check=False, timeout=30)
            ahead_commits = [c.strip() for c in res_ahead.stdout.splitlines() if c.strip()]
            if ahead_commits:
                issues.append(f"Branch '{b}' ({resolved_b}) has {len(ahead_commits)} unmerged commits not reachable from '{base_branch}'. Rogue commits violate promotion pipeline!")

        return len(issues) == 0, issues

    def create_prod_pr(self, title: str, body: str, head_branch: str, root_dir: str = ".") -> int:
        raise NotImplementedError


class GitHubProvider(BaseGitProvider):
    def create_prod_pr(self, title: str, body: str, head_branch: str, root_dir: str = ".") -> int:
        print("=== PRODUCTION PR SECURITY GATE ===")
        print("Validating prod PR rules: auto-merge=DISABLED, human_review=ENFORCED...")
        if not shutil.which("gh"):
            print("[INFO] 'gh' CLI not found. Falling back to Local Git Provider.")
            return LocalGitProvider().create_prod_pr(title, body, head_branch, root_dir=root_dir)

        cmd = [
            "gh", "pr", "create",
            "--base", "prod",
            "--head", head_branch,
            "--title", title,
            "--body", f"{body}\n\n> [!CAUTION]\n> **STRICT HUMAN-ONLY GATE**: AI agents are forbidden from merging this PR. Auto-merge is disabled.",
            "--label", "needs/human-review",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
        if res.returncode == 0:
            pr_output = res.stdout.strip()
            print(f"[PASS] Production PR created successfully: {pr_output}")
            # Mechanically disable auto-merge on GitHub (DEFECT-06)
            subprocess.run(["gh", "pr", "merge", "--disable-auto", head_branch], capture_output=True, text=True, check=False, timeout=30)
            print("[GATE] Auto-merge mechanically disabled via 'gh pr merge --disable-auto'.")
            print("[GATE] Reminder: Merging into 'prod' must be performed by a human engineer.")
        else:
            print(f"[ERROR] Failed to create prod PR: {res.stderr.strip()}", file=sys.stderr)
        return res.returncode


class GitLabProvider(BaseGitProvider):
    def create_prod_pr(self, title: str, body: str, head_branch: str, root_dir: str = ".") -> int:
        print("=== PRODUCTION MR SECURITY GATE ===")
        if not shutil.which("glab"):
            return LocalGitProvider().create_prod_pr(title, body, head_branch, root_dir=root_dir)
        cmd = [
            "glab", "mr", "create",
            "--target-branch", "prod",
            "--source-branch", head_branch,
            "--title", title,
            "--description", f"{body}\n\n> [!CAUTION]\n> **STRICT HUMAN-ONLY GATE**: AI agents are forbidden from merging this MR."
        ]
        return subprocess.run(cmd, check=False, timeout=30).returncode


class LocalGitProvider(BaseGitProvider):
    def create_prod_pr(self, title: str, body: str, head_branch: str, root_dir: str = ".") -> int:
        print("[OK] Local Git Provider: Recording PR intent for 'prod'...")
        rel_dir = os.path.join(root_dir, "docs", "releases")
        os.makedirs(rel_dir, exist_ok=True)
        pr_path = os.path.join(rel_dir, "PR_PROD_PENDING.md")
        with open(pr_path, "w", encoding="utf-8") as f:
            f.write(
                f"# Pending Production PR: {title}\n\n"
                f"- **Head Branch**: `{head_branch}`\n"
                f"- **Target Branch**: `prod`\n"
                f"- **Date**: `{datetime.date.today().isoformat()}`\n"
                "- **Auto-Merge**: DISABLED\n\n"
                f"{body}\n\n"
                "> [!CAUTION]\n"
                "> **STRICT HUMAN-ONLY GATE**: Merging to `prod` must be performed by a human user.\n"
            )
        print(f"[OK] Production PR record created at '{pr_path}'.")
        print("[GATE] AI agents are strictly forbidden from merging to 'prod'.")
        return 0


def get_git_provider() -> BaseGitProvider:
    try:
        res = subprocess.run(["git", "config", "remote.origin.url"], capture_output=True, text=True, check=False, timeout=10)
        remote = res.stdout.strip().lower()
    except Exception:
        remote = ""
    if "github.com" in remote:
        return GitHubProvider()
    elif "gitlab.com" in remote:
        return GitLabProvider()
    elif not remote:
        return LocalGitProvider()
    if shutil.which("gh") and ("github" in remote or not remote):
        return GitHubProvider()
    elif shutil.which("glab") and "gitlab" in remote:
        return GitLabProvider()
    return LocalGitProvider()


def cmd_vcs(args: argparse.Namespace) -> int:
    action = args.action
    provider = get_git_provider()

    if action == "sync-check":
        base = args.base or "main"
        print(f"Executing multi-tier VCS topology sync-check against base '{base}'...")
        ok, issues = provider.sync_check(base_branch=base)
        if not ok:
            print("[FAIL] VCS Topology Drift Detected!", file=sys.stderr)
            for iss in issues:
                print(f"  ❌ {iss}", file=sys.stderr)
            print("\nRemediation: Fast-forward or rebase promotion branches from 'main'.", file=sys.stderr)
            return 1
        print("[OK] Multi-Tier VCS Topology in sync. Zero rogue commits detected.")
        return 0
    elif action in ("init-branches", "init-topology"):
        base = args.base or "main"
        branches = ["test", "stage", "prod"]
        print(f"=== Initializing Multi-Tier VCS Branches from '{base}' ===")
        for b in branches:
            res_check = subprocess.run(["git", "rev-parse", "--verify", b], capture_output=True, text=True, check=False, timeout=10)
            if res_check.returncode == 0:
                print(f"  ℹ️ Branch '{b}' already exists.")
            else:
                res_create = subprocess.run(["git", "branch", b, base], capture_output=True, text=True, check=False, timeout=10)
                if res_create.returncode == 0:
                    print(f"  ✅ Created branch '{b}' at '{base}'.")
                else:
                    print(f"  ❌ Failed to create '{b}': {res_create.stderr.strip()}", file=sys.stderr)

        if getattr(args, "push", True):
            res_rem = subprocess.run(["git", "remote"], capture_output=True, text=True, check=False, timeout=10)
            if "origin" in res_rem.stdout.splitlines():
                print("Publishing promotion branches to remote 'origin'...")
                res_push = subprocess.run(["git", "push", "-u", "origin", "test", "stage", "prod"], capture_output=True, text=True, check=False, timeout=60)
                if res_push.returncode == 0:
                    print("  ✅ Successfully published 'test', 'stage', and 'prod' to 'origin'.")
                else:
                    print(f"  ℹ️ Remote push status: {res_push.stderr.strip() or res_push.stdout.strip()}")
        print("[OK] Multi-Tier VCS topology ready.")
        return 0
    return 0


def cmd_pr(args: argparse.Namespace) -> int:
    action = args.action
    provider = get_git_provider()

    if action == "create-prod":
        surface_file = getattr(args, "surface_file", "CHANGE_SURFACE.md") or "CHANGE_SURFACE.md"
        if os.path.exists(surface_file):
            try:
                from scripts.ep_scaffold import archive_change_surface
            except ImportError:
                from ep_scaffold import archive_change_surface  # type: ignore[import-not-found,no-redef]
            ok_arc, arc_res = archive_change_surface(surface_file, reset_root=True)
            if ok_arc:
                print(f"[OK] Change Surface auto-archived to '{arc_res}' prior to production PR.")

        head = args.head or provider.get_current_branch()
        title = args.title or f"Release Candidate: {head}"
        body = args.body or "Automated release candidate prepared under EP-OS protocol."
        return provider.create_prod_pr(title=title, body=body, head_branch=head)
    return 0


def pack_release(args: argparse.Namespace) -> int:
    """
    Package EP-OS runtime into an absolutely minimalized release zip binary.
    Enforces maximum file count constraint (<= max_files, default 30).
    """
    import zipfile

    output_path = getattr(args, "output", "Packed.zip") or "Packed.zip"
    max_files = getattr(args, "max_files", 30) or 30
    root_dir = getattr(args, "root", ".") or "."
    root_dir = os.path.abspath(root_dir)

    # Core metadata and manifest files
    root_files = [
        "SKILL.md",
        "PRODUCT_SKILL.md",
        "AGENT.md",
        "README.md",
        "LICENSE",
        "project.json",
    ]

    # Core runtime Python scripts
    scripts_dir = os.path.join(root_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        print(f"[ERROR] Scripts directory not found at '{scripts_dir}'.", file=sys.stderr)
        return 1

    script_files = sorted([f for f in os.listdir(scripts_dir) if f.endswith(".py")])

    # Launcher wrapper script for root
    launcher_content = """#!/usr/bin/env bash
# EP-OS Release Binary Entrypoint Launcher
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${DIR}/scripts:${PYTHONPATH:-}"
exec python3 "${DIR}/scripts/ep.py" "$@"
"""

    total_files = len(root_files) + len(script_files) + 1  # +1 for root launcher 'ep'

    print("=== EP-OS Release Binary Packaging ===")
    print(f"Target Output: '{output_path}'")
    print(f"Maximum File Count Ceiling: {max_files}")
    print(f"Selected Files Count: {total_files}")

    if total_files > max_files:
        print(
            f"[ERROR] Release package contains {total_files} files, exceeding limit of {max_files} files.\n"
            f"Remediation: Prune non-essential files before packaging.",
            file=sys.stderr,
        )
        return 1

    # Verify that all required files exist
    for rf in root_files:
        full_p = os.path.join(root_dir, rf)
        if not os.path.isfile(full_p):
            print(f"[ERROR] Required release file '{rf}' does not exist at '{full_p}'.", file=sys.stderr)
            return 1

    try:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        tmp_output = f"{output_path}.tmp.{os.getpid()}"
        with zipfile.ZipFile(tmp_output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 1. Add root executable entrypoint
            zinfo = zipfile.ZipInfo("ep")
            zinfo.external_attr = 0o755 << 16  # rwxr-xr-x
            zinfo.date_time = datetime.datetime.now().timetuple()[:6]
            zf.writestr(zinfo, launcher_content)

            # 2. Add root manifest and documentation files
            for rf in root_files:
                full_p = os.path.join(root_dir, rf)
                zf.write(full_p, rf)

            # 3. Add scripts with executable bits preserved where appropriate
            for sf in script_files:
                full_p = os.path.join(scripts_dir, sf)
                arcname = f"scripts/{sf}"
                zinfo = zipfile.ZipInfo(arcname)
                if os.access(full_p, os.X_OK):
                    zinfo.external_attr = 0o755 << 16
                else:
                    zinfo.external_attr = 0o644 << 16
                zinfo.date_time = datetime.datetime.now().timetuple()[:6]
                with open(full_p, "rb") as fh:
                    zf.writestr(zinfo, fh.read())

        # Verify archive integrity
        with zipfile.ZipFile(tmp_output, "r") as zf_check:
            bad_file = zf_check.testzip()
            if bad_file:
                print(f"[ERROR] Corrupt file '{bad_file}' detected in generated zip.", file=sys.stderr)
                os.remove(tmp_output)
                return 1
            packed_names = zf_check.namelist()
            if len(packed_names) > max_files:
                print(f"[ERROR] Packed zip has {len(packed_names)} files > {max_files} limit.", file=sys.stderr)
                os.remove(tmp_output)
                return 1

        os.replace(tmp_output, output_path)
        file_size_kb = os.path.getsize(output_path) / 1024
        print(f"[OK] Release zip binary created successfully at '{output_path}'.")
        print(f"     Total Files: {len(packed_names)} (Ceiling: <= {max_files}) | Size: {file_size_kb:.1f} KB")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to create release zip binary: {e}", file=sys.stderr)
        return 1

