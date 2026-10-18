#!/usr/bin/env python3
"""
ep_hooks.py — Zero-Dependency Native Git Hook Management Engine for EP-OS
Installs and manages bulletproof, zero-external-dependency git hooks for
pre-commit blast-radius bounding, secret scanning, migration safety,
pre-push VCS topology sync-checks, and conventional commit message verification.
"""

import argparse
import os
import re
import stat
import subprocess
import sys
from typing import List, Optional, Tuple

PRE_COMMIT_SCRIPT = """#!/usr/bin/env bash
# EP-OS Native Pre-Commit Gate (Zero-Dependency)
set -euo pipefail

SCRIPT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PYTHON_EXEC="python3"

if ! command -v "$PYTHON_EXEC" &>/dev/null; then
    echo "[EP-OS HOOK] Warning: python3 not found. Skipping mechanical gates." >&2
    exit 0
fi

EP_BIN="${SCRIPT_DIR}/scripts/ep.py"
if [ ! -f "$EP_BIN" ]; then
    # Fallback to globally available ep if inside skill or alias
    if command -v ep &>/dev/null; then
        EP_BIN="ep"
    else
        exit 0
    fi
fi

echo "=== [EP-OS HOOK] Running Pre-Commit Mechanical Gates ==="

# 1. Staged Secret Scanning Gate
echo "--> 1. Verifying staged diff for secrets and credentials..."
"$PYTHON_EXEC" "$EP_BIN" security scan --staged

# 2. Change Surface Blast-Radius Gate (if Change Surface or docs/changes present)
if [ -f "CHANGE_SURFACE.md" ] || [ -d "docs/changes" ]; then
    echo "--> 2. Verifying staged diff against declared Change Surface..."
    "$PYTHON_EXEC" "$EP_BIN" surface check-diff --strict
fi

# 3. Zero-Downtime Expand/Contract Migration Gate
if [ -d "migrations" ] || [ -d "prisma/migrations" ] || [ -d "db/migrations" ]; then
    echo "--> 3. Checking migration DDL safety..."
    "$PYTHON_EXEC" "$EP_BIN" migration check --diff
fi

echo "[EP-OS HOOK] All pre-commit gates passed successfully."
exit 0
"""

PRE_PUSH_SCRIPT = """#!/usr/bin/env bash
# EP-OS Native Pre-Push Gate (Zero-Dependency)
set -euo pipefail

SCRIPT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PYTHON_EXEC="python3"

if ! command -v "$PYTHON_EXEC" &>/dev/null; then
    exit 0
fi

EP_BIN="${SCRIPT_DIR}/scripts/ep.py"
if [ ! -f "$EP_BIN" ]; then
    if command -v ep &>/dev/null; then
        EP_BIN="ep"
    else
        exit 0
    fi
fi

echo "=== [EP-OS HOOK] Running Pre-Push Verification Suite ==="
"$PYTHON_EXEC" "$EP_BIN" verify

echo "=== [EP-OS HOOK] Running Pre-Push Multi-Tier VCS Sync-Check ==="
"$PYTHON_EXEC" "$EP_BIN" vcs sync-check
"""

COMMIT_MSG_SCRIPT = r"""#!/usr/bin/env python3
# EP-OS Native Conventional Commits Linter
import re
import sys

COMMIT_MSG_FILE = sys.argv[1]

CONVENTIONAL_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\([a-zA-Z0-9_\-\.\/]+\))?!?:\s*.+$"
)

try:
    with open(COMMIT_MSG_FILE, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
except Exception as e:
    print(f"[EP-OS HOOK] Failed to read commit message: {e}", file=sys.stderr)
    sys.exit(1)

# Ignore merge, squash, or fixup commits
if first_line.startswith(("Merge ", "Revert \"", "fixup!", "squash!")):
    sys.exit(0)

if not CONVENTIONAL_PATTERN.match(first_line):
    print("[FAIL] Invalid commit message format!", file=sys.stderr)
    print(f"       Message: '{first_line}'", file=sys.stderr)
    print("       Expected: <type>(<scope>): <summary>", file=sys.stderr)
    print("       Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert", file=sys.stderr)
    print("       Example: feat(auth): implement refresh token rotation", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
"""


def find_git_hooks_dir(repo_root: str = ".") -> Optional[str]:
    git_path = os.path.join(repo_root, ".git")
    if not os.path.exists(git_path):
        return None
    if os.path.isfile(git_path):
        # Worktree or submodule: parse gitdir pointer
        try:
            with open(git_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content.startswith("gitdir:"):
                gitdir = content.split("gitdir:", 1)[1].strip()
                if not os.path.isabs(gitdir):
                    gitdir = os.path.abspath(os.path.join(repo_root, gitdir))
                return os.path.join(gitdir, "hooks")
        except Exception:
            return None
    return os.path.join(git_path, "hooks")


def install_hooks(repo_root: str = ".") -> int:
    hooks_dir = find_git_hooks_dir(repo_root)
    if not hooks_dir:
        print(f"[ERROR] '{repo_root}' is not a valid git repository (.git not found).", file=sys.stderr)
        return 1

    os.makedirs(hooks_dir, exist_ok=True)

    hook_files = [
        ("pre-commit", PRE_COMMIT_SCRIPT),
        ("pre-push", PRE_PUSH_SCRIPT),
        ("commit-msg", COMMIT_MSG_SCRIPT),
    ]

    for name, script_content in hook_files:
        dest_path = os.path.join(hooks_dir, name)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        # chmod +x (0o755)
        current_stat = os.stat(dest_path)
        os.chmod(dest_path, current_stat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"[OK] Installed native git hook: '{dest_path}'.")

    print("[SUCCESS] EP-OS native git hooks installed (pre-commit, pre-push, commit-msg).")
    print("          All gates active with zero external package dependencies.")
    return 0


def uninstall_hooks(repo_root: str = ".") -> int:
    hooks_dir = find_git_hooks_dir(repo_root)
    if not hooks_dir or not os.path.exists(hooks_dir):
        print(f"[INFO] No git hooks found in '{repo_root}'.")
        return 0

    removed = 0
    for name in ["pre-commit", "pre-push", "commit-msg"]:
        hook_path = os.path.join(hooks_dir, name)
        if os.path.exists(hook_path):
            try:
                os.remove(hook_path)
                print(f"[OK] Removed hook: '{hook_path}'.")
                removed += 1
            except Exception as e:
                print(f"[ERROR] Could not remove '{hook_path}': {e}", file=sys.stderr)

    print(f"[SUCCESS] Uninstalled {removed} EP-OS git hooks.")
    return 0


def run_hook(hook_name: str = "pre-commit", repo_root: str = ".") -> int:
    hooks_dir = find_git_hooks_dir(repo_root)
    if hooks_dir:
        hook_path = os.path.join(hooks_dir, hook_name)
        if os.path.isfile(hook_path):
            print(f"=== [EP-OS HOOK] Executing '{hook_name}' Hook ===")
            return subprocess.run([hook_path], check=False, timeout=120).returncode

    # Direct execution fallback (DEFECT-10)
    print(f"=== [EP-OS HOOK] Executing '{hook_name}' Hook in direct mode ===")
    ep_bin = os.path.join(repo_root, "scripts", "ep.py")
    if hook_name == "pre-commit":
        rc1 = subprocess.run([sys.executable, ep_bin, "security", "scan", "--staged"], check=False, timeout=120).returncode
        if rc1 != 0:
            return rc1
        rc2 = subprocess.run([sys.executable, ep_bin, "migration", "check", "--diff"], check=False, timeout=120).returncode
        return rc2
    elif hook_name == "pre-push":
        rc1 = subprocess.run([sys.executable, ep_bin, "surface", "check-diff", "--strict"], check=False, timeout=120).returncode
        if rc1 != 0:
            return rc1
        rc2 = subprocess.run([sys.executable, ep_bin, "verify"], check=False, timeout=120).returncode
        if rc2 != 0:
            return rc2
        return subprocess.run([sys.executable, ep_bin, "vcs", "sync-check"], check=False, timeout=120).returncode
    return 0


def cmd_hooks(args: argparse.Namespace) -> int:
    action = args.action
    root = getattr(args, "root", ".") or "."
    if action == "install":
        return install_hooks(root)
    elif action == "uninstall":
        return uninstall_hooks(root)
    elif action == "run":
        hook_name = getattr(args, "hook_name", None) or "pre-commit"
        return run_hook(hook_name, root)
    return 0
