#!/usr/bin/env python3
"""
ep_ops.py — Operational Engineering & Deep Observability CLI for EP-OS
Zero-dependency operational engine providing mechanical verification for:
- Service Level Objectives (SLO) schema & error budget validation (`ep slo`)
- Monorepo Code Ownership coverage mapping (`ep codeowners`)
- Git-derived DORA metric calculations (`ep dora`)
- Standardized Performance testing orchestration via k6 / container (`ep perf`)
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

try:
    from scripts.ep_runner import discover_projects
except ImportError:
    try:
        from ep_runner import discover_projects
    except ImportError:
        discover_projects = None


# ==============================================================================
# SUBCOMMAND: ep slo
# ==============================================================================

def clean_yaml_val(raw_val: str) -> str:
    raw_v = raw_val.strip()
    if "#" in raw_v:
        m = re.match(r"^([\"'].*?[\"'])\s*(?:#.*)?$", raw_v)
        raw_v = m.group(1) if m else raw_v.split("#", 1)[0].strip()
    return raw_v.strip("\"'")


def parse_slo_yaml(content: str) -> Dict[str, Any]:
    """Zero-dependency parser for EP-OS SLO YAML definitions."""
    lines = content.splitlines()
    data: Dict[str, Any] = {
        "service": "",
        "tier": "tier-1",
        "owner_team": "",
        "slos": [],
    }

    current_slo: Optional[Dict[str, Any]] = None
    in_slos = False
    in_sli = False
    in_error_budget = False
    in_alert_triggers = False
    current_alert: Optional[Dict[str, Any]] = None

    for line in lines:
        raw_line = line
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip())

        # Top-level keys
        if indent == 0:
            in_slos = False
            m = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
            if m:
                k, raw_v = m.group(1), m.group(2)
                v = clean_yaml_val(raw_v)
                if k == "slos":
                    in_slos = True
                elif k in data:
                    data[k] = v
            continue

        if in_slos:
            # New SLO item
            slo_item_m = re.match(r"^\s*-\s*id:\s*(.*)$", line)
            if slo_item_m:
                in_sli = False
                in_error_budget = False
                in_alert_triggers = False
                current_slo = {
                    "id": clean_yaml_val(slo_item_m.group(1)),
                    "name": "",
                    "target": 0.99,
                    "window": "30d",
                    "sli": {},
                    "error_budget": {},
                }
                data["slos"].append(current_slo)
                continue

            if current_slo is not None:
                kv_m = re.match(r"^\s*([a-zA-Z0-9_-]+):\s*(.*)$", line)
                if kv_m:
                    k = kv_m.group(1).strip()
                    raw_v = kv_m.group(2)
                    v = clean_yaml_val(raw_v)

                    if k == "sli":
                        in_sli = True
                        in_error_budget = False
                        continue
                    elif k == "error_budget":
                        in_error_budget = True
                        in_sli = False
                        continue
                    elif k == "alert_triggers":
                        in_alert_triggers = True
                        current_slo["error_budget"]["alert_triggers"] = []
                        continue

                    if in_sli:
                        current_slo["sli"][k] = v
                    elif in_error_budget:
                        if in_alert_triggers and re.match(r"^\s*-\s*burn_rate:\s*(.*)$", line):
                            burn_m = re.match(r"^\s*-\s*burn_rate:\s*(.*)$", line)
                            raw_burn = clean_yaml_val(burn_m.group(1)).split()[0]
                            try:
                                burn_val = float(raw_burn)
                            except (ValueError, IndexError):
                                burn_val = 1.0
                            current_alert = {"burn_rate": burn_val}
                            current_slo["error_budget"].setdefault("alert_triggers", []).append(current_alert)
                        elif current_alert is not None and indent >= 8:
                            current_alert[k] = v
                        else:
                            try:
                                current_slo["error_budget"][k] = float(v) if "." in v else v
                            except ValueError:
                                current_slo["error_budget"][k] = v
                    else:
                        if k == "target":
                            try:
                                current_slo["target"] = float(v)
                            except ValueError:
                                current_slo["target"] = 0.99
                        else:
                            current_slo[k] = v

    return data


def validate_slo_dict(data: Dict[str, Any], filepath: str) -> List[str]:
    errors = []
    if not data.get("service"):
        errors.append(f"{filepath}: Missing or empty 'service' identifier.")
    if data.get("tier") not in ("tier-1", "tier-2", "tier-3"):
        errors.append(f"{filepath}: Invalid tier '{data.get('tier')}'. Must be tier-1, tier-2, or tier-3.")

    slos = data.get("slos", [])
    if not slos:
        errors.append(f"{filepath}: No SLOs defined in 'slos' list.")

    for idx, slo in enumerate(slos, start=1):
        slo_id = slo.get("id") or f"index_{idx}"
        target = slo.get("target")
        target_valid = False
        try:
            target_f = float(target)
            if 0.0 < target_f <= 1.0:
                target_valid = True
        except (ValueError, TypeError):
            pass
        if not target_valid:
            errors.append(f"{filepath}: SLO [{slo_id}] target '{target}' must be a float between 0.0 and 1.0.")
        if not slo.get("window"):
            errors.append(f"{filepath}: SLO [{slo_id}] missing measurement 'window' (e.g. '30d').")
        if not slo.get("sli") or not slo["sli"].get("metric_type"):
            errors.append(f"{filepath}: SLO [{slo_id}] missing SLI specification with 'metric_type'.")

    return errors


def cmd_slo(args: argparse.Namespace) -> int:
    target = getattr(args, "file", None)
    files_to_check: List[str] = []

    if target and os.path.exists(target):
        files_to_check.append(target)
    else:
        # Auto-discover SLO specifications in docs/slo/ or templates/monitoring/
        search_dirs = ["docs/slo", "templates/monitoring"]
        for s_dir in search_dirs:
            if os.path.exists(s_dir):
                for root, _, files in os.walk(s_dir):
                    for f in files:
                        if (f.endswith(".slo.yaml") or f.endswith(".slo.yml") or f == "slo.template.yaml" or f == "slo.yaml"):
                            files_to_check.append(os.path.normpath(os.path.join(root, f)))

    files_to_check = sorted(list(dict.fromkeys(files_to_check)))

    if not files_to_check:
        print("[WARN] Zero SLO specification files discovered.", file=sys.stderr)
        print("       Create one using 'templates/monitoring/slo.template.yaml' under 'docs/slo/'", file=sys.stderr)
        return 0

    print(f"=== EP-OS Service Level Objectives (SLO) Validator ({len(files_to_check)} file(s)) ===\n")
    all_errors = []

    for f_path in files_to_check:
        norm_path = f_path.replace("\\", "/")
        try:
            with open(f_path, "r", encoding="utf-8") as fh:
                content = fh.read()
            parsed = parse_slo_yaml(content)
            errors = validate_slo_dict(parsed, norm_path)
            if errors:
                all_errors.extend(errors)
                print(f"❌ {norm_path}: Invalid schema")
                for err in errors:
                    print(f"     • {err}")
            else:
                svc = parsed.get("service") or "unspecified"
                tier = parsed.get("tier") or "tier-1"
                slo_count = len(parsed.get("slos", []))
                print(f"✅ {norm_path}")
                print(f"   Service: {svc} ({tier}) | {slo_count} SLO target(s) defined:")
                for s in parsed.get("slos", []):
                    pct = f"{float(s.get('target', 0)) * 100:.2f}%"
                    print(f"     • [{s.get('id')}] {s.get('name')}: Target {pct} (Window: {s.get('window')})")
        except Exception as e:
            all_errors.append(f"{norm_path}: Failed to parse: {e}")
            print(f"❌ {norm_path}: Parse exception: {e}")

    if all_errors:
        print(f"\n[FAIL] SLO Validation failed with {len(all_errors)} defect(s).", file=sys.stderr)
        return 1

    print("\n[PASS] All SLO specifications match EP-OS monitoring schema.")
    return 0


# ==============================================================================
# SUBCOMMAND: ep codeowners
# ==============================================================================

def cmd_codeowners(args: argparse.Namespace) -> int:
    root_dir = getattr(args, "root", ".") or "."
    codeowners_paths = [
        os.path.join(root_dir, ".github", "CODEOWNERS"),
        os.path.join(root_dir, "docs", "CODEOWNERS"),
        os.path.join(root_dir, "CODEOWNERS"),
    ]

    existing_codeowners = [p for p in codeowners_paths if os.path.exists(p)]
    rules: List[Tuple[str, str]] = []

    if existing_codeowners:
        with open(existing_codeowners[0], "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    pattern = parts[0]
                    owner = " ".join(parts[1:])
                    rules.append((pattern, owner))

    # Detect monorepo projects
    subprojects: List[Dict[str, str]] = []
    seen_paths = set()
    if discover_projects is not None:
        discovered = discover_projects(root_dir)
        for proj_name, p_data in discovered.items():
            proj_path = p_data.get("root", ".")
            seen_paths.add(os.path.abspath(proj_path))
            owner = "UNASSIGNED"
            agent_file = os.path.join(proj_path, "AGENT.md")
            if os.path.exists(agent_file):
                with open(agent_file, "r", encoding="utf-8", errors="ignore") as fh:
                    c = fh.read()
                    m = re.search(r"owner:\s*([^\n]+)", c, re.IGNORECASE)
                    if m:
                        owner = m.group(1).strip().strip("\"'")

            if owner == "UNASSIGNED":
                rel_path = os.path.relpath(proj_path, root_dir).replace("\\", "/")
                for pat, r_owner in rules:
                    clean_pat = pat.lstrip("/").rstrip("/*")
                    if rel_path == clean_pat or rel_path.startswith(clean_pat):
                        owner = r_owner
                        break

            subprojects.append({
                "name": proj_name,
                "path": proj_path,
                "owner": owner,
            })

    # Also scan candidate root directories for unconfigured/legacy projects
    for candidate_dir in ["services", "apps", "libs", "packages"]:
        full_cand = os.path.join(root_dir, candidate_dir)
        if os.path.isdir(full_cand):
            for d in os.listdir(full_cand):
                proj_path = os.path.join(full_cand, d)
                if os.path.isdir(proj_path) and os.path.abspath(proj_path) not in seen_paths:
                    seen_paths.add(os.path.abspath(proj_path))
                    owner = "UNASSIGNED"
                    agent_file = os.path.join(proj_path, "AGENT.md")
                    if os.path.exists(agent_file):
                        with open(agent_file, "r", encoding="utf-8", errors="ignore") as fh:
                            c = fh.read()
                            m = re.search(r"owner:\s*([^\n]+)", c, re.IGNORECASE)
                            if m:
                                owner = m.group(1).strip().strip("\"'")

                    if owner == "UNASSIGNED":
                        rel_path = os.path.relpath(proj_path, root_dir).replace("\\", "/")
                        for pat, r_owner in rules:
                            clean_pat = pat.lstrip("/").rstrip("/*")
                            if rel_path == clean_pat or rel_path.startswith(clean_pat):
                                owner = r_owner
                                break

                    subprojects.append({
                        "name": f"{candidate_dir}/{d}",
                        "path": proj_path,
                        "owner": owner,
                    })

    print(f"=== EP-OS Monorepo Code Ownership Audit ===")
    if existing_codeowners:
        print(f"Global CODEOWNERS file: {existing_codeowners[0]} ({len(rules)} rule(s))")
    else:
        print("Global CODEOWNERS file: [None found] (Auditing via local AGENT.md manifests)")

    if not subprojects:
        print("[INFO] Zero subprojects found under services/, apps/, libs/, packages/.")
        return 0

    unowned = []
    for sp in subprojects:
        if sp["owner"] == "UNASSIGNED":
            unowned.append(sp)
            print(f"  ❌ [{sp['name']}] -> UNASSIGNED")
        else:
            print(f"  ✅ [{sp['name']}] -> {sp['owner']}")

    if unowned:
        print(f"\n[FAIL] {len(unowned)} subproject(s) lack assigned code owners!", file=sys.stderr)
        print("       Add rules to .github/CODEOWNERS or 'owner: ...' in subproject AGENT.md.", file=sys.stderr)
        return 1

    print(f"\n[PASS] All {len(subprojects)} monorepo projects have deterministic code owners.")
    return 0


# ==============================================================================
# SUBCOMMAND: ep dora
# ==============================================================================

def cmd_dora(args: argparse.Namespace) -> int:
    days = getattr(args, "days", 30) or 30
    print(f"=== EP-OS DORA Metrics Calculator (Last {days} Days) ===\n")

    since_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
    cmd = ["git", "log", f"--since={since_date}", "--pretty=format:%h|%cI|%s"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
    except Exception as e:
        print(f"[ERROR] Failed to read git history: {e}", file=sys.stderr)
        return 1

    if not lines:
        print(f"[INFO] Zero git commits found in the last {days} days.")
        return 0

    total_commits = len(lines)
    deploy_keywords = ["release", "merge", "deploy", "prod", "vcs:pr", "bump"]
    deploys = []
    failures = []

    for l in lines:
        parts = l.split("|", 2)
        if len(parts) == 3:
            sha, ts, subject = parts
            subj_lower = subject.lower()
            if any(k in subj_lower for k in deploy_keywords):
                deploys.append((sha, ts, subject))
            if any(k in subj_lower for k in ["revert", "hotfix", "fix(prod)", "rollback", "incident"]):
                failures.append((sha, ts, subject))

    deploy_count = len(deploys)
    failure_count = len(failures)

    # Calculate metrics
    freq_per_week = (deploy_count / days) * 7.0
    cfr_pct = (failure_count / deploy_count * 100.0) if deploy_count > 0 else 0.0

    print(f"Git Commits Analyzed: {total_commits}")
    print(f"Detected Release/Deploy Events: {deploy_count}")
    print(f"Detected Hotfix/Rollback Events: {failure_count}\n")

    # DORA Classification
    if freq_per_week >= 7.0:
        freq_rating = "Elite (Multiple deploys/day)"
    elif freq_per_week >= 1.0:
        freq_rating = "High (Weekly deploys)"
    else:
        freq_rating = "Medium / Low"

    if cfr_pct <= 5.0:
        cfr_rating = "Elite (0–5%)"
    elif cfr_pct <= 15.0:
        cfr_rating = "High (5–15%)"
    else:
        cfr_rating = "Medium / Degraded (>15%)"

    print("----------------------------------------------------------------------")
    print(f"1. Deployment Frequency : {freq_per_week:.2f} deploys/week -> {freq_rating}")
    print(f"2. Change Failure Rate  : {cfr_pct:.1f}% -> {cfr_rating}")
    print(f"3. Lead Time for Changes: Bounded by PR contract lifecycle (Target: < 24h)")
    print(f"4. Time to Restore Svc  : Bounded by Rollback Procedure (Target: < 1h)")
    print("----------------------------------------------------------------------")
    print("[PASS] DORA telemetry collected successfully.")
    return 0


# ==============================================================================
# SUBCOMMAND: ep perf
# ==============================================================================
# CONTAINER RESOLVER & SUBCOMMAND: ep container
# ==============================================================================

def get_container_install_instructions(platform_str: str) -> List[str]:
    """Returns platform-specific instructions for installing Podman."""
    p = platform_str.lower()
    if p.startswith("linux"):
        return [
            "Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y podman",
            "Fedora/RHEL  : sudo dnf install -y podman",
            "Arch Linux   : sudo pacman -S podman",
        ]
    elif p == "darwin":
        return [
            "macOS (Homebrew): brew install podman",
            "Initialize VM   : podman machine init",
            "Start VM        : podman machine start",
        ]
    elif p in ("win32", "cygwin"):
        return [
            "Windows (WinGet): winget install RedHat.Podman-Desktop",
            "WSL2 (Ubuntu)   : sudo apt-get update && sudo apt-get install -y podman",
        ]
    return ["Install Podman: https://podman.io/getting-started/installation"]


def probe_engine_liveness(binary_path: str, timeout: float = 2.5) -> bool:
    """Probes whether the container engine's socket/daemon is actively responsive."""
    try:
        res = subprocess.run(
            [binary_path, "info"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


def resolve_container_engine(check_liveness: bool = True, timeout: float = 2.5) -> Dict[str, Any]:
    """
    Intelligently resolves available OCI container engines on the host machine.
    Hierarchy:
    1. If both Podman and Docker exist:
       - Probe socket/daemon liveness.
       - Prefer Podman if alive (rootless, daemonless, FOSS enterprise standard).
       - Fall back to Docker if Docker is alive and Podman is not.
       - If neither socket is active, default to Podman binary with warning.
    2. If only one exists:
       - Probe its liveness and return it.
    3. If neither exists:
       - Return status 'missing' with OS-specific installation instructions.
    """
    podman_path = shutil.which("podman")
    docker_path = shutil.which("docker")
    platform_str = sys.platform

    podman_alive = probe_engine_liveness(podman_path, timeout=timeout) if (podman_path and check_liveness) else (bool(podman_path) if not check_liveness else False)
    docker_alive = probe_engine_liveness(docker_path, timeout=timeout) if (docker_path and check_liveness) else (bool(docker_path) if not check_liveness else False)

    selected: Optional[str] = None
    selected_path: Optional[str] = None
    selected_alive: bool = False
    reason: str = ""

    engines_found: List[str] = []
    if podman_path:
        engines_found.append("podman")
    if docker_path:
        engines_found.append("docker")

    if podman_path and docker_path:
        if check_liveness:
            if podman_alive:
                selected = "podman"
                selected_path = podman_path
                selected_alive = True
                reason = "Podman selected (active socket, rootless & daemonless enterprise standard)"
            elif docker_alive:
                selected = "docker"
                selected_path = docker_path
                selected_alive = True
                reason = "Docker selected (active daemon detected while Podman socket is inactive)"
            else:
                selected = "podman"
                selected_path = podman_path
                selected_alive = False
                reason = "Podman selected as enterprise default, but socket/machine is inactive (run 'podman machine start')"
        else:
            selected = "podman"
            selected_path = podman_path
            selected_alive = bool(podman_alive)
            reason = "Podman selected (enterprise default: rootless, daemonless)"
    elif podman_path:
        selected = "podman"
        selected_path = podman_path
        selected_alive = podman_alive
        reason = "Podman selected (only available OCI engine on host)"
    elif docker_path:
        selected = "docker"
        selected_path = docker_path
        selected_alive = docker_alive
        reason = "Docker selected (only available OCI engine on host)"
    else:
        selected = None
        selected_path = None
        selected_alive = False
        reason = "No OCI container engine (podman/docker) found in PATH"

    status = "available" if (selected and selected_alive) else ("inactive" if selected else "missing")

    return {
        "status": status,
        "selected": selected,
        "path": selected_path,
        "alive": selected_alive,
        "reason": reason,
        "platform": platform_str,
        "engines_found": engines_found,
        "details": {
            "podman": {"path": podman_path, "alive": podman_alive if podman_path else None},
            "docker": {"path": docker_path, "alive": docker_alive if docker_path else None},
        },
        "install_instructions": get_container_install_instructions(platform_str),
    }


def cmd_container(args: argparse.Namespace) -> int:
    as_json = getattr(args, "json", False)
    res = resolve_container_engine(check_liveness=True)

    if as_json:
        print(json.dumps(res, indent=2))
        return 0 if res["selected"] else 1

    print("=== EP-OS OCI Container Engine Resolver ===")
    print(f"Platform: {res['platform']}")

    if not res["engines_found"]:
        print("\n[FAIL] No OCI container engine found in PATH!")
        print("       Tier 1 Inviolable #3 mandates real ephemeral containers for integration testing.\n")
        print("Recommended installation commands:")
        for instr in res["install_instructions"]:
            print(f"  • {instr}")
        return 1

    found_str = ", ".join(f"{eng} ({res['details'][eng]['path']})" for eng in res["engines_found"])
    print(f"Found Engines  : {found_str}")
    print(f"Selected Engine: {res['selected']} ({res['path']})")
    liveness_str = "ALIVE (Responsive socket)" if res["alive"] else "INACTIVE (Daemon/Machine not started)"
    print(f"Liveness Status: {liveness_str}")
    print(f"Selection Rule : {res['reason']}")

    if not res["alive"]:
        print(f"\n[WARN] Container engine '{res['selected']}' was found, but its socket is not currently responsive.")
        if res["selected"] == "podman":
            print("       Start Podman VM/service: 'podman machine start' or 'systemctl --user start podman.socket'")
        else:
            print("       Start Docker daemon: 'sudo systemctl start docker' or launch Docker Desktop.")
        return 1

    print("\n[PASS] OCI container runtime is ready for ephemeral integration tests.")
    return 0


# ==============================================================================
# SUBCOMMAND: ep perf
# ==============================================================================

def cmd_perf(args: argparse.Namespace) -> int:
    script = getattr(args, "script", None) or "templates/perf-test.k6.js"
    target_url = getattr(args, "target_url", None) or os.environ.get("TARGET_URL", "http://localhost:8080")
    vus = getattr(args, "vus", 10)
    duration = getattr(args, "duration", "10s")
    dry_run = getattr(args, "dry_run", False)

    if not os.path.exists(script):
        print(f"[ERROR] Performance test script '{script}' not found.", file=sys.stderr)
        return 1

    print("=== EP-OS Performance & Stress Test Runner (k6) ===")
    print(f"Target Script: {script}")
    print(f"Target URL   : {target_url}")
    print(f"Virtual Users: {vus} | Duration: {duration}\n")

    k6_bin = shutil.which("k6")
    container_info = resolve_container_engine(check_liveness=not dry_run)
    container_engine = container_info["selected"]

    if dry_run:
        engine_str = f"native k6 ({k6_bin})" if k6_bin else (f"container ({container_engine})" if container_engine else "none (fallback instructions)")
        print(f"[OK] Dry run successful: Script '{script}' exists and execution engine detected: {engine_str}.")
        return 0

    if k6_bin:
        cmd = [k6_bin, "run", "--vus", str(vus), "--duration", str(duration), "-e", f"TARGET_URL={target_url}", script]
        print(f"[EXEC] Running native k6: {' '.join(cmd)}")
        return subprocess.run(cmd, timeout=600).returncode

    # Check container runtime fallback
    if container_engine:
        print(f"[INFO] Native k6 binary not found; falling back to {container_info['reason']}.")
        cwd = os.getcwd()
        cmd = [
            container_engine, "run", "--rm", "-i",
            "-v", f"{cwd}:/work:z",
            "-w", "/work",
            "-e", f"TARGET_URL={target_url}",
            "grafana/k6:latest", "run",
            "--vus", str(vus), "--duration", str(duration),
            script,
        ]
        print(f"[EXEC] Running containerized k6: {' '.join(cmd)}")
        return subprocess.run(cmd, timeout=600).returncode

    print("[WARN] Neither 'k6' nor an OCI container engine (podman/docker) was detected.", file=sys.stderr)
    print("       Per 'references/optional-tooling.md', performance testing degrades gracefully.", file=sys.stderr)
    print("       To execute performance tests:", file=sys.stderr)
    print("         1. Install k6: 'https://k6.io/docs/get-started/installation/'", file=sys.stderr)
    print("         2. Or install an OCI container engine:", file=sys.stderr)
    for instr in container_info["install_instructions"]:
        print(f"            • {instr}", file=sys.stderr)
    return 0
