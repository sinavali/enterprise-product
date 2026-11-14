#!/usr/bin/env python3
"""
Unit tests for architectural boundary checks in ep_quality.py.
Verifies DDD & Hexagonal boundary enforcement across polyglot languages:
- Inverted dependency detection (domain importing application)
- Cloud SDK detection in domain
- Network transport / HTTP client detection in domain
- Infrastructure / adapter detection
- Comment stripping and ep-boundary-exempt handling
"""

import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ep_quality import check_boundaries


class TestBoundaryChecks(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run_boundary_check(self):
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = check_boundaries(self.temp_dir)
        return rc, buf_out.getvalue(), buf_err.getvalue()

    def test_domain_importing_application_ts(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "user.ts")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import { UserService } from '../application/user.service';\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("application layer", err.lower())

    def test_domain_importing_application_py_relative(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "user.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("from ..application.services import UserService\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("application layer", err.lower())

    def test_domain_importing_application_py_absolute(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "user.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("from src.application.services import UserService\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("application layer", err.lower())

    def test_domain_importing_application_go(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "user.go")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write('package domain\n\nimport "myorg/pkg/application"\n')
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("application layer", err.lower())

    def test_domain_importing_application_csharp(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "User.cs")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("using MyOrg.Project.Application;\nnamespace Domain;\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("application layer", err.lower())

    def test_application_importing_domain_passes(self):
        a_dir = os.path.join(self.temp_dir, "services", "orders", "src", "application")
        os.makedirs(a_dir, exist_ok=True)
        f_path = os.path.join(a_dir, "service.ts")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import { User } from '../domain/user';\n")
        rc, out, _ = self._run_boundary_check()
        self.assertEqual(rc, 0)
        self.assertIn("[OK]", out)

    def test_domain_importing_boto3(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "storage.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import boto3\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("Cloud SDK", err)

    def test_domain_importing_aws_sdk_ts(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "storage.ts")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import { S3Client } from '@aws-sdk/client-s3';\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("Cloud SDK", err)

    def test_domain_importing_google_cloud_py(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "storage.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("from google.cloud import storage\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("Cloud SDK", err)

    def test_domain_importing_azure_storage_py(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "storage.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("from azure.storage.blob import BlobServiceClient\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("Cloud SDK", err)

    def test_domain_importing_stripe_py(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "payment.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import stripe\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("Cloud SDK", err)

    def test_domain_importing_requests(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "client.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import requests\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("network transport", err)

    def test_domain_importing_axios(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "client.ts")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import axios from 'axios';\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("network transport", err)

    def test_domain_importing_urllib(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "client.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import urllib.request\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("network transport", err)

    def test_domain_importing_node_http(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "client.ts")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import http from 'http';\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("network transport", err)

    def test_domain_commented_out_import_passes(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "user.ts")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("// import { PrismaClient } from 'prisma';\n/* import axios from 'axios'; */\n# import boto3\nexport class User {}\n")
        rc, out, _ = self._run_boundary_check()
        self.assertEqual(rc, 0)
        self.assertIn("[OK]", out)

    def test_domain_variable_named_application_passes(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "application.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("class JobApplication:\n    def __init__(self, application_id: str):\n        self.application_id = application_id\n")
        rc, out, _ = self._run_boundary_check()
        self.assertEqual(rc, 0)
        self.assertIn("[OK]", out)

    def test_domain_boundary_exempt_passes(self):
        d_dir = os.path.join(self.temp_dir, "services", "orders", "src", "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "exempt.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("# ep-boundary-exempt\nimport boto3\n")
        rc, out, _ = self._run_boundary_check()
        self.assertEqual(rc, 0)
        self.assertIn("[OK]", out)

    def test_root_domain_folder_detected(self):
        d_dir = os.path.join(self.temp_dir, "domain")
        os.makedirs(d_dir, exist_ok=True)
        f_path = os.path.join(d_dir, "user.py")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import boto3\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("Cloud SDK", err)

    def test_lib_imports_service_via_php_use_fails(self):
        lib_dir = os.path.join(self.temp_dir, "libs", "shared", "src")
        os.makedirs(lib_dir, exist_ok=True)
        f_path = os.path.join(lib_dir, "Helper.php")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("<?php\nnamespace Libs\\Shared;\nuse apps\\users\\UserService;\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("Library/shared package imports application or service code", err)

    def test_lib_imports_service_via_dart_package_fails(self):
        pkg_dir = os.path.join(self.temp_dir, "packages", "common", "lib")
        os.makedirs(pkg_dir, exist_ok=True)
        f_path = os.path.join(pkg_dir, "common.dart")
        with open(f_path, "w", encoding="utf-8") as fh:
            fh.write("import 'package:services/auth.dart';\n")
        rc, _, err = self._run_boundary_check()
        self.assertEqual(rc, 1)
        self.assertIn("Library/shared package imports application or service code", err)


if __name__ == "__main__":
    unittest.main()
