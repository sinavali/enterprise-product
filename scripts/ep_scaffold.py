#!/usr/bin/env python3
"""
ep_scaffold.py — Scaffolding, Worktrees, Manifest Projection & Preflight for EP-OS
Handles project initialization across architectural profiles (A/B/C/D),
isolated monorepo git worktrees, universal agent manifest projection (CLAUDE.md, .cursorrules),
and environment preflight capability verification.
"""

import argparse
import datetime
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


CLEAN_SURFACE_TEMPLATE = """---
title: "Change Surface: [Short Descriptive Title]"
author: "[Author or Agent ID]"
created_date: "{date}"
target_branch: "main"
risk_level: "LOW"                    # LOW | MEDIUM | HIGH | CRITICAL
affected_projects:
  - "services/core"
---

# Change Surface: [Feature or Task Title]

## 1. Intent & Business Rationale
[Provide a clear, unambiguous statement of why this change is needed, what problem it solves, and the expected business outcome.]

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `services/core` | Profile A (DDD/Hexagonal) | Target project |

## 3. Code Surface (Targeted Symbols & Files)
Declare the exact files and symbols that will be modified or created. Modifying files outside this surface requires updating this document.

### Added Files
- `services/core/src/index.ts`

### Modified Files
- `services/core/src/service.ts`

## 4. Test Surface
Every code change must have a corresponding test surface. Happy-path-only tests are prohibited.

### Unit & Domain Tests
- `services/core/tests/unit/service.spec.ts`

### Integration Tests (Real Ephemeral Containers)
- `services/core/tests/integration/service.test.ts`

### Failure & Resilience Tests
- `services/core/tests/integration/resilience.test.ts`

### Concurrency Tests
- `services/core/tests/integration/concurrency.test.ts`

## 5. Invariants & Non-Negotiables Preserved
- [ ] Tier 1: Pure domain logic remains 100% free of framework or ORM imports.
- [ ] Tier 1: Real container integration tests (no engine-substitution emulators like SQLite for Postgres).
- [ ] Tier 1: All stored and wire timestamps use UTC ISO-8601 (`Z`).
- [ ] Tier 1: Directory nesting depth does not exceed 6 levels from project root.
- [ ] Tier 1: Database migrations follow Expand/Contract pattern for zero-downtime rollout.
- [ ] Tier 2: Files respect size ceilings (\\le 800 lines hard, \\le 400 lines soft); no micro-file sprawl.
- [ ] Tier 2: Domain test coverage maintains \\ge 95% line & branch coverage; adapters \\ge 80%.
- [ ] Tier 2: Transactional outbox pattern used for domain events published to brokers.
- [ ] Tier 2: Backward compatibility of existing API contracts preserved.

## 6. Risk Matrix & Rollback Strategy
| Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|
| Potential regression in callers | Low | Low | Comprehensive automated regression test suite |

### Rollback Strategy
Revert commits via standard git rollback or branch reset.
"""


def get_clean_surface_template(date_str: Optional[str] = None) -> str:
    d = date_str or datetime.date.today().isoformat()
    return CLEAN_SURFACE_TEMPLATE.format(date=d)


def is_surface_unpopulated(content: str) -> bool:
    """Returns True if the content is an unpopulated baseline template."""
    if not content or not content.strip():
        return True
    placeholder_tokens = [
        "[Short Descriptive Title]",
        "[Feature or Task Title]",
        "[Author or Agent ID]",
        "[Provide a clear, unambiguous statement",
    ]
    has_placeholder = any(token in content for token in placeholder_tokens)
    has_date_placeholder = "YYYY-MM-DD" in content
    return has_placeholder or has_date_placeholder


def archive_change_surface(
    surface_file: str = "CHANGE_SURFACE.md",
    changes_dir: str = "docs/changes",
    reset_root: bool = True,
) -> Tuple[bool, str]:
    """
    Archives a populated Change Surface to docs/changes/YYYY-MM-DD-<slug>.md
    and resets the active surface to a clean baseline template.
    """
    if not os.path.exists(surface_file):
        return False, f"Change Surface file '{surface_file}' does not exist."

    try:
        with open(surface_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"Failed to read Change Surface file '{surface_file}': {e}"

    if not content.strip():
        return False, f"Change Surface file '{surface_file}' is empty."

    if is_surface_unpopulated(content):
        return False, "Active Change Surface is an unpopulated baseline template. Skipping archival."

    # Extract title
    title_match = re.search(r"^title:\s*[\"']?(.*?)[\"']?\s*$", content, re.MULTILINE)
    if title_match:
        raw_title = title_match.group(1).strip()
    else:
        h1_match = re.search(r"^#\s*(.*?)$", content, re.MULTILINE)
        raw_title = h1_match.group(1).strip() if h1_match else "change-surface"

    clean_title = re.sub(r"^Change Surface:\s*", "", raw_title, flags=re.IGNORECASE).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", clean_title.lower()).strip("-")
    if len(slug) > 60:
        slug = slug[:60].rstrip("-")
    if not slug:
        slug = "task-surface"

    # Extract date
    date_match = re.search(r"^created_date:\s*[\"']?(\d{4}[-/]\d{2}[-/]\d{2})[\"']?", content, re.MULTILINE)
    if date_match:
        created_date = date_match.group(1).replace("/", "-")
    else:
        created_date = datetime.date.today().isoformat()

    os.makedirs(changes_dir, exist_ok=True)
    target_path = os.path.join(changes_dir, f"{created_date}-{slug}.md")

    # Handle collision
    if os.path.exists(target_path) and os.path.abspath(target_path) != os.path.abspath(surface_file):
        try:
            with open(target_path, "r", encoding="utf-8") as f_ex:
                if f_ex.read().strip() == content.strip():
                    pass
                else:
                    counter = 1
                    while os.path.exists(os.path.join(changes_dir, f"{created_date}-{slug}-{counter}.md")):
                        counter += 1
                    target_path = os.path.join(changes_dir, f"{created_date}-{slug}-{counter}.md")
        except Exception:
            pass

    # Atomically write archive
    if os.path.abspath(target_path) != os.path.abspath(surface_file):
        atomic_write(target_path, content)

    # Reset root file to clean template if requested
    if reset_root and os.path.abspath(surface_file) != os.path.abspath(target_path):
        clean_template = get_clean_surface_template()
        atomic_write(surface_file, clean_template)

    return True, target_path

