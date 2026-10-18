#!/usr/bin/env python3
"""
ep_sync.py — Automated Bidirectional Skill Synchronization Engine for EP-OS
Keeps the active Antigravity skill directory (~/.gemini/config/skills/enterprise-product)
and the standalone Git workspace repository (/home/sinavali/Workspace/Work/Projects/enterprise-product)
in 100% cryptographic SHA-256 parity with zero manual file copying.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Set, Tuple

DEFAULT_SKILL_DIR = os.path.expanduser("~/.gemini/config/skills/enterprise-product")


def resolve_default_workspace_dir() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DEFAULT_WORKSPACE_DIR = resolve_default_workspace_dir()

TRACKED_SUBDIRS = ["scripts", "references", "templates", "tests"]
TRACKED_ROOT_FILES = ["SKILL.md", "README.md", "package.json", "tsconfig.json"]
EXCLUDED_PATTERNS = {"__pycache__", ".git", ".ep", ".cache", ".pytest_cache"}


def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def get_tracked_manifest(base_dir: str) -> Dict[str, str]:
    manifest: Dict[str, str] = {}
    if not os.path.exists(base_dir):
        return manifest

    for rf in TRACKED_ROOT_FILES:
        fp = os.path.join(base_dir, rf)
        if os.path.isfile(fp):
            manifest[rf] = sha256_file(fp)

    for sd in TRACKED_SUBDIRS:
        sd_path = os.path.join(base_dir, sd)
        if not os.path.exists(sd_path):
            continue
        for root, dirs, files in os.walk(sd_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_PATTERNS and not d.startswith(".")]
            for f in files:
                if f.endswith(".pyc") or f.startswith("."):
                    continue
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, base_dir).replace("\\", "/")
                manifest[rel_p] = sha256_file(full_p)

    return manifest


def sync_trees(source_dir: str, dest_dir: str) -> List[str]:
    updated_files = []
    source_manifest = get_tracked_manifest(source_dir)
    dest_manifest = get_tracked_manifest(dest_dir)

    for rel_path, src_hash in source_manifest.items():
        dst_hash = dest_manifest.get(rel_path)
        if dst_hash != src_hash:
            src_file = os.path.join(source_dir, rel_path)
            dst_file = os.path.join(dest_dir, rel_path)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)
            updated_files.append(rel_path)

    return updated_files


def cmd_sync_skill(args: argparse.Namespace) -> int:
    skill_dir = getattr(args, "skill_dir", None) or DEFAULT_SKILL_DIR
    workspace_dir = getattr(args, "workspace_dir", None) or DEFAULT_WORKSPACE_DIR
    direction = getattr(args, "direction", "to-workspace") or "to-workspace"
    check_only = getattr(args, "check", False)

    skill_dir = os.path.abspath(os.path.expanduser(skill_dir))
    workspace_dir = os.path.abspath(os.path.expanduser(workspace_dir))

    if not os.path.exists(skill_dir):
        print(f"[ERROR] Skill directory '{skill_dir}' does not exist.", file=sys.stderr)
        return 1
    if not os.path.exists(workspace_dir):
        print(f"[ERROR] Workspace directory '{workspace_dir}' does not exist.", file=sys.stderr)
        return 1

    skill_manifest = get_tracked_manifest(skill_dir)
    workspace_manifest = get_tracked_manifest(workspace_dir)

    all_paths = sorted(set(list(skill_manifest.keys()) + list(workspace_manifest.keys())))
    diffs = []
    for p in all_paths:
        h1 = skill_manifest.get(p)
        h2 = workspace_manifest.get(p)
        if h1 != h2:
            status = "DIFF" if (h1 and h2) else ("SKILL_ONLY" if h1 else "WORKSPACE_ONLY")
            diffs.append((p, status))

    print(f"=== EP-OS Skill Sync Status ===")
    print(f"Skill Dir:     {skill_dir}")
    print(f"Workspace Dir: {workspace_dir}")
    print(f"Total Tracked Files: {len(all_paths)}")
    print(f"Parity Drift:        {len(diffs)} file(s)")

    if check_only:
        if diffs:
            for p, st in diffs:
                print(f"  ❌ [{st}] {p}")
            return 1
        print("[PASS] Skill and workspace are in 100% cryptographic parity.")
        return 0

    if not diffs:
        print("[OK] Skill and workspace are already in 100% parity. Zero sync needed.")
        return 0

    if direction in ("to-workspace", "skill-to-workspace"):
        print(f"\n--> Syncing {len(diffs)} files from Skill to Workspace repository...")
        synced = sync_trees(skill_dir, workspace_dir)
    elif direction in ("to-skill", "workspace-to-skill"):
        print(f"\n--> Syncing {len(diffs)} files from Workspace to Skill directory...")
        synced = sync_trees(workspace_dir, skill_dir)
    else:
        print(f"[ERROR] Unknown sync direction '{direction}'.", file=sys.stderr)
        return 1

    print(f"[SUCCESS] Synchronized {len(synced)} file(s).")
    for s in synced:
        print(f"  ✅ {s}")

    # Re-verify parity
    post_skill = get_tracked_manifest(skill_dir)
    post_workspace = get_tracked_manifest(workspace_dir)
    residual = [p for p in post_skill if post_skill.get(p) != post_workspace.get(p)]
    if residual:
        print(f"[WARNING] Residual drift remains on {len(residual)} file(s).", file=sys.stderr)
        return 1

    print("[VERIFIED] Cryptographic SHA-256 parity achieved across both locations.")
    return 0
