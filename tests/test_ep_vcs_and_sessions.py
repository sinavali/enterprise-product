#!/usr/bin/env python3
"""
Unit and integration tests for EP-OS Multi-Session, VCS Governance,
Universal Manifest Projection, and Polyglot Stack Detection.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EP_SCRIPT = REPO_ROOT / "scripts" / "ep.py"

from scripts.ep import detect_stack, LocalGitProvider


class TestEpVcsAndSessions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_ep(self, args, cwd=None):
        cmd = [sys.executable, str(EP_SCRIPT)] + args
        return subprocess.run(
            cmd,
            cwd=cwd or self.temp_dir,
            capture_output=True,
            text=True,
        )

    def test_preflight_gate(self):
        proc = self.run_ep(["preflight"])
        self.assertEqual(proc.returncode, 0, f"Error: {proc.stderr}")
        self.assertIn("[PASS] Shell Execution", proc.stdout)
        self.assertIn("[PASS] Version Control", proc.stdout)
        self.assertIn("[OK] Preflight Verified", proc.stdout)

    def test_session_save_and_resume_and_retention(self):
        session_id = "agent-alpha"

        # Save 18 checkpoints to verify incremental numbering and 15-file retention
        for i in range(1, 19):
            proc = self.run_ep([
                "session", "save",
                "--session-id", session_id,
                "--task", f"Task-{i}",
                "--mode", "implement"
            ])
            self.assertEqual(proc.returncode, 0, f"Error at step {i}: {proc.stderr}")

        session_dir = os.path.join(self.temp_dir, ".ep", "sessions", session_id)
        self.assertTrue(os.path.isdir(session_dir))

        # Check total remaining files (should be max 15 state files + 1 current.json)
        state_files = sorted([f for f in os.listdir(session_dir) if f.endswith("_state.json")])
        self.assertEqual(len(state_files), 15)
        # Oldest file should be 0004_state.json (1, 2, 3 pruned)
        self.assertEqual(state_files[0], "0004_state.json")
        self.assertEqual(state_files[-1], "0018_state.json")

        # Resume session
        resume_proc = self.run_ep(["session", "resume", "--session-id", session_id])
        self.assertEqual(resume_proc.returncode, 0)
        self.assertIn("Checkpoint 0018_state.json", resume_proc.stdout)
        self.assertIn("Task-18", resume_proc.stdout)

        # List sessions
        list_proc = self.run_ep(["session", "list"])
        self.assertEqual(list_proc.returncode, 0)
        self.assertIn("agent-alpha", list_proc.stdout)

    def test_manifest_projection_sync(self):
        # Create root AGENT.md
        root_agent = os.path.join(self.temp_dir, "AGENT.md")
        with open(root_agent, "w", encoding="utf-8") as f:
            f.write("# Root AGENT Manifest\n\nAll projects must follow DDD and Hexagonal architecture.\n")

        # Create subproject AGENT.md
        sub_dir = os.path.join(self.temp_dir, "services", "auth")
        os.makedirs(sub_dir, exist_ok=True)
        sub_agent = os.path.join(sub_dir, "AGENT.md")
        with open(sub_agent, "w", encoding="utf-8") as f:
            f.write("# Auth Service AGENT\nProfile: A\n")

        # Run manifest sync
        proc = self.run_ep(["manifest", "sync", "--root", self.temp_dir])
        self.assertEqual(proc.returncode, 0, f"Error: {proc.stderr}")
        self.assertIn("[OK] Manifest projection complete", proc.stdout)

        # Check projected files
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "CLAUDE.md")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, ".cursorrules")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, ".windsurfrules")))
        self.assertTrue(os.path.exists(os.path.join(sub_dir, "CLAUDE.md")))

        with open(os.path.join(self.temp_dir, "CLAUDE.md"), "r") as f:
            content = f.read()
        self.assertIn("All projects must follow DDD", content)

    def test_root_manifest_re_read_directive_and_projection_sync(self):
        root_agent = os.path.join(REPO_ROOT, "AGENT.md")
        self.assertTrue(os.path.exists(root_agent), "AGENT.md must exist at repo root")
        with open(root_agent, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify AGENT.md contains the re-read mandate
        self.assertIn("MANDATORY SESSION RESTORATION & SKILL RE-READ DIRECTIVE", content)
        self.assertIn("SKILL.md", content)

        # Execute manifest sync on repo root
        proc = self.run_ep(["manifest", "sync", "--root", str(REPO_ROOT)])
        self.assertEqual(proc.returncode, 0, f"ep manifest sync failed: {proc.stderr}")

        # Verify projections exist and contain the directive
        for proj_file in ["CLAUDE.md", ".cursorrules", ".windsurfrules"]:
            proj_path = os.path.join(REPO_ROOT, proj_file)
            self.assertTrue(os.path.exists(proj_path), f"Projection file '{proj_file}' missing")
            with open(proj_path, "r", encoding="utf-8") as f:
                proj_content = f.read()
            self.assertIn("MANDATORY SESSION RESTORATION & SKILL RE-READ DIRECTIVE", proj_content,
                          f"Projection '{proj_file}' is missing the re-read directive")
            self.assertIn("SKILL.md", proj_content)

    def test_vcs_sync_check_and_topology(self):
        # Setup git repo in temp_dir
        subprocess.run(["git", "init", "-b", "main"], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "tester@test.com"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.temp_dir, check=True)

        with open(os.path.join(self.temp_dir, "README.md"), "w") as f:
            f.write("Root\n")
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.temp_dir, check=True)

        # Create synchronized test and stage branches
        subprocess.run(["git", "branch", "test", "main"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "branch", "stage", "main"], cwd=self.temp_dir, check=True)

        # Run sync-check (should pass)
        proc_ok = self.run_ep(["vcs", "sync-check", "--base", "main"], cwd=self.temp_dir)
        self.assertEqual(proc_ok.returncode, 0, f"Expected 0: {proc_ok.stdout}")
        self.assertIn("Zero rogue commits detected", proc_ok.stdout)

        # Introduce rogue unmerged commit directly on 'test' branch
        subprocess.run(["git", "checkout", "test"], cwd=self.temp_dir, check=True)
        with open(os.path.join(self.temp_dir, "rogue.txt"), "w") as f:
            f.write("rogue\n")
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "rogue commit on test"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "checkout", "main"], cwd=self.temp_dir, check=True)

        # Run sync-check (should FAIL)
        proc_fail = self.run_ep(["vcs", "sync-check", "--base", "main"], cwd=self.temp_dir)
        self.assertEqual(proc_fail.returncode, 1, f"Expected 1: {proc_fail.stdout}")
        self.assertIn("Topology Drift Detected", proc_fail.stderr)

    def test_pr_create_prod_local_gate(self):
        local_provider = LocalGitProvider()
        res = local_provider.create_prod_pr("Release v3.0.0", "Release candidate description", "feat-billing", root_dir=self.temp_dir)
        self.assertEqual(res, 0)
        # Check generated record
        record_path = os.path.join(self.temp_dir, "docs", "releases", "PR_PROD_PENDING.md")
        self.assertTrue(os.path.exists(record_path))
        with open(record_path, "r") as f:
            content = f.read()
        self.assertIn("STRICT HUMAN-ONLY GATE", content)
        self.assertIn("Auto-Merge", content)
        self.assertIn("DISABLED", content)

    def test_release_and_milestone(self):
        # Git repo setup
        subprocess.run(["git", "init", "-b", "main"], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "tester@test.com"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.temp_dir, check=True)
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("1")
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.temp_dir, check=True)

        # Create release tag
        rel_proc = self.run_ep(["release", "create", "v1.4.0"], cwd=self.temp_dir)
        self.assertEqual(rel_proc.returncode, 0)
        self.assertIn("Created release tag 'v1.4.0'", rel_proc.stdout)

        # Create milestone
        ms_proc = self.run_ep(["milestone", "create", "M04-Compliance", "--due", "2026-12-01"], cwd=self.temp_dir)
        self.assertEqual(ms_proc.returncode, 0)
        ms_file = os.path.join(self.temp_dir, "docs", "milestones", "M04-Compliance.md")
        self.assertTrue(os.path.exists(ms_file))

    def test_polyglot_stack_detector(self):
        # Go project
        go_dir = os.path.join(self.temp_dir, "go_svc")
        os.makedirs(go_dir)
        with open(os.path.join(go_dir, "go.mod"), "w") as f:
            f.write("module example.com/test\n")
        self.assertEqual(detect_stack(go_dir)["lang"], "go")

        # Rust project
        rust_dir = os.path.join(self.temp_dir, "rust_svc")
        os.makedirs(rust_dir)
        with open(os.path.join(rust_dir, "Cargo.toml"), "w") as f:
            f.write("[package]\nname = 'test'\n")
        self.assertEqual(detect_stack(rust_dir)["lang"], "rust")

        # Flutter project
        dart_dir = os.path.join(self.temp_dir, "flutter_app")
        os.makedirs(dart_dir)
        with open(os.path.join(dart_dir, "pubspec.yaml"), "w") as f:
            f.write("name: test_app\n")
        self.assertEqual(detect_stack(dart_dir)["lang"], "dart")

        # Kotlin project
        kt_dir = os.path.join(self.temp_dir, "kt_app")
        os.makedirs(kt_dir)
        with open(os.path.join(kt_dir, "build.gradle.kts"), "w") as f:
            f.write("// kotlin gradle\n")
        self.assertEqual(detect_stack(kt_dir)["lang"], "kotlin")

    def test_session_collision_detection(self):
        # 1. Clean check with zero sessions
        proc_clean = self.run_ep(["session", "check-collision"], cwd=self.temp_dir)
        self.assertEqual(proc_clean.returncode, 0)
        self.assertIn("Zero collisions", proc_clean.stdout)

        # 2. Simulate Session Alpha modifying apps/web/src/App.tsx
        s_alpha_dir = os.path.join(self.temp_dir, ".ep", "sessions", "session-alpha")
        os.makedirs(s_alpha_dir, exist_ok=True)
        with open(os.path.join(s_alpha_dir, "current.json"), "w", encoding="utf-8") as f:
            json.dump({"session_id": "session-alpha", "modified_files": ["apps/web/src/App.tsx"]}, f)

        # Simulate Session Beta modifying the same file apps/web/src/App.tsx
        s_beta_dir = os.path.join(self.temp_dir, ".ep", "sessions", "session-beta")
        os.makedirs(s_beta_dir, exist_ok=True)
        with open(os.path.join(s_beta_dir, "current.json"), "w", encoding="utf-8") as f:
            json.dump({"session_id": "session-beta", "modified_files": ["apps/web/src/App.tsx", "libs/core/index.ts"]}, f)

        # Update registry
        reg_file = os.path.join(self.temp_dir, ".ep", "sessions", "registry.json")
        with open(reg_file, "w", encoding="utf-8") as f:
            json.dump({"session-alpha": {}, "session-beta": {}}, f)

        # Run collision check -> must fail with code 1
        proc_coll = self.run_ep(["session", "check-collision"], cwd=self.temp_dir)
        self.assertEqual(proc_coll.returncode, 1)
        self.assertIn("Concurrent Session Mutation Conflict Detected", proc_coll.stderr)
        self.assertIn("apps/web/src/App.tsx", proc_coll.stderr)


if __name__ == "__main__":
    unittest.main()
