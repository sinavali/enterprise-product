import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.ep_vcs import pack_release


class TestEpReleasePack(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_zip = os.path.join(self.temp_dir, "Packed.zip")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pack_release_creates_zip(self):
        args = argparse.Namespace(
            output=self.output_zip,
            max_files=30,
            root=REPO_ROOT,
        )
        rc = pack_release(args)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(self.output_zip))
        self.assertGreater(os.path.getsize(self.output_zip), 0)

    def test_pack_release_file_count_strictly_within_ceiling(self):
        args = argparse.Namespace(
            output=self.output_zip,
            max_files=30,
            root=REPO_ROOT,
        )
        rc = pack_release(args)
        self.assertEqual(rc, 0)

        with zipfile.ZipFile(self.output_zip, "r") as zf:
            namelist = zf.namelist()
            self.assertLessEqual(len(namelist), 30, f"Packed files count {len(namelist)} must be <= 30")
            self.assertEqual(len(namelist), 29, f"Expected exactly 29 minimal runtime files, got {len(namelist)}")

    def test_pack_release_contains_mandatory_files(self):
        args = argparse.Namespace(
            output=self.output_zip,
            max_files=30,
            root=REPO_ROOT,
        )
        pack_release(args)

        with zipfile.ZipFile(self.output_zip, "r") as zf:
            namelist = set(zf.namelist())
            expected_root_files = {
                "ep",
                "SKILL.md",
                "PRODUCT_SKILL.md",
                "AGENT.md",
                "README.md",
                "LICENSE",
                "project.json",
                "scripts/ep.py",
                "scripts/ep_vcs.py",
                "scripts/ep_ops.py",
                "scripts/ep_runner.py",
                "scripts/ep_doctor.py",
                "scripts/audit-runner.py",
            }
            for rf in expected_root_files:
                self.assertIn(rf, namelist, f"Mandatory file '{rf}' missing from Packed.zip")

    def test_pack_release_exceeding_max_files_fails(self):
        args = argparse.Namespace(
            output=self.output_zip,
            max_files=10,  # Below the required 29 files
            root=REPO_ROOT,
        )
        rc = pack_release(args)
        self.assertEqual(rc, 1, "pack_release should fail when selected files exceed max_files ceiling")
        self.assertFalse(os.path.exists(self.output_zip))

    def test_pack_release_executable_bits(self):
        args = argparse.Namespace(
            output=self.output_zip,
            max_files=30,
            root=REPO_ROOT,
        )
        pack_release(args)

        with zipfile.ZipFile(self.output_zip, "r") as zf:
            ep_info = zf.getinfo("ep")
            # Upper 16 bits of external_attr hold POSIX permissions
            perm = (ep_info.external_attr >> 16) & 0o777
            self.assertEqual(perm, 0o755, f"Entrypoint 'ep' should have 0o755 permissions, got {oct(perm)}")

    def test_cli_release_pack_integration(self):
        cmd = [
            sys.executable,
            os.path.join(REPO_ROOT, "scripts", "ep.py"),
            "release",
            "pack",
            "--output",
            self.output_zip,
            "--max-files",
            "30",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, timeout=30)
        self.assertEqual(res.returncode, 0, f"CLI ep release pack failed: {res.stderr}")
        self.assertIn("[OK] Release zip binary created successfully", res.stdout)
        self.assertTrue(os.path.isfile(self.output_zip))

    def test_extracted_package_runs_help(self):
        args = argparse.Namespace(
            output=self.output_zip,
            max_files=30,
            root=REPO_ROOT,
        )
        pack_release(args)

        extract_dir = os.path.join(self.temp_dir, "extracted")
        with zipfile.ZipFile(self.output_zip, "r") as zf:
            zf.extractall(extract_dir)

        ep_bin = os.path.join(extract_dir, "ep")
        os.chmod(ep_bin, 0o755)

        res = subprocess.run([ep_bin, "--help"], capture_output=True, text=True, cwd=extract_dir, timeout=20)
        self.assertEqual(res.returncode, 0, f"Extracted ep binary failed: {res.stderr}")
        self.assertIn("Unified Mechanical CLI for Enterprise-Product Engineering OS (EP-OS)", res.stdout)


if __name__ == "__main__":
    unittest.main()
