#!/usr/bin/env python3
"""
tests/test_license_scanner.py — Comprehensive unit tests for Polyglot License Scanner (Feature 12).
Verifies license extraction, copyleft contagion detection (GPL, AGPL, SSPL, BUSL, etc.),
permissive licenses (MIT, Apache-2.0, BSD-3-Clause), and SBOM generation across:
- PHP: composer.json
- Dart / Flutter: pubspec.yaml
- Python: pyproject.toml, requirements.txt, Pipfile
- Go: go.mod
- C#: .csproj, packages.config
- JavaScript/Rust: package.json, Cargo.toml
"""

import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ep_security import COPYLEFT_LICENSES, check_licenses, cmd_license


class TestLicenseScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --- PHP: composer.json Tests ---

    def test_composer_gpl_contagion_detected(self):
        pkg = os.path.join(self.temp_dir, "php_app")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "composer.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "acme/php-svc", "license": "GPL-3.0"}, f)
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["project"], "acme/php-svc")
        self.assertEqual(manifests[0]["license"], "GPL-3.0")

    def test_composer_clean_permissive_passes(self):
        pkg = os.path.join(self.temp_dir, "php_app")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "composer.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "acme/php-clean", "license": ["MIT", "Apache-2.0"]}, f)
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 1)
        self.assertIn("MIT", manifests[0]["license"])
        self.assertIn("Apache-2.0", manifests[0]["license"])
        self.assertFalse(any(cl in manifests[0]["license"].upper() for cl in COPYLEFT_LICENSES))

    # --- Dart / Flutter: pubspec.yaml Tests ---

    def test_pubspec_agpl_contagion_detected(self):
        pkg = os.path.join(self.temp_dir, "flutter_app")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "pubspec.yaml"), "w", encoding="utf-8") as f:
            f.write("name: app\nlicense: AGPL-3.0\ndependencies:\n  flutter: {sdk: flutter}\n")
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["project"], "app")
        self.assertEqual(manifests[0]["license"], "AGPL-3.0")

    def test_pubspec_dependency_inline_license(self):
        pkg = os.path.join(self.temp_dir, "flutter_app")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "pubspec.yaml"), "w", encoding="utf-8") as f:
            f.write("name: app\nlicense: MIT\ndependencies:\n  viral_lib: ^1.0.0 # license: GPL-3.0\n")
        _, manifests = check_licenses(self.temp_dir)
        licenses = [m["license"] for m in manifests]
        self.assertIn("GPL-3.0", licenses)
        self.assertIn("MIT", licenses)

    def test_pubspec_clean_license_passes(self):
        pkg = os.path.join(self.temp_dir, "flutter_clean")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "pubspec.yaml"), "w", encoding="utf-8") as f:
            f.write("name: clean_mobile\nlicense: Apache-2.0\ndependencies:\n  clean_pkg: ^2.0.0 # license: BSD-3-Clause\n")
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 2)
        for m in manifests:
            self.assertFalse(any(cl in m["license"].upper() for cl in COPYLEFT_LICENSES))

    # --- Python: pyproject.toml, requirements.txt, Pipfile Tests ---

    def test_pyproject_gpl_detected(self):
        pkg = os.path.join(self.temp_dir, "py_svc")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write('[project]\nname = "py-svc"\nlicense = "GPL-3.0"\n')
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["project"], "py-svc")
        self.assertEqual(manifests[0]["license"], "GPL-3.0")

    def test_pyproject_clean_license_passes(self):
        pkg = os.path.join(self.temp_dir, "py_clean")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write('[project]\nname = "clean-py"\nlicense = { text = "BSD-3-Clause" }\n')
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["project"], "clean-py")
        self.assertEqual(manifests[0]["license"], "BSD-3-Clause")

    def test_requirements_inline_gpl_detected(self):
        pkg = os.path.join(self.temp_dir, "py_app")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("requests==2.31.0\ngpl-lib==1.0 # license: GPL-2.0\n")
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["project"], "gpl-lib")
        self.assertEqual(manifests[0]["license"], "GPL-2.0")

    def test_requirements_clean_and_header_license(self):
        pkg = os.path.join(self.temp_dir, "py_app")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("# license: MIT\nfastapi>=0.100.0 # license: MIT\nuvicorn == 0.23.0 # license: BSD-3-Clause\n")
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 3)
        for m in manifests:
            self.assertFalse(any(cl in m["license"].upper() for cl in COPYLEFT_LICENSES))

    def test_pipfile_inline_sspl_detected(self):
        pkg = os.path.join(self.temp_dir, "py_pipfile")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "Pipfile"), "w", encoding="utf-8") as f:
            f.write('[packages]\nrestricted-db = "*" # license: SSPL\nclean-http = "==1.0" # license: MIT\n')
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 2)
        lics = {m["project"]: m["license"] for m in manifests}
        self.assertEqual(lics["restricted-db"], "SSPL")
        self.assertEqual(lics["clean-http"], "MIT")

    # --- Go: go.mod Tests ---

    def test_go_mod_dependency_agpl_detected(self):
        pkg = os.path.join(self.temp_dir, "go_svc")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "go.mod"), "w", encoding="utf-8") as f:
            f.write("module github.com/acme/svc\n\ngo 1.21\n\nrequire (\n  github.com/viral/pkg v1.0.0 // license: AGPL-3.0\n)\n")
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["project"], "github.com/viral/pkg")
        self.assertEqual(manifests[0]["license"], "AGPL-3.0")

    def test_go_mod_clean_module_and_dependencies(self):
        pkg = os.path.join(self.temp_dir, "go_clean")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "go.mod"), "w", encoding="utf-8") as f:
            f.write(
                "module github.com/acme/clean // license: Apache-2.0\n\n"
                "go 1.22\n\n"
                "require (\n"
                "  github.com/stretchr/testify v1.8.4 // license: MIT\n"
                ")\n"
                "require github.com/single/dep v1.0.0 // license: BSD-3-Clause\n"
            )
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 3)
        for m in manifests:
            self.assertFalse(any(cl in m["license"].upper() for cl in COPYLEFT_LICENSES))

    # --- C#: .csproj and packages.config Tests ---

    def test_csproj_license_gpl_detected(self):
        pkg = os.path.join(self.temp_dir, "cs_svc")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "Order.csproj"), "w", encoding="utf-8") as f:
            f.write(
                '<Project Sdk="Microsoft.NET.Sdk">\n'
                '  <PropertyGroup>\n'
                '    <PackageId>Acme.Order</PackageId>\n'
                '    <PackageLicenseExpression>GPL-3.0</PackageLicenseExpression>\n'
                '  </PropertyGroup>\n'
                '</Project>\n'
            )
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["project"], "Acme.Order")
        self.assertEqual(manifests[0]["license"], "GPL-3.0")

    def test_csproj_clean_license_and_package_reference(self):
        pkg = os.path.join(self.temp_dir, "cs_clean")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "Clean.csproj"), "w", encoding="utf-8") as f:
            f.write(
                '<Project Sdk="Microsoft.NET.Sdk">\n'
                '  <PropertyGroup>\n'
                '    <PackageId>Acme.Clean</PackageId>\n'
                '    <PackageLicense>MIT</PackageLicense>\n'
                '  </PropertyGroup>\n'
                '  <ItemGroup>\n'
                '    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" license="MIT" />\n'
                '  </ItemGroup>\n'
                '</Project>\n'
            )
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 2)
        for m in manifests:
            self.assertFalse(any(cl in m["license"].upper() for cl in COPYLEFT_LICENSES))

    def test_packages_config_gpl_detected(self):
        pkg = os.path.join(self.temp_dir, "cs_legacy")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "packages.config"), "w", encoding="utf-8") as f:
            f.write(
                '<packages>\n'
                '  <package id="NUnit" version="3.13.3" license="MIT" />\n'
                '  <package id="ViralPackage" version="1.0.0" license="GPL-2.0" />\n'
                '</packages>\n'
            )
        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 2)
        lics = {m["project"]: m["license"] for m in manifests}
        self.assertEqual(lics["NUnit"], "MIT")
        self.assertEqual(lics["ViralPackage"], "GPL-2.0")

    # --- npm and Cargo Regression Tests ---

    def test_npm_and_cargo_regression(self):
        pkg_npm = os.path.join(self.temp_dir, "node_pkg")
        os.makedirs(pkg_npm, exist_ok=True)
        with open(os.path.join(pkg_npm, "package.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "npm-lib", "license": "MIT"}, f)

        pkg_cargo = os.path.join(self.temp_dir, "rust_pkg")
        os.makedirs(pkg_cargo, exist_ok=True)
        with open(os.path.join(pkg_cargo, "Cargo.toml"), "w", encoding="utf-8") as f:
            f.write('[package]\nname = "rust-lib"\nlicense = "Apache-2.0"\n')

        _, manifests = check_licenses(self.temp_dir)
        self.assertEqual(len(manifests), 2)
        projects = {m["project"]: m["license"] for m in manifests}
        self.assertEqual(projects["npm-lib"], "MIT")
        self.assertEqual(projects["rust_pkg"], "Apache-2.0")

    # --- Gate Integration & SBOM Tests ---

    def test_cmd_license_clean_returns_zero(self):
        pkg = os.path.join(self.temp_dir, "clean_service")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "composer.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "clean/php", "license": "MIT"}, f)
        with open(os.path.join(pkg, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write('[project]\nname = "clean-py"\nlicense = "Apache-2.0"\n')

        args = argparse.Namespace(action="check", root=self.temp_dir, package_json=None, sbom=False)
        rc = cmd_license(args)
        self.assertEqual(rc, 0)

    def test_cmd_license_copyleft_returns_one(self):
        pkg = os.path.join(self.temp_dir, "copyleft_service")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "composer.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "viral/php", "license": "GPL-3.0"}, f)

        args = argparse.Namespace(action="check", root=self.temp_dir, package_json=None, sbom=False)
        rc = cmd_license(args)
        self.assertEqual(rc, 1)

    def test_cmd_license_sbom_export_with_polyglot_components(self):
        pkg = os.path.join(self.temp_dir, "svc")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "composer.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "acme/php", "license": "MIT"}, f)
        with open(os.path.join(pkg, "pubspec.yaml"), "w", encoding="utf-8") as f:
            f.write("name: acme_app\nlicense: BSD-3-Clause\n")

        cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            args = argparse.Namespace(action="check", root=".", package_json=None, sbom=True)
            rc = cmd_license(args)
            self.assertEqual(rc, 0)

            sbom_file = os.path.join(self.temp_dir, ".ep", "sbom.json")
            self.assertTrue(os.path.isfile(sbom_file))
            with open(sbom_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("bomFormat"), "CycloneDX")
            self.assertEqual(len(data.get("components", [])), 2)
            comp_names = {c["project"] for c in data["components"]}
            self.assertIn("acme/php", comp_names)
            self.assertIn("acme_app", comp_names)
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
