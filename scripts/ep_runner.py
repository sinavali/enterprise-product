#!/usr/bin/env python3
"""
ep_runner.py — Zero-Dependency Standalone Topological Task DAG Runner for EP-OS
Discovers project.json target contracts across polyglot monorepos, constructs
dependency graphs (DAGs), performs topological sorting, and executes targets
(lint, test, build, audit) with zero external Node.js/Nx package dependencies.
"""

import argparse
import collections
import concurrent.futures
import json
import os
import re
import shlex
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

EXCLUDED_DIRS = {
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
    "templates",
}


def discover_projects(root_dir: str = ".") -> Dict[str, Dict[str, Any]]:
    projects: Dict[str, Dict[str, Any]] = {}
    for current_root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        if "project.json" in files:
            p_file = os.path.join(current_root, "project.json")
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                name = data.get("name") or os.path.basename(current_root)
                data["_root"] = current_root.replace("\\", "/")
                projects[name] = data
            except Exception as e:
                print(f"[WARN] Failed to parse '{p_file}': {e}", file=sys.stderr)
    return projects


SHELL_CHARS = set(";&|><$`\n\r*?()[]{}~#")


def execute_target(
    project_name: str, target_name: str, target_cfg: Dict[str, Any], project_root: str, timeout: int = 300
) -> Tuple[int, str, float]:
    options = target_cfg.get("options", {})
    command = options.get("command")
    if not command:
        return 0, f"No command defined for {project_name}:{target_name}", 0.0

    cwd = options.get("cwd") or project_root
    t_start = time.time()
    try:
        if isinstance(command, str) and not any(c in command for c in SHELL_CHARS):
            cmd_args = shlex.split(command)
            res = subprocess.run(cmd_args, shell=False, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout)
        else:
            res = subprocess.run(command, shell=True, executable="/bin/sh", cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout)
        elapsed = time.time() - t_start
        output = res.stdout if res.returncode == 0 else f"{res.stdout}\n{res.stderr}".strip()
        return res.returncode, output, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t_start
        return 124, f"Target '{project_name}:{target_name}' timed out after {timeout}s", elapsed


def get_project_dependencies(p_name: str, p_data: Dict[str, Any], projects: Dict[str, Dict[str, Any]]) -> Set[str]:
    """Resolves upstream dependencies declared in project.json or package manifests."""
    declared = p_data.get("implicitDependencies")
    if declared is not None:
        return set(declared)

    deps: Set[str] = set()
    p_root = p_data.get("_root") or p_data.get("root", "")

    # Check package.json
    pkg_json = os.path.join(p_root, "package.json")
    if os.path.isfile(pkg_json):
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                pj = json.load(f)
            all_deps = {**pj.get("dependencies", {}), **pj.get("devDependencies", {})}
            for other_p in projects:
                if other_p != p_name and any(d == other_p or d.endswith(f"/{other_p}") for d in all_deps):
                    deps.add(other_p)
        except Exception:
            pass

    # Check go.mod
    go_mod = os.path.join(p_root, "go.mod")
    if os.path.isfile(go_mod):
        try:
            with open(go_mod, "r", encoding="utf-8") as f:
                content = f.read()
            for other_p in projects:
                if other_p != p_name and re.search(rf"\b{re.escape(other_p)}\b", content):
                    deps.add(other_p)
        except Exception:
            pass

    # Check Cargo.toml
    cargo_toml = os.path.join(p_root, "Cargo.toml")
    if os.path.isfile(cargo_toml):
        try:
            with open(cargo_toml, "r", encoding="utf-8") as f:
                content = f.read()
            for other_p in projects:
                if other_p != p_name and re.search(rf"\b{re.escape(other_p)}\b", content):
                    deps.add(other_p)
        except Exception:
            pass

    # Default heuristic: apps and services depend on libraries, but peer services do not depend on each other
    if not deps:
        is_app = p_data.get("projectType") != "library" and not (
            p_root.startswith("libs/") or p_root.startswith("packages/") or "/libs/" in p_root or "/packages/" in p_root
        )
        if is_app:
            for other_p, other_data in projects.items():
                if other_p == p_name:
                    continue
                o_root = other_data.get("_root") or other_data.get("root", "")
                is_lib = other_data.get("projectType") == "library" or o_root.startswith("libs/") or o_root.startswith("packages/") or "/libs/" in o_root or "/packages/" in o_root
                if is_lib:
                    deps.add(other_p)

    return deps


def build_dag_and_sort(
    projects: Dict[str, Dict[str, Any]], target_name: str, selected_projects: Optional[List[str]] = None, return_waves: bool = False
) -> Any:
    if selected_projects is None:
        selected_projects = list(projects.keys())
    # Nodes: (project_name, target_name)
    nodes: Set[Tuple[str, str]] = set()
    graph: Dict[Tuple[str, str], Set[Tuple[str, str]]] = collections.defaultdict(set)
    in_degree: Dict[Tuple[str, str], int] = collections.defaultdict(int)

    for p_name in selected_projects:
        p_data = projects.get(p_name)
        if not p_data or "targets" not in p_data:
            continue
        if target_name in p_data["targets"]:
            node = (p_name, target_name)
            nodes.add(node)
            depends_on = p_data["targets"][target_name].get("dependsOn", [])
            for dep in depends_on:
                if dep.startswith("^"):
                    # Depends on upstream target across declared/detected dependency projects (DEFECT-03)
                    upstream_target = dep[1:]
                    upstream_projects = get_project_dependencies(p_name, p_data, projects)
                    for up_p in upstream_projects:
                        if up_p in projects and upstream_target in projects[up_p].get("targets", {}):
                            parent_node = (up_p, upstream_target)
                            nodes.add(parent_node)
                            graph[parent_node].add(node)
                elif ":" in dep:
                    # Cross-project target dependency (DEFECT-09)
                    dep_p, dep_t = dep.split(":", 1)
                    if dep_p in projects and dep_t in projects[dep_p].get("targets", {}):
                        parent_node = (dep_p, dep_t)
                        nodes.add(parent_node)
                        graph[parent_node].add(node)
                    else:
                        print(f"[WARN] Dependency '{dep}' referenced by '{p_name}:{target_name}' not found.", file=sys.stderr)
                else:
                    # Depends on local target on same project
                    local_dep = (p_name, dep)
                    nodes.add(local_dep)
                    graph[local_dep].add(node)

    for node in nodes:
        if node not in in_degree:
            in_degree[node] = 0
    for parent, children in graph.items():
        for ch in children:
            in_degree[ch] += 1

    waves: List[List[Tuple[str, str]]] = []
    ordered: List[Tuple[str, str]] = []
    current_wave = [n for n in nodes if in_degree[n] == 0]

    while current_wave:
        waves.append(sorted(current_wave))
        next_wave = []
        for curr in current_wave:
            ordered.append(curr)
            for neighbor in graph[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_wave.append(neighbor)
        current_wave = next_wave

    cycles = [n for n in nodes if in_degree[n] > 0]
    cycle_errors = [f"Cyclic dependency detected involving target {c[0]}:{c[1]}" for c in cycles]

    if return_waves:
        return ordered, cycle_errors, waves
    return ordered, cycle_errors


def cmd_run(args: argparse.Namespace) -> int:
    target_spec = args.target_spec  # Format: "project:target"
    if ":" not in target_spec:
        print(f"[ERROR] Target specification '{target_spec}' must follow format 'project:target'.", file=sys.stderr)
        return 1

    project_name, target_name = target_spec.split(":", 1)
    projects = discover_projects(getattr(args, "root", ".") or ".")

    if project_name not in projects:
        print(f"[ERROR] Project '{project_name}' not found in monorepo.", file=sys.stderr)
        return 1

    p_data = projects[project_name]
    targets = p_data.get("targets", {})
    if target_name not in targets:
        print(f"[ERROR] Target '{target_name}' not defined for project '{project_name}'.", file=sys.stderr)
        return 1

    ordered, cycle_errs = build_dag_and_sort(projects, target_name, [project_name])
    if cycle_errs:
        for err in cycle_errs:
            print(f"[FAIL] {err}", file=sys.stderr)
        return 1

    print(f"=== EP-OS Topological DAG Runner: {project_name}:{target_name} ===")
    print(f"Resolved execution pipeline ({len(ordered)} step(s)):")
    for p, t in ordered:
        print(f"  • {p}:{t}")

    for p, t in ordered:
        t_cfg = projects[p]["targets"][t]
        p_root = projects[p].get("_root") or projects[p].get("root", "")
        print(f"\n--> Running {p}:{t}...")
        rc, out, elapsed = execute_target(p, t, t_cfg, p_root)
        if out:
            print(out)
        if rc != 0:
            print(f"\n[FAIL] Step '{p}:{t}' failed with exit code {rc}.", file=sys.stderr)
            return rc
        print(f"[PASS] {p}:{t} ({elapsed:.2f}s)")

    print(f"\n[SUCCESS] Pipeline {project_name}:{target_name} completed cleanly.")
    return 0


def cmd_run_many(args: argparse.Namespace) -> int:
    target_name = args.target
    root_dir = getattr(args, "root", ".") or "."
    projects = discover_projects(root_dir)

    selected: List[str] = []
    if getattr(args, "projects", None):
        selected = [p.strip() for p in args.projects.split(",") if p.strip()]
    elif getattr(args, "affected", False):
        base = getattr(args, "base", "origin/main") or "origin/main"
        res = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True, check=False, timeout=30)
        diff_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
        for p_name, p_data in projects.items():
            p_prefix = p_data["_root"].lstrip("./") + "/"
            if any(f.startswith(p_prefix) for f in diff_files):
                selected.append(p_name)
        if not selected:
            print("[INFO] Zero affected projects detected in git diff.")
            return 0
    else:
        selected = list(projects.keys())

    # Filter to projects implementing target_name
    valid_selected = [p for p in selected if p in projects and target_name in projects[p].get("targets", {})]
    if not valid_selected:
        print(f"[INFO] Zero projects implement target '{target_name}'.")
        return 0

    ordered, cycle_errs, waves = build_dag_and_sort(projects, target_name, valid_selected, return_waves=True)
    if cycle_errs:
        for err in cycle_errs:
            print(f"[FAIL] {err}", file=sys.stderr)
        return 1

    parallel = getattr(args, "parallel", False)
    print(f"=== EP-OS Topological DAG Runner (Target: '{target_name}') ===")
    print(f"Executing {len(ordered)} step(s) across {len(valid_selected)} project(s) (parallel={parallel}):")

    failures = 0
    if parallel:
        for wave_idx, wave in enumerate(waves):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_step = {
                    executor.submit(execute_target, p, t, projects[p]["targets"][t], projects[p]["_root"]): (p, t)
                    for p, t in wave
                }
                for fut in concurrent.futures.as_completed(future_to_step):
                    p, t = future_to_step[fut]
                    rc, out, elapsed = fut.result()
                    if rc == 0:
                        print(f"  [PASS] {p}:{t} ({elapsed:.2f}s)")
                    else:
                        print(f"  [FAIL] {p}:{t} -> {out}", file=sys.stderr)
                        failures += 1
            if failures > 0:
                print(f"[FAIL] Wave {wave_idx + 1} encountered {failures} failure(s); aborting downstream execution.", file=sys.stderr)
                break
    else:
        for p, t in ordered:
            t_cfg = projects[p]["targets"][t]
            p_root = projects[p]["_root"]
            rc, out, elapsed = execute_target(p, t, t_cfg, p_root)
            if rc == 0:
                print(f"  [PASS] {p}:{t} ({elapsed:.2f}s)")
            else:
                print(f"  [FAIL] {p}:{t} -> {out}", file=sys.stderr)
                failures += 1

    if failures > 0:
        print(f"\n[FAIL] {failures} target(s) failed execution.", file=sys.stderr)
        return 1

    print(f"\n[SUCCESS] All {len(ordered)} steps completed successfully.")
    return 0
