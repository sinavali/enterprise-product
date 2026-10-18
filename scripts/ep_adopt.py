#!/usr/bin/env python3
"""
ep_adopt.py — Brownfield Monorepo Adoption Wizard & Ratchet Baseline Engine for EP-OS
Analyzes legacy or in-progress codebases, discovers subproject boundaries,
generates compliant AGENT.md manifests and project.json target contracts,
and snapshots technical debt into .ep/baseline.json for non-breaking adoption.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from scripts.ep_stack import detect_stack
except ImportError:
    from ep_stack import detect_stack

EXCLUDED_ADOPT_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".cache",
    ".venv",
    ".nx",
    "coverage",
    "__pycache__",
    ".ep",
    "templates",
}

PROJECT_MARKERS = [
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle.kts",
    "composer.json",
    "pubspec.yaml",
    "pyproject.toml",
    "CMakeLists.txt",
    "mix.exs",
]


def discover_subprojects(root_dir: str = ".") -> List[str]:
    discovered = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_ADOPT_DIRS and not d.startswith(".")]
        # Check if current directory has a project marker
        if any(marker in files for marker in PROJECT_MARKERS):
            rel_path = os.path.relpath(root, root_dir)
            if rel_path != ".":
                discovered.append(rel_path.replace("\\", "/"))
    return sorted(discovered)


def infer_scope(project_path: str) -> str:
    tokens = set(re.split(r"[/\\_\-]+", project_path.lower()))
    if any(t in tokens for t in ["backend", "services", "api", "server", "worker"]):
        return "backend"
    if any(t in tokens for t in ["frontend", "web", "ui", "client"]):
        return "frontend"
    if any(t in tokens for t in ["mobile", "ios", "android"]) or ("app" in tokens and "apps" not in tokens):
        return "mobile"
    return "shared"


def scaffold_agent_manifest(project_path: str, stack_info: Dict[str, str], profile: str = "B") -> str:
    project_name = os.path.basename(project_path)
    scope = infer_scope(project_path)
    stack_lang = stack_info.get("lang", "generic")
    audit_cmd = stack_info.get("audit") or f"python3 scripts/ep.py audit --scope {project_path}"
    content = f"""---
project_name: "{project_name}"
profile: "{profile.upper()}"
architectural_profile: "{profile.upper()}"
stack: "{stack_lang}"
scope: "{scope}"
owner: "engineering"
tier_overrides: []
---

# Project Agent Manifest: {project_name}

## 1. Scope & Business Intent
Subproject '{project_name}' adopted into EP-OS governance.
Inferred scope: `{scope}`.

## 2. Architectural Profile
Enforcing Profile {profile.upper()}:
- DDD Domain isolation
- Explicit Target Contracts
- Zero unhandled errors

## 3. Local Nx Target
- **Lint**: `{stack_info.get('lint', 'echo No lint')}`
- **Test**: `{stack_info.get('test', 'echo No test')}`
- **Build**: `{stack_info.get('build', 'echo No build')}`
- **Audit**: `{audit_cmd}`

## 4. Test & Verification
- Unit & integration verification adhering to 10-dimension audit criteria.
"""
    return content


def scaffold_project_json(project_path: str, stack_info: Dict[str, str], profile: str = "B") -> Dict[str, Any]:
    project_name = os.path.basename(project_path)
    scope = infer_scope(project_path)
    rel_schema = os.path.relpath("node_modules/nx/schemas/project-schema.json", project_path).replace("\\", "/")
    return {
        "name": project_name,
        "$schema": rel_schema,
        "projectType": "application" if scope in ("frontend", "mobile") else "service",
        "sourceRoot": f"{project_path}/src",
        "tags": [
            f"profile:{profile.lower()}",
            f"scope:{scope}",
            f"lang:{stack_info.get('lang', 'generic')}",
        ],
        "targets": {
            "lint": {
                "executor": "nx:run-commands",
                "options": {
                    "command": stack_info.get("lint", "echo 'No lint command'"),
                    "cwd": project_path,
                },
            },
            "test": {
                "executor": "nx:run-commands",
                "options": {
                    "command": stack_info.get("test", "echo 'No test command'"),
                    "cwd": project_path,
                },
            },
            "build": {
                "executor": "nx:run-commands",
                "options": {
                    "command": stack_info.get("build", "echo 'No build command'"),
                    "cwd": project_path,
                },
            },
            "audit": {
                "executor": "nx:run-commands",
                "options": {
                    "command": f"python3 scripts/ep.py audit --scope {project_path}",
                },
            },
        },
    }


def create_baseline_snapshot(root_dir: str = ".") -> int:
    os.makedirs(os.path.join(root_dir, ".ep"), exist_ok=True)
    baseline_file = os.path.join(root_dir, ".ep", "baseline.json")

    audit_runner_path = os.path.join(SCRIPTS_DIR, "audit-runner.py")
    if not os.path.exists(audit_runner_path):
        return 0

    cmd = [sys.executable, audit_runner_path, "--scope", root_dir, "--json"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
    findings = []
    if res.returncode in (0, 1):
        try:
            data = json.loads(res.stdout)
            findings = data.get("findings", [])
        except Exception:
            pass

    baseline_data = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_grandfathered_findings": len(findings),
        "findings": findings,
    }

    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f, indent=2)

    print(f"[OK] Snapshotted {len(findings)} initial technical debt findings into '{baseline_file}'.")
    return len(findings)


def cmd_adopt(args: argparse.Namespace) -> int:
    root = getattr(args, "scope", None) or getattr(args, "root", ".") or "."
    profile = getattr(args, "profile", "B") or "B"
    dry_run = getattr(args, "dry_run", False)

    print(f"=== EP-OS Brownfield Monorepo Adoption Wizard ===")
    print(f"Scanning '{root}' for subprojects...")

    subprojects = discover_subprojects(root)
    if not subprojects:
        print("[INFO] No subprojects discovered under standard project markers.")
        return 0

    print(f"Discovered {len(subprojects)} subproject(s):")
    for sp in subprojects:
        print(f"  • {sp}")

    adopted_agents = 0
    adopted_targets = 0

    for sp in subprojects:
        sp_full_path = os.path.join(root, sp)
        stack_info = detect_stack(sp_full_path)
        agent_path = os.path.join(sp_full_path, "AGENT.md")
        target_path = os.path.join(sp_full_path, "project.json")

        if not os.path.exists(agent_path):
            if not dry_run:
                manifest_content = scaffold_agent_manifest(sp, stack_info, profile=profile)
                with open(agent_path, "w", encoding="utf-8") as fh:
                    fh.write(manifest_content)
            adopted_agents += 1
            print(f"  [+] Created AGENT.md for '{sp}' (Profile {profile}, lang: {stack_info['lang']})")

        if not os.path.exists(target_path):
            if not dry_run:
                target_json = scaffold_project_json(sp, stack_info, profile=profile)
                with open(target_path, "w", encoding="utf-8") as fh:
                    json.dump(target_json, fh, indent=2)
            adopted_targets += 1
            print(f"  [+] Created project.json for '{sp}'")

    if not dry_run:
        print("\nCreating initial audit baseline ratchet snapshot...")
        create_baseline_snapshot(root)

    print(f"\n[SUCCESS] Adoption Complete! Generated {adopted_agents} AGENT.md and {adopted_targets} project.json manifests.")
    print("          All subprojects are now bound to EP-OS governance contracts.")
    return 0
