#!/usr/bin/env python3
"""
ep_doctor.py — Enterprise Prerequisite Auditor, Autonomous Healer & Product Skill Generator
Validates that a repository conforms to all enterprise operating system requirements.
In --heal mode, autonomously builds, scaffolds, and publishes all missing configurations.
Generates tailored, compact, multi-profile PRODUCT_SKILL.md files to eliminate context bloat.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "templates")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

if TYPE_CHECKING:
    from scripts.ep_hooks import find_git_hooks_dir, install_hooks
    from scripts.ep_ops import atomic_write, resolve_container_engine
    from scripts.ep_runner import discover_projects
else:
    try:
        from scripts.ep_hooks import find_git_hooks_dir, install_hooks
        from scripts.ep_ops import atomic_write, resolve_container_engine
        from scripts.ep_runner import discover_projects
    except ImportError:
        from ep_hooks import find_git_hooks_dir, install_hooks
        from ep_ops import atomic_write, resolve_container_engine
        from ep_runner import discover_projects


PROFILE_DESCRIPTIONS = {
    "A": {
        "name": "Profile A (Backend DDD & Hexagonal Architecture)",
        "invariants": [
            "Pure Domain logic: zero framework or ORM imports in domain layer.",
            "Real ephemeral containers (Podman/Docker) for all database integration tests.",
            "Strict UTC storage convention for all timestamps and events.",
            "Transactional Outbox pattern for publishing domain events.",
        ],
    },
    "B": {
        "name": "Profile B (Web Applications)",
        "invariants": [
            "Strict WCAG 2.1 AA accessibility (a11y) compliance.",
            "Core Web Vitals performance targets (LCP < 2.5s, CLS < 0.1).",
            "Typed API client contracts derived from backend schemas (OpenAPI/Protobuf).",
        ],
    },
    "C": {
        "name": "Profile C (Mobile Clients)",
        "invariants": [
            "Predictable state management (BLoC / Redux / Riverpod).",
            "Offline-first sync engine with conflict resolution.",
            "Zero business logic inside UI widget / view classes.",
        ],
    },
    "D": {
        "name": "Profile D (Shared Contracts & Core Libraries)",
        "invariants": [
            "Pure stateless schemas, serializers, or utility functions.",
            "Zero dependencies on concrete services or application code.",
            "Semantic versioning and backward-compatible schema evolutions.",
        ],
    },
}


def check_git_hooks(root_dir: str = ".") -> Tuple[bool, str]:
    hooks_dir = find_git_hooks_dir(root_dir)
    if not hooks_dir:
        return False, "Not inside a git repository."
    required_hooks = ["pre-commit", "pre-push", "commit-msg"]
    missing = [h for h in required_hooks if not os.path.isfile(os.path.join(hooks_dir, h))]
    if missing:
        return False, f"Missing native git hooks: {', '.join(missing)}"
    return True, "All native git hooks active."


def check_vcs_branches(root_dir: str = ".") -> Tuple[bool, str]:
    required = ["main", "test", "stage", "prod"]
    missing = []
    for b in required:
        try:
            res = subprocess.run(["git", "rev-parse", "--verify", b], cwd=root_dir, capture_output=True, text=True, check=False, timeout=10)
            if res.returncode != 0:
                # Check origin
                res_origin = subprocess.run(["git", "rev-parse", "--verify", f"origin/{b}"], cwd=root_dir, capture_output=True, text=True, check=False, timeout=10)
                if res_origin.returncode != 0:
                    missing.append(b)
        except Exception:
            missing.append(b)
    if missing:
        return False, f"Missing multi-tier VCS promotion branches: {', '.join(missing)}"
    return True, "Multi-tier VCS topology fully configured (main, test, stage, prod)."


def check_codeowners(root_dir: str = ".") -> Tuple[bool, str]:
    candidates = [
        os.path.join(root_dir, ".github", "CODEOWNERS"),
        os.path.join(root_dir, "CODEOWNERS"),
        os.path.join(root_dir, "docs", "CODEOWNERS"),
    ]
    if any(os.path.isfile(c) for c in candidates):
        return True, "Deterministic CODEOWNERS configuration present."
    return False, "No CODEOWNERS file found at .github/CODEOWNERS or root."


def check_project_contracts(root_dir: str = ".") -> Tuple[bool, str]:
    projects = discover_projects(root_dir)
    if not projects:
        return False, "Zero project.json contracts found across monorepo."
    return True, f"Found {len(projects)} valid project.json contract(s)."


def check_manifests(root_dir: str = ".") -> Tuple[bool, str]:
    root_agent = os.path.join(root_dir, "AGENT.md")
    if not os.path.isfile(root_agent):
        return False, "Missing root AGENT.md manifest."
    return True, "Root AGENT.md manifest active."


def check_container_engine(root_dir: str = ".") -> Tuple[bool, str]:
    info = resolve_container_engine()
    engine = info.get("selected") or info.get("engine")
    if engine and engine != "none" and info.get("status") in ("available", "active", "ok", "degraded"):
        return True, f"Container engine detected: {engine} ({info.get('status')})."
    return False, "No running OCI container engine detected (Podman or Docker required for Tier 1 testing)."


def check_product_skill(root_dir: str = ".") -> Tuple[bool, str]:
    candidates = [
        os.path.join(root_dir, "PRODUCT_SKILL.md"),
        os.path.join(root_dir, ".ep", "SKILL.md"),
    ]
    if any(os.path.isfile(c) for c in candidates):
        return True, "Tailored Product Skill active."
    return False, "No tailored PRODUCT_SKILL.md found (run 'ep skill generate')."


def generate_product_skill(root_dir: str = ".", output_path: Optional[str] = None) -> str:
    """Generates a lean, compact PRODUCT_SKILL.md tailored to the exact projects and profiles present."""
    projects = discover_projects(root_dir)
    target_out = output_path or os.path.join(root_dir, "PRODUCT_SKILL.md")

    # Detect monorepo profiles and languages
    detected_profiles: Set[str] = set()
    project_rows = []

    for name, p_data in sorted(projects.items()):
        tags = [str(t).lower() for t in p_data.get("tags", [])]
        p_profile = "D"
        for t in tags:
            if t.startswith("profile:"):
                p_profile = t.split(":", 1)[1].upper()
                break
        detected_profiles.add(p_profile)
        p_scope = "shared"
        for t in tags:
            if t.startswith("scope:"):
                p_scope = t.split(":", 1)[1]
                break
        p_root = p_data.get("_root", p_data.get("root", "."))
        rel_root = os.path.relpath(p_root, root_dir).replace("\\", "/")
        project_rows.append(f"| `{name}` | `{rel_root}` | **Profile {p_profile}** | `{p_scope}` |")

    if not detected_profiles:
        detected_profiles = {"A", "D"}

    if not project_rows:
        project_rows.append("| `root` | `.` | **Profile D** | `shared` |")

    profile_sections = []
    for prof in sorted(list(detected_profiles)):
        p_info = PROFILE_DESCRIPTIONS.get(prof, {"name": f"Profile {prof}", "invariants": []})
        invariants_md = "\n".join(f"- {inv}" for inv in p_info["invariants"])
        profile_sections.append(f"### {p_info['name']}\n{invariants_md}")

    content = f"""# Product Operating Skill Manifest: Monorepo Governance

This is the **tailored operating skill** for this product monorepo. Agents working on this codebase must strictly observe the localized rules and profile mappings below.

---

## 1. Monorepo Project & Profile Matrix

| Project Name | Project Path | Architectural Profile | Scope |
|---|---|---|---|
{chr(10).join(project_rows)}

---

## 2. Active Architectural Profiles & Invariants

{chr(10).join(profile_sections)}

---

## 3. High-Velocity Single-Turn Ingestion Mandate (P0)

AI agents are **strictly forbidden from reading files one by one with sequential tool calls**.
Before modifying code:
1. Ingest all target files in a single turn:
   ```bash
   python3 scripts/ep.py pack --surface
   ```
2. For diff-based modifications:
   ```bash
   python3 scripts/ep.py pack --diff
   ```

---

## 4. Local Execution & Mechanical Verification

- **Run target**: `python3 scripts/ep.py run <project>:<target>`
- **Verify blast radius**: `python3 scripts/ep.py surface check-diff --strict`
- **Verify compliance**: `python3 scripts/ep.py verify`
- **10-Dimension Audit**: `python3 scripts/ep.py audit`
- **Run test suite**: `python3 -m unittest discover tests` (or native project test runner)
"""

    atomic_write(target_out, content.strip() + "\n")
    return target_out


def run_doctor(root_dir: str = ".", heal: bool = False) -> int:
    print("=== EP-OS Enterprise Operating System Diagnostic (Doctor) ===")
    print(f"Target Root: {os.path.abspath(root_dir)}\n")

    checks = [
        ("Git Hooks Gate", check_git_hooks),
        ("Multi-Tier VCS Topology", check_vcs_branches),
        ("CODEOWNERS Configuration", check_codeowners),
        ("Nx Target Contracts", check_project_contracts),
        ("Agent Manifest (AGENT.md)", check_manifests),
        ("OCI Container Engine", check_container_engine),
        ("Tailored Product Skill", check_product_skill),
    ]

    failed_checks = []

    for name, check_fn in checks:
        ok, msg = check_fn(root_dir)

        if ok:
            print(f"  ✅ {name}: {msg}")
        else:
            print(f"  ❌ {name}: {msg}")
            failed_checks.append((name, msg))

    if not failed_checks:
        print("\n[OK] Enterprise Doctor: 100% compliant. All operating system prerequisites satisfied.")
        return 0

    if not heal:
        print(f"\n[FAIL] Enterprise Doctor: {len(failed_checks)} prerequisite(s) missing or misconfigured.")
        print("Remediation: Run 'python3 scripts/ep.py doctor --heal' to autonomously build and configure them.")
        return 1

    print("\n--> Initiating Autonomous Self-Healing (--heal)...")

    # Heal Git Hooks
    if any(name == "Git Hooks Gate" for name, _ in failed_checks):
        print("  [HEAL] Installing native git hooks (pre-commit, pre-push, commit-msg)...")
        install_hooks(root_dir)

    # Heal VCS Branches
    if any(name == "Multi-Tier VCS Topology" for name, _ in failed_checks):
        print("  [HEAL] Scaffolding multi-tier VCS branches (test, stage, prod)...")
        for b in ["test", "stage", "prod"]:
            subprocess.run(["git", "branch", b, "main"], cwd=root_dir, capture_output=True, check=False, timeout=10)
        # Push if remote origin exists
        res_remote = subprocess.run(["git", "remote"], cwd=root_dir, capture_output=True, text=True, check=False, timeout=10)
        if "origin" in res_remote.stdout:
            print("  [HEAL] Publishing multi-tier branches to remote origin...")
            subprocess.run(["git", "push", "-u", "origin", "test", "stage", "prod"], cwd=root_dir, capture_output=True, check=False, timeout=30)

    # Heal CODEOWNERS
    if any(name == "CODEOWNERS Configuration" for name, _ in failed_checks):
        gh_dir = os.path.join(root_dir, ".github")
        os.makedirs(gh_dir, exist_ok=True)
        co_file = os.path.join(gh_dir, "CODEOWNERS")
        print(f"  [HEAL] Creating deterministic CODEOWNERS at '{co_file}'...")
        atomic_write(co_file, "# Enterprise Monorepo Code Ownership\n* @core-team\n")

    # Heal Product Skill
    if any(name == "Tailored Product Skill" for name, _ in failed_checks):
        print("  [HEAL] Compiling tailored multi-profile PRODUCT_SKILL.md...")
        ps_path = generate_product_skill(root_dir)
        print(f"  [HEAL] Generated '{ps_path}'.")

    # Re-verify
    print("\n--> Re-verifying post-healing state...")
    return run_doctor(root_dir=root_dir, heal=False)


def cmd_doctor(args: argparse.Namespace) -> int:
    root_dir = getattr(args, "root", ".") or "."
    heal = getattr(args, "heal", False)
    return run_doctor(root_dir=root_dir, heal=heal)


def cmd_skill(args: argparse.Namespace) -> int:
    action = getattr(args, "action", "generate") or "generate"
    root_dir = getattr(args, "root", ".") or "."
    if action == "generate":
        out_file = getattr(args, "output", None)
        path = generate_product_skill(root_dir=root_dir, output_path=out_file)
        print(f"[OK] Tailored Product Skill generated at '{path}'.")
        return 0
    return 0


def cmd_ci(args: argparse.Namespace) -> int:
    action = getattr(args, "action", "init") or "init"
    root_dir = getattr(args, "root", ".") or "."
    platform = getattr(args, "platform", "github") or "github"

    if action == "init":
        tmpl = os.path.join(TEMPLATES_DIR, "ci-workflow.template.yml")
        if not os.path.isfile(tmpl):
            print(f"[ERROR] CI workflow template not found at '{tmpl}'.", file=sys.stderr)
            return 1

        if platform == "github":
            dest_dir = os.path.join(root_dir, ".github", "workflows")
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, "ep-ci.yml")
            shutil.copyfile(tmpl, dest_file)
            print(f"[OK] Stamped GitHub Actions CI workflow to '{dest_file}'.")
            return 0
        elif platform == "gitlab":
            dest_file = os.path.join(root_dir, ".gitlab-ci.yml")
            # Minimal GitLab translation
            content = """stages:
  - verify
  - test
  - audit

ep-verify:
  stage: verify
  image: python:3.12
  script:
    - python3 scripts/ep.py verify

ep-test:
  stage: test
  image: python:3.12
  script:
    - python3 -m unittest discover tests

ep-audit:
  stage: audit
  image: python:3.12
  script:
    - python3 scripts/ep.py audit
"""
            atomic_write(dest_file, content)
            print(f"[OK] Stamped GitLab CI workflow to '{dest_file}'.")
            return 0
        else:
            print(f"[ERROR] Unsupported platform: {platform}", file=sys.stderr)
            return 1

    return 0
