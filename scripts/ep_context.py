#!/usr/bin/env python3
"""
ep_context.py — Single-Turn Context Ingestion & Bundle Engine for EP-OS
Eliminates multi-turn 'one-by-one' file reading roundtrip latency by packing
target files into a structured, LLM-ready bundle in a single execution.
"""

import argparse
import os
import re
import subprocess
import sys
from typing import List, Optional, Set, Tuple

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
    ".ep",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
    ".zip", ".tar", ".gz", ".7z", ".bin", ".exe", ".so", ".dylib",
    ".pyc", ".class", ".woff", ".woff2", ".ttf", ".eot"
}


def is_binary_file(filepath: str) -> bool:
    _, ext = os.path.splitext(filepath.lower())
    if ext in BINARY_EXTENSIONS:
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            return b"\0" in chunk
    except Exception:
        return True


def collect_files_from_surface(root_dir: str = ".") -> List[str]:
    """Extracts declared code surface files from the active Change Surface."""
    target_file = os.path.join(root_dir, "CHANGE_SURFACE.md")
    if not os.path.exists(target_file):
        changes_dir = os.path.join(root_dir, "docs", "changes")
        if os.path.exists(changes_dir):
            changes = sorted(
                [os.path.join(changes_dir, f) for f in os.listdir(changes_dir) if f.endswith(".md")],
                key=lambda p: os.path.getmtime(p),
            )
            if changes:
                target_file = changes[-1]

    if not os.path.exists(target_file):
        return []

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    code_surface_match = re.search(r"## 3\.\s*Code Surface.*?(?=## 4\.\s*Test Surface|\Z)", content, re.DOTALL | re.IGNORECASE)
    if not code_surface_match:
        return []

    surface_text = code_surface_match.group(0)
    raw_paths = re.findall(r"[`']([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)[`']", surface_text)
    resolved = []
    for p in sorted(list(set(raw_paths))):
        full_p = os.path.join(root_dir, p)
        if os.path.isfile(full_p) and not is_binary_file(full_p):
            resolved.append(p)
    return resolved


def collect_files_from_diff(base: str = "origin/main", root_dir: str = ".") -> List[str]:
    """Collects all modified, staged, and untracked files relative to base."""
    files: Set[str] = set()
    try:
        diff_target = base if ("..." in base or base in ("HEAD", "HEAD~1")) else f"{base}...HEAD"
        res = subprocess.run(["git", "diff", "--name-only", diff_target], cwd=root_dir, capture_output=True, text=True, check=False, timeout=30)
        if res.returncode == 0:
            for l in res.stdout.splitlines():
                if l.strip():
                    files.add(l.strip())

        res_staged = subprocess.run(["git", "diff", "--name-only", "--cached"], cwd=root_dir, capture_output=True, text=True, check=False, timeout=30)
        if res_staged.returncode == 0:
            for l in res_staged.stdout.splitlines():
                if l.strip():
                    files.add(l.strip())

        res_status = subprocess.run(["git", "status", "--porcelain"], cwd=root_dir, capture_output=True, text=True, check=False, timeout=30)
        if res_status.returncode == 0:
            for l in res_status.stdout.splitlines():
                if len(l) >= 4:
                    raw_path = l[3:].strip()
                    if " -> " in raw_path:
                        raw_path = raw_path.split(" -> ")[1].strip()
                    files.add(raw_path)
    except Exception:
        pass

    resolved = []
    for f in sorted(list(files)):
        full_p = os.path.join(root_dir, f)
        if os.path.isfile(full_p) and not is_binary_file(full_p):
            resolved.append(f)
    return resolved


def collect_files_from_scope(scope_dir: str, root_dir: str = ".") -> List[str]:
    """Recursively collects text files from a directory."""
    full_scope = os.path.join(root_dir, scope_dir)
    if not os.path.isdir(full_scope):
        return []

    collected = []
    for current_root, dirs, files in os.walk(full_scope):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for f in files:
            full_path = os.path.join(current_root, f)
            rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
            if os.path.isfile(full_path) and not is_binary_file(full_path):
                collected.append(rel_path)
    return sorted(collected)


def pack_files(
    file_list: List[str], max_lines: int = 800, root_dir: str = "."
) -> Tuple[str, int, int, int]:
    """Packs target files into a structured bundle string. Returns (content, count, total_lines, total_bytes)."""
    blocks = []
    total_lines = 0
    total_bytes = 0

    for rel_path in file_list:
        full_path = os.path.join(root_dir, rel_path)
        if not os.path.isfile(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            continue

        file_line_count = len(lines)
        if max_lines and file_line_count > max_lines:
            truncated_lines = lines[:max_lines]
            truncated_lines.append(f"\n... [TRUNCATED {file_line_count - max_lines} REMAINING LINES; EXCEEDED max_lines={max_lines}] ...\n")
            body = "".join(truncated_lines)
        else:
            body = "".join(lines)

        file_bytes = len(body.encode("utf-8"))
        total_lines += file_line_count
        total_bytes += file_bytes

        block = (
            f"=== [EP-OS CONTEXT BUNDLE: {rel_path}] ===\n"
            f"[LINES: {file_line_count} | BYTES: {file_bytes}]\n"
            f"{body}\n"
            f"=== [END: {rel_path}] ==="
        )
        blocks.append(block)

    bundle_str = "\n\n".join(blocks)
    return bundle_str, len(blocks), total_lines, total_bytes


def cmd_pack(args: argparse.Namespace) -> int:
    root_dir = getattr(args, "root", ".") or "."
    target_files: List[str] = []

    if getattr(args, "files", None):
        target_files = args.files
    elif getattr(args, "diff", None):
        base = args.diff if isinstance(args.diff, str) else "origin/main"
        target_files = collect_files_from_diff(base=base, root_dir=root_dir)
    elif getattr(args, "scope", None):
        target_files = collect_files_from_scope(args.scope, root_dir=root_dir)
    else:
        # Default: pack active Change Surface
        target_files = collect_files_from_surface(root_dir=root_dir)
        if not target_files:
            # Fallback to diff
            target_files = collect_files_from_diff(base="origin/main", root_dir=root_dir)

    if not target_files:
        print("[EP-OS PACK] No target files discovered to pack.", file=sys.stderr)
        return 0

    max_lines = getattr(args, "max_lines", 800) or 800
    bundle_str, count, lines, bytes_count = pack_files(target_files, max_lines=max_lines, root_dir=root_dir)

    out_file = getattr(args, "output", None)
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(bundle_str)
        print(f"[EP-OS PACK] Bundled {count} file(s) ({lines} lines, {bytes_count} bytes) into '{out_file}'.", file=sys.stderr)
    else:
        print(bundle_str)
        print(f"\n[EP-OS PACK] Successfully bundled {count} file(s) ({lines} lines, {bytes_count} bytes) in a single turn.", file=sys.stderr)

    return 0


def main():
    parser = argparse.ArgumentParser(description="EP-OS Context Bundle & Anti-Slowness Tool")
    parser.add_argument("--surface", action="store_true", help="Pack files declared in active Change Surface")
    parser.add_argument("--diff", nargs="?", const="origin/main", help="Pack files modified in git diff")
    parser.add_argument("--scope", help="Directory scope to pack")
    parser.add_argument("--files", nargs="+", help="Specific files to pack")
    parser.add_argument("--output", help="Output file path (default stdout)")
    parser.add_argument("--max-lines", type=int, default=800, help="Max lines per file")
    parser.add_argument("--root", default=".", help="Monorepo root")
    args = parser.parse_args()
    sys.exit(cmd_pack(args))


if __name__ == "__main__":
    main()
