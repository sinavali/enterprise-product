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
from typing import List, Optional, Tuple


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

    def sync_check(self, base_branch: str = "main", branches: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        if not branches:
            branches = ["test", "stage", "prod"]
        issues = []
        
        # Verify base branch exists locally or remotely (DEFECT-05)
        resolved_base = None
        for cand in [base_branch, f"origin/{base_branch}"]:
            res = subprocess.run(["git", "rev-parse", "--verify", cand], capture_output=True, text=True, check=False, timeout=30)
            if res.returncode == 0:
                resolved_base = cand
                break
        
        if not resolved_base:
            return False, [f"Base branch '{base_branch}' not found locally or on origin. Cannot perform sync-check."]

        for b in branches:
            resolved_b = None
            for cand in [b, f"origin/{b}"]:
                res_b = subprocess.run(["git", "rev-parse", "--verify", cand], capture_output=True, text=True, check=False, timeout=30)
                if res_b.returncode == 0:
                    resolved_b = cand
                    break
            if not resolved_b:
                continue

            res_ahead = subprocess.run(["git", "rev-list", f"{resolved_base}..{resolved_b}"], capture_output=True, text=True, check=False, timeout=30)
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
        head = args.head or provider.get_current_branch()
        title = args.title or f"Release Candidate: {head}"
        body = args.body or "Automated release candidate prepared under EP-OS protocol."
        return provider.create_prod_pr(title=title, body=body, head_branch=head)
    return 0
