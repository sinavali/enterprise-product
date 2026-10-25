#!/usr/bin/env python3
"""
ep_scaffold.py — Scaffolding, Worktrees, Manifest Projection & Preflight for EP-OS
Handles project initialization across architectural profiles (A/B/C/D),
isolated monorepo git worktrees, universal agent manifest projection (CLAUDE.md, .cursorrules),
and environment preflight capability verification.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from scripts.ep_ops import atomic_write
    from scripts.ep_stack import STACK_DEFINITIONS
else:
    try:
        from scripts.ep_ops import atomic_write
    except ImportError:
        try:
            from ep_ops import atomic_write
        except ImportError:
            def atomic_write(filepath: str, content: str, mode: str = "w", encoding: str = "utf-8") -> None:
                dir_name = os.path.dirname(os.path.abspath(filepath))
                os.makedirs(dir_name, exist_ok=True)
                tmp_file = f"{filepath}.tmp.{os.getpid()}"
                with open(tmp_file, mode, encoding=encoding) as f:
                    f.write(content)
                os.replace(tmp_file, filepath)
    try:
        from scripts.ep_stack import STACK_DEFINITIONS
    except ImportError:
        from ep_stack import STACK_DEFINITIONS

LANG_ALIASES = {
    "c#": "dotnet",
    "cs": "dotnet",
    "csharp": "dotnet",
    "golang": "go",
    "rs": "rust",
    "py": "python",
    "ts": "ts",
    "typescript": "ts",
    "node": "ts",
    "nodejs": "ts",
    "flutter": "dart",
    "c++": "cpp",
    "c": "cpp",
}


def cmd_init(args: argparse.Namespace) -> int:
    name = args.name
    profile = args.profile.upper()
    lang = (args.lang or "ts").lower()
    target_dir = args.dir or (f"apps/{name}" if profile in {"B", "C"} else f"services/{name}" if profile == "A" else f"libs/{name}")

    if os.path.exists(target_dir):
        print(f"[ERROR] Target directory '{target_dir}' already exists.", file=sys.stderr)
        return 1

    os.makedirs(target_dir, exist_ok=True)
    scope = "backend" if profile == "A" else "frontend" if profile == "B" else "mobile" if profile == "C" else "shared"

    templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "profiles")
    template_file = None
    if profile == "A" and lang in ("go", "golang"):
        template_file = "go-service-project.json"
    elif profile == "A" and lang in ("rust", "rs"):
        template_file = "rust-service-project.json"
    elif profile == "A" and lang in ("ts", "typescript", "node", "nodejs"):
        template_file = "node-service-project.json"
    elif profile == "A" and lang in ("python", "py"):
        template_file = "python-service-project.json"
    elif profile == "B":
        template_file = "next-web-project.json"
    elif profile == "C":
        template_file = "flutter-mobile-project.json"
    elif profile == "D":
        template_file = "contracts-project.json"

    project_json = None
    if template_file:
        template_path = os.path.join(templates_dir, template_file)
        if os.path.exists(template_path):
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    project_json = json.load(f)
                project_json["name"] = name
                project_json["sourceRoot"] = f"{target_dir}/src" if profile != "C" else f"{target_dir}/lib"
                for _, t_val in project_json.get("targets", {}).items():
                    if isinstance(t_val, dict) and "options" in t_val and "cwd" in t_val["options"]:
                        t_val["options"]["cwd"] = target_dir
            except Exception:
                project_json = None

    if not project_json:
        rel_schema = os.path.relpath("node_modules/nx/schemas/project-schema.json", target_dir).replace("\\", "/")
        norm_lang = LANG_ALIASES.get(lang, lang)
        stack_entry = next((s for s in STACK_DEFINITIONS if s[0] == norm_lang), None)
        if stack_entry:
            _, _, lint_c, test_c, build_c, audit_c = stack_entry
        else:
            lint_c = f"echo 'Linting {name}...'"
            test_c = f"echo 'Testing {name}...'"
            build_c = f"echo 'Building {name}...'"
            audit_c = f"echo 'Auditing {name}...'"

        project_json = {
            "name": name,
            "$schema": rel_schema,
            "projectType": "application" if profile != "D" else "library",
            "sourceRoot": f"{target_dir}/src",
            "tags": [f"profile:{profile.lower()}", f"scope:{scope}", f"lang:{norm_lang}"],
            "targets": {
                "lint": {"executor": "nx:run-commands", "options": {"command": lint_c, "cwd": target_dir}},
                "test": {"executor": "nx:run-commands", "options": {"command": test_c, "cwd": target_dir}},
                "build": {"executor": "nx:run-commands", "options": {"command": build_c, "cwd": target_dir}},
                "audit": {"executor": "nx:run-commands", "options": {"command": audit_c, "cwd": target_dir}},
            },
        }
    atomic_write(os.path.join(target_dir, "project.json"), json.dumps(project_json, indent=2) + "\n")

    agent_md = f"""---
project_name: "{name}"
profile: "{profile}"
stack: "{lang}"
scope: "{scope}"
owner: "engineering"
tier_overrides: []
dr:
  rto: "1h"
  rpo: "15m"
slo:
  tier: "tier-1"
  availability_target: "0.999"
resources:
  cpu_limit: "1000m"
  memory_limit: "1Gi"
---

# Project Agent Manifest: {name}

## 1. Scope & Business Intent
Domain responsibility and business purpose of {name}.

## 2. Architectural Profile & Boundaries
- **Profile**: {profile}
- **Primary Inputs**: Internal domain events, API clients.
- **Allowed Outbound Dependencies**: `libs/core-contracts`
- **Forbidden Dependencies**: Direct cross-boundary domain couplings.

## 3. Local Target Delegations
- `nx lint {name}`
- `nx test {name}`
- `nx build {name}`
- `nx audit {name}`

## 4. Test & Verification Rules
- Real ephemeral container verification for databases.
- Domain coverage target $\\ge 95\\%$, adapter coverage $\\ge 80\\%$.
"""
    atomic_write(os.path.join(target_dir, "AGENT.md"), agent_md)

    if profile == "A":
        for d in ["src/domain/entities", "src/domain/events", "src/application/use-cases", "src/infrastructure/adapters", "tests/unit", "tests/integration"]:
            os.makedirs(os.path.join(target_dir, d), exist_ok=True)
    elif profile == "B":
        for d in ["src/components/ui", "src/features", "src/routes", "tests/unit", "tests/e2e"]:
            os.makedirs(os.path.join(target_dir, d), exist_ok=True)
    elif profile == "C":
        for d in ["lib/core", "lib/features/sample/domain", "lib/features/sample/data", "lib/features/sample/presentation", "test/unit"]:
            os.makedirs(os.path.join(target_dir, d), exist_ok=True)
    elif profile == "D":
        for d in ["schemas/openapi", "schemas/proto", "src/generated", "tests/compatibility"]:
            os.makedirs(os.path.join(target_dir, d), exist_ok=True)

    print(f"[OK] Successfully initialized Profile {profile} project '{name}' at '{target_dir}'.")
    return 0


def cmd_worktree(args: argparse.Namespace) -> int:
    action = args.action
    branch = args.branch

    if action == "create":
        worktree_path = f"../worktrees/{branch.replace('/', '-')}"
        print(f"Creating isolated monorepo worktree for branch '{branch}' at '{worktree_path}'...")
        res = subprocess.run(["git", "worktree", "add", worktree_path, "-b", branch], check=False, timeout=30)
        if res.returncode != 0:
            return res.returncode
        print(f"[OK] Worktree created at {worktree_path}. Run 'cd {worktree_path} && pnpm install --frozen-lockfile'.")
        return 0

    elif action == "remove":
        worktree_path = f"../worktrees/{branch.replace('/', '-')}"
        print(f"Removing monorepo worktree at '{worktree_path}'...")
        res = subprocess.run(["git", "worktree", "remove", worktree_path], check=False, timeout=30)
        subprocess.run(["git", "worktree", "prune"], check=False, timeout=30)
        return res.returncode

    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    root_dir = args.root or "."
    count = 0
    root_agent = os.path.join(root_dir, "AGENT.md")
    if os.path.exists(root_agent):
        with open(root_agent, "r", encoding="utf-8") as f:
            agent_content = f.read()

        claude_path = os.path.join(root_dir, "CLAUDE.md")
        atomic_write(claude_path, f"<!-- AUTO-GENERATED FROM AGENT.md by ep manifest sync. DO NOT EDIT DIRECTLY. -->\n\n{agent_content}")
        count += 1

        cursor_path = os.path.join(root_dir, ".cursorrules")
        atomic_write(cursor_path, f"# Cursor AI Rules - Auto-generated from AGENT.md\n\n{agent_content}")
        count += 1

        windsurf_path = os.path.join(root_dir, ".windsurfrules")
        atomic_write(windsurf_path, f"# Windsurf Rules - Auto-generated from AGENT.md\n\n{agent_content}")
        count += 1

    for cur_root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "dist", "build"} and not d.startswith(".")]
        if "AGENT.md" in files and cur_root != root_dir:
            sub_agent = os.path.join(cur_root, "AGENT.md")
            sub_claude = os.path.join(cur_root, "CLAUDE.md")
            with open(sub_agent, "r", encoding="utf-8") as f:
                c = f.read()
            atomic_write(sub_claude, f"<!-- AUTO-GENERATED FROM AGENT.md by ep manifest sync -->\n\n{c}")
            count += 1

    print(f"[OK] Manifest projection complete: {count} agent manifest files synchronized.")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    checks = []
    shell_ok = False
    shell_name = "None"
    for sh, cmd_args in [("bash", ["bash", "-c", "echo ok"]), ("powershell", ["powershell", "-Command", "Write-Output ok"]), ("cmd", ["cmd", "/c", "echo ok"])]:
        try:
            res = subprocess.run(cmd_args, capture_output=True, text=True, check=False, timeout=10)
            if res.returncode == 0 and "ok" in res.stdout.lower():
                shell_ok = True
                shell_name = sh
                break
        except Exception:
            continue
    checks.append((f"Shell Execution (`{shell_name}`)", shell_ok))

    try:
        res = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False, timeout=10)
        checks.append(("Version Control (`git`)", res.returncode == 0))
    except Exception:
        checks.append(("Version Control (`git`)", False))

    py_ok = sys.version_info >= (3, 10)
    checks.append((f"Python Runtime ({sys.version_info.major}.{sys.version_info.minor})", py_ok))

    test_file = ".ep_preflight_probe"
    try:
        with open(test_file, "w") as f:
            f.write("probe")
        os.remove(test_file)
        checks.append(("Workspace Write Access", True))
    except Exception:
        checks.append(("Workspace Write Access", False))

    all_passed = all(status for _, status in checks)
    print("=== EP-OS Platform Preflight Access Verification ===")
    for name, status in checks:
        print(f"  [{'PASS' if status else 'FAIL'}] {name}")

    if not all_passed:
        print("\n[CRITICAL] Missing required execution capabilities!", file=sys.stderr)
        print("Repeatable Manual Fallback Instructions:", file=sys.stderr)
        print("  1. Ensure Python 3.10+ and Git are installed and available in PATH.", file=sys.stderr)
        print("  2. Grant the agent subprocess/shell execution permissions in the IDE settings.", file=sys.stderr)
        print("  3. Note: These permissions must be granted per-session by the human user.", file=sys.stderr)
        print("\nRefusing engagement on the Product until required execution capabilities are granted.", file=sys.stderr)
        return 2

    print("\n[OK] Preflight Verified: All required agent execution capabilities are granted.")
    return 0
