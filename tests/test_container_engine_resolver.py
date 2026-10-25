#!/usr/bin/env python3
"""
Unit and integration tests for EP-OS OCI Container Engine Resolver (scripts/ep_ops.py & scripts/ep.py).
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
EP_SCRIPT = REPO_ROOT / "scripts" / "ep.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ep_ops import (
    cmd_container,
    get_container_install_instructions,
    probe_engine_liveness,
    resolve_container_engine,
)


class TestContainerEngineResolver(unittest.TestCase):
    def test_install_instructions_platforms(self):
        linux_instr = get_container_install_instructions("linux")
        self.assertTrue(any("apt-get" in s for s in linux_instr))
        self.assertTrue(any("dnf" in s for s in linux_instr))

        mac_instr = get_container_install_instructions("darwin")
        self.assertTrue(any("brew install podman" in s for s in mac_instr))

        win_instr = get_container_install_instructions("win32")
        self.assertTrue(any("winget" in s for s in win_instr))
        self.assertTrue(any("WSL2" in s for s in win_instr))

    @patch("shutil.which")
    @patch("scripts.ep_ops.probe_engine_liveness")
    def test_both_engines_podman_alive_selects_podman(self, mock_liveness, mock_which):
        mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("podman", "docker") else None
        mock_liveness.side_effect = lambda path, timeout=2.5: True if "podman" in path else True

        res = resolve_container_engine(check_liveness=True)
        self.assertEqual(res["status"], "available")
        self.assertEqual(res["selected"], "podman")
        self.assertTrue(res["alive"])
        self.assertIn("Podman selected", res["reason"])
        self.assertEqual(res["engines_found"], ["podman", "docker"])

    @patch("shutil.which")
    @patch("scripts.ep_ops.probe_engine_liveness")
    def test_both_engines_podman_down_docker_alive_selects_docker(self, mock_liveness, mock_which):
        mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("podman", "docker") else None
        # podman is dead, docker is alive
        mock_liveness.side_effect = lambda path, timeout=2.5: False if "podman" in path else True

        res = resolve_container_engine(check_liveness=True)
        self.assertEqual(res["status"], "available")
        self.assertEqual(res["selected"], "docker")
        self.assertTrue(res["alive"])
        self.assertIn("Docker selected", res["reason"])

    @patch("shutil.which")
    @patch("scripts.ep_ops.probe_engine_liveness")
    def test_both_engines_both_inactive_defaults_podman_warning(self, mock_liveness, mock_which):
        mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("podman", "docker") else None
        mock_liveness.return_value = False

        res = resolve_container_engine(check_liveness=True)
        self.assertEqual(res["status"], "inactive")
        self.assertEqual(res["selected"], "podman")
        self.assertFalse(res["alive"])
        self.assertIn("inactive", res["reason"])

    @patch("shutil.which")
    @patch("scripts.ep_ops.probe_engine_liveness")
    def test_only_docker_available(self, mock_liveness, mock_which):
        mock_which.side_effect = lambda name: "/usr/bin/docker" if name == "docker" else None
        mock_liveness.return_value = True

        res = resolve_container_engine(check_liveness=True)
        self.assertEqual(res["status"], "available")
        self.assertEqual(res["selected"], "docker")
        self.assertEqual(res["engines_found"], ["docker"])

    @patch("shutil.which")
    @patch("scripts.ep_ops.probe_engine_liveness")
    def test_neither_engine_available(self, mock_liveness, mock_which):
        mock_which.return_value = None

        res = resolve_container_engine(check_liveness=True)
        self.assertEqual(res["status"], "missing")
        self.assertIsNone(res["selected"])
        self.assertFalse(res["alive"])
        self.assertIn("No OCI container engine", res["reason"])
        self.assertTrue(len(res["install_instructions"]) > 0)

    def test_cli_container_status_live(self):
        proc = subprocess.run(
            [sys.executable, str(EP_SCRIPT), "container", "status"],
            capture_output=True,
            text=True,
        )
        self.assertIn("EP-OS OCI Container Engine Resolver", proc.stdout)

    def test_cli_container_json_live(self):
        proc = subprocess.run(
            [sys.executable, str(EP_SCRIPT), "container", "--json"],
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertIn("status", data)
        self.assertIn("platform", data)
        self.assertIn("engines_found", data)


if __name__ == "__main__":
    unittest.main()
