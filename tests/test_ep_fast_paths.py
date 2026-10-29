#!/usr/bin/env python3
"""
Unit tests for EP-OS Fast Paths & Agent Speed Acceleration.
Tests AST caching, git diff scoping, context packing with summary, and sub-second verification paths.
"""

import argparse
import json
import os
import shutil
import tempfile
import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ep_ast import (
    load_ast_cache,
    save_ast_cache,
    scan_structural_rules,
    cmd_ast,
)
from scripts.ep_context import (
    pack_files,
    cmd_pack,
    collect_files_from_surface,
)



class TestEpFastPaths(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ast_cache_save_and_load(self):
        cache_data = {
            "src/service.ts": {
                "hash": "abcdef123456",
                "findings": [],
            }
        }
        # Override CACHE_FILE temporarily
        orig_cache_file = "scripts.ep_ast.CACHE_FILE"
        test_cache = os.path.join(self.temp_dir, "cache.json")
        import scripts.ep_ast as ep_ast
        ep_ast.CACHE_FILE = test_cache

        try:
            save_ast_cache(cache_data)
            loaded = load_ast_cache()
            self.assertEqual(loaded["src/service.ts"]["hash"], "abcdef123456")
        finally:
            ep_ast.CACHE_FILE = ".ep/cache/ast_cache.json"

    def test_context_pack_files_and_summary(self):
        file1 = os.path.join(self.temp_dir, "file1.ts")
        with open(file1, "w", encoding="utf-8") as f:
            f.write("export const A = 1;\nexport const B = 2;\n")

        file2 = os.path.join(self.temp_dir, "file2.ts")
        with open(file2, "w", encoding="utf-8") as f:
            f.write("export const C = 3;\n")

        bundle, count, lines, bytes_count = pack_files(
            ["file1.ts", "file2.ts"],
            max_lines=800,
            root_dir=self.temp_dir,
        )
        self.assertEqual(count, 2)
        self.assertEqual(lines, 3)
        self.assertIn("EP-OS CONTEXT BUNDLE: file1.ts", bundle)
        self.assertIn("EP-OS CONTEXT BUNDLE: file2.ts", bundle)

    def test_cmd_pack_with_summary_flag(self):
        file1 = os.path.join(self.temp_dir, "app.ts")
        with open(file1, "w", encoding="utf-8") as f:
            f.write("console.log('hello');\n")

        out_bundle = os.path.join(self.temp_dir, "bundle.txt")
        args = argparse.Namespace(
            root=self.temp_dir,
            files=["app.ts"],
            diff=None,
            scope=None,
            surface=False,
            output=out_bundle,
            max_lines=800,
            summary=True,
        )
        rc = cmd_pack(args)
        self.assertEqual(rc, 0)
        with open(out_bundle, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("EP-OS TASK CONTEXT & BLAST-RADIUS SUMMARY", content)
        self.assertIn("app.ts", content)

    def test_cmd_ast_surface_scoping(self):
        # Create a mock surface with declared file
        surf_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        with open(surf_file, "w", encoding="utf-8") as f:
            f.write("""
# Change Surface
## 3. Code Surface
- `src/handler.ts`
""")
        src_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        handler_file = os.path.join(src_dir, "handler.ts")
        with open(handler_file, "w", encoding="utf-8") as f:
            f.write("export function handle() { return true; }\n")

        args = argparse.Namespace(
            action="scan",
            scope=self.temp_dir,
            surface=True,
            diff=None,
        )
        rc = cmd_ast(args)
        # Should execute cleanly without error
        self.assertEqual(rc, 0)

    def test_cmd_quality_surface_scoping(self):
        from scripts.ep_quality import cmd_quality
        surf_file = os.path.join(self.temp_dir, "CHANGE_SURFACE.md")
        with open(surf_file, "w", encoding="utf-8") as f:
            f.write("""
# Change Surface
## 3. Code Surface
- `src/clean.ts`
""")
        src_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        clean_file = os.path.join(src_dir, "clean.ts")
        with open(clean_file, "w", encoding="utf-8") as f:
            f.write("export const x = 1;\n")

        args = argparse.Namespace(
            action="check",
            root=self.temp_dir,
            surface=True,
            diff=None,
            json=True,
        )
        rc = cmd_quality(args)
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

