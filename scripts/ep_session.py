#!/usr/bin/env python3
"""
ep_session.py — Multi-Session Workspace, Pause/Resume & Incremental State Machine for EP-OS
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from scripts.ep_ops import atomic_write
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


def parse_porcelain_line(line: str) -> Optional[str]:
    if len(line) >= 4:
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            return raw_path.split(" -> ")[1].strip()
        return raw_path
    return None


def cmd_session(args: argparse.Namespace) -> int:
    session_root = ".ep/sessions"
    os.makedirs(session_root, exist_ok=True)
    registry_file = os.path.join(session_root, "registry.json")

    action = args.action
    session_id = args.session_id or "default"

    if action == "save":
        session_dir = os.path.join(session_root, session_id)
        os.makedirs(session_dir, exist_ok=True)

        existing = [f for f in os.listdir(session_dir) if re.match(r"^\d{4}_state\.json$", f)]
        next_seq = 1
        if existing:
            seqs = [int(f.split("_")[0]) for f in existing]
            next_seq = max(seqs) + 1

        branch_res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False, timeout=30)
        current_branch = branch_res.stdout.strip() if branch_res.returncode == 0 else "unknown"
        status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False, timeout=30)
        modified = []
        for line in status_res.stdout.splitlines():
            p = parse_porcelain_line(line)
            if p:
                modified.append(p)

        state = {
            "session_id": session_id,
            "seq": next_seq,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "mode": args.mode or "implement",
            "task": args.task or "active-task",
            "branch": current_branch,
            "modified_files": modified,
            "notes": args.notes or "",
        }

        filename = f"{next_seq:04d}_state.json"
        state_path = os.path.join(session_dir, filename)
        atomic_write(state_path, json.dumps(state, indent=2) + "\n")

        current_path = os.path.join(session_dir, "current.json")
        atomic_write(current_path, json.dumps(state, indent=2) + "\n")

        registry = {}
        if os.path.exists(registry_file):
            try:
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                registry = {}
        registry[session_id] = {
            "latest_seq": next_seq,
            "last_heartbeat": state["timestamp"],
            "branch": current_branch,
            "task": state["task"],
            "mode": state["mode"],
        }
        atomic_write(registry_file, json.dumps(registry, indent=2) + "\n")

        # Retention pruning (keep latest 15)
        all_states = sorted([f for f in os.listdir(session_dir) if re.match(r"^\d{4}_state\.json$", f)])
        if len(all_states) > 15:
            for p_file in all_states[:-15]:
                try:
                    os.remove(os.path.join(session_dir, p_file))
                except Exception:
                    pass

        print(f"[OK] Checkpoint saved: '{session_id}/{filename}' (seq {next_seq}). Active modified files: {len(modified)}.")
        return 0

    elif action == "resume":
        session_dir = os.path.join(session_root, session_id)
        if not os.path.exists(session_dir):
            print(f"[ERROR] Session directory '{session_dir}' does not exist.", file=sys.stderr)
            return 1

        all_states = sorted([f for f in os.listdir(session_dir) if re.match(r"^\d{4}_state\.json$", f)])
        if not all_states:
            print(f"[ERROR] No state checkpoints found in '{session_dir}'.", file=sys.stderr)
            return 1

        latest_file = all_states[-1]
        with open(os.path.join(session_dir, latest_file), "r", encoding="utf-8") as f:
            state = json.load(f)

        print(f"=== EP-OS RESUME: Session '{session_id}' (Checkpoint {latest_file}) ===")
        print(f"- Task: {state.get('task')}")
        print(f"- Mode: {state.get('mode')}")
        print(f"- Branch: {state.get('branch')}")
        print(f"- Timestamp: {state.get('timestamp')}")
        print(f"- Modified files ({len(state.get('modified_files', []))}):")
        for mf in state.get("modified_files", [])[:10]:
            print(f"  • {mf}")
        return 0

    elif action == "list":
        if not os.path.exists(registry_file):
            print("No active sessions registered.")
            return 0
        with open(registry_file, "r", encoding="utf-8") as f:
            reg = json.load(f)
        print("=== Active EP-OS Sessions ===")
        for sid, meta in reg.items():
            print(f"• {sid} (seq {meta.get('latest_seq')} | task: {meta.get('task')} | mode: {meta.get('mode')} | {meta.get('last_heartbeat')})")
        return 0

    elif action == "prune":
        pruned_count = 0
        for entry in os.listdir(session_root):
            entry_path = os.path.join(session_root, entry)
            if os.path.isdir(entry_path):
                states = sorted([f for f in os.listdir(entry_path) if re.match(r"^\d{4}_state\.json$", f)])
                if len(states) > 15:
                    for old_file in states[:-15]:
                        os.remove(os.path.join(entry_path, old_file))
                        pruned_count += 1
        print(f"[OK] Pruned {pruned_count} historical session state files.")
        return 0

    elif action == "check-collision":
        if not os.path.exists(registry_file):
            print("[OK] No active sessions registered. Zero collisions.")
            return 0
        with open(registry_file, "r", encoding="utf-8") as f:
            reg = json.load(f)

        session_files: Dict[str, Set[str]] = {}
        for sid in reg.keys():
            curr_path = os.path.join(session_root, sid, "current.json")
            if os.path.exists(curr_path):
                try:
                    with open(curr_path, "r", encoding="utf-8") as cf:
                        s_data = json.load(cf)
                    session_files[sid] = set(s_data.get("modified_files", []))
                except Exception:
                    pass

        collisions = []
        target_sids = [session_id] if session_id != "default" and session_id in session_files else list(session_files.keys())
        checked_pairs = set()

        for s1 in target_sids:
            for s2, files2 in session_files.items():
                if s1 == s2:
                    continue
                pair_key = tuple(sorted([s1, s2]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                overlap = session_files.get(s1, set()).intersection(files2)
                if overlap:
                    collisions.append((s1, s2, sorted(list(overlap))))

        if collisions:
            print("[COLLISION] Concurrent Session Mutation Conflict Detected!", file=sys.stderr)
            for coll_s1, coll_s2, coll_overlap in collisions:
                print(f"  ❌ Conflict between Session '{coll_s1}' and '{coll_s2}':", file=sys.stderr)
                for coll_f in coll_overlap:
                    print(f"     • {coll_f}", file=sys.stderr)
            print("\nRemediation: Commit or stash changes before switching contexts, or coordinate worktree separation.", file=sys.stderr)
            return 1

        print(f"[OK] Concurrency Clean: Zero collisions detected across {len(session_files)} active session(s).")
        return 0

    return 0
