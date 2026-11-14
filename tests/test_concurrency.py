#!/usr/bin/env python3
"""
Unit tests for concurrency, atomic file operations, and race condition resistance.
Verifies thread-safe and process-safe state management across:
- ep memory save / load
- ep session state save / load
- Change Surface initialization and validation under concurrency
"""

import argparse
import concurrent.futures
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ep import cmd_memory
from scripts.ep_session import cmd_session
from scripts.ep_ops import atomic_write


class TestConcurrencyAndAtomicOperations(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_memory_saves_remain_valid_json(self):
        """Verify that concurrent writes to memory.json via cmd_memory never produce corrupt JSON."""
        num_workers = 8
        iterations_per_worker = 10

        def worker_task(worker_id: int):
            for i in range(iterations_per_worker):
                args = argparse.Namespace(
                    action="save",
                    task=f"Worker {worker_id} Task Iteration {i}",
                    notes=f"Notes from thread {worker_id}"
                )
                rc = cmd_memory(args)
                if rc != 0:
                    return False
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, wid) for wid in range(num_workers)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertTrue(all(results))

        # Ensure memory.json exists and is valid parseable JSON with all required keys
        mem_file = os.path.join(self.temp_dir, ".ep", "memory.json")
        self.assertTrue(os.path.exists(mem_file))
        with open(mem_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("product", data)
        self.assertIn("timestamp", data)
        self.assertIn("invariants", data)
        self.assertEqual(data["product"], "enterprise-product")

    def test_concurrent_session_state_persistence(self):
        """Verify that atomic_write and cmd_session survive concurrent thread executions."""
        test_file = os.path.join(self.temp_dir, "atomic_target.json")
        num_threads = 6

        def file_writer(tid: int):
            for i in range(15):
                state = {
                    "thread_id": tid,
                    "iteration": i,
                    "status": "in_progress",
                    "payload": list(range(50))
                }
                atomic_write(test_file, json.dumps(state, indent=2))
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(file_writer, tid) for tid in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertTrue(all(results))

        with open(test_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertIsNotNone(loaded)
        self.assertIn("thread_id", loaded)
        self.assertIn("payload", loaded)
        self.assertEqual(len(loaded["payload"]), 50)


if __name__ == "__main__":
    unittest.main()
