"""
Shared fixtures and test utilities for EP-OS End-to-End (E2E) opaque-box tests.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EP_SCRIPT = REPO_ROOT / "scripts" / "ep.py"
EP_BIN = REPO_ROOT / "scripts" / "bin" / "ep"


class EpCliRunner:
    """Helper runner to invoke EP-OS CLI as an opaque external process."""

    def __init__(self, script_path: Path = EP_SCRIPT, bin_path: Path = EP_BIN):
        self.script_path = script_path
        self.bin_path = bin_path

    def run(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        use_bin: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run CLI with args and return CompletedProcess."""
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        if use_bin and self.bin_path.exists() and os.access(self.bin_path, os.X_OK):
            cmd = [str(self.bin_path)] + args
        else:
            cmd = [sys.executable, str(self.script_path)] + args

        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else str(REPO_ROOT),
            env=full_env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )


@pytest.fixture(scope="session")
def ep_runner() -> EpCliRunner:
    """Session-scoped CLI runner."""
    return EpCliRunner()


@pytest.fixture
def temp_dir():
    """Provides a pristine temporary directory, automatically cleaned up."""
    d = tempfile.mkdtemp(prefix="ep_e2e_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def temp_git_repo(temp_dir: Path):
    """Provides an isolated initialized git repository."""
    subprocess.run(["git", "init", "-b", "main"], cwd=str(temp_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test-agent@example.com"], cwd=str(temp_dir), check=True)
    subprocess.run(["git", "config", "user.name", "Test Agent"], cwd=str(temp_dir), check=True)

    # Base commit with minimal project contract
    root_pj = temp_dir / "project.json"
    root_pj.write_text(json.dumps({
        "name": "enterprise-monorepo",
        "tags": ["profile:a", "scope:backend"],
        "targets": {
            "lint": {"executor": "nx:run-commands", "options": {"command": "echo lint"}},
            "test": {"executor": "nx:run-commands", "options": {"command": "echo test"}},
            "build": {"executor": "nx:run-commands", "options": {"command": "echo build"}},
            "audit": {"executor": "nx:run-commands", "options": {"command": "echo audit"}}
        }
    }, indent=2), encoding="utf-8")

    root_agent = temp_dir / "AGENT.md"
    root_agent.write_text(
        "# Enterprise Agent Manifest\n"
        "At session start or immediately following context compaction/memory reset, "
        "AI agents MUST re-read `SKILL.md` before executing tasks or proposing code changes.\n\n"
        "## Tier 1 Inviolables\n"
        "- Pure domain\n- Inward dependencies\n",
        encoding="utf-8"
    )

    # Initialize .ep directory
    (temp_dir / ".ep" / "cache").mkdir(parents=True, exist_ok=True)
    (temp_dir / ".ep" / "surfaces").mkdir(parents=True, exist_ok=True)
    (temp_dir / ".ep" / "sessions").mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "add", "."], cwd=str(temp_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "chore: initialize monorepo base"], cwd=str(temp_dir), check=True, capture_output=True)

    yield temp_dir
