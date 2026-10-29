"""
Standard Locust Performance & Load Testing Harness for EP-OS
Conforms to Golden Signals (RED/USE methods) and Check 1.1 / Check 1.2 standards.
"""

import os
import random
import time
from locust import HttpUser, task, between, events


class EnterpriseServiceUser(HttpUser):
    wait_time = between(0.1, 0.3)  # Bounded think time with jitter

    def on_start(self):
        self.tenant_id = os.environ.get("TENANT_ID", "tenant-perf-001")
        self.headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": self.tenant_id,
            "traceparent": f"00-{random.getrandbits(128):032x}-{random.getrandbits(64):016x}-01",
        }

    @task(3)
    def health_check(self):
        """Liveness / readiness endpoint probe."""
        with self.client.get("/healthz", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Healthz probe failed with status {response.status_code}")

    @task(7)
    def query_resources(self):
        """Primary transaction workload with p95 target <= 150ms."""
        start_time = time.time()
        with self.client.get("/api/v1/resources?limit=20&page=1", headers=self.headers, catch_response=True) as response:
            duration_ms = (time.time() - start_time) * 1000
            if response.status_code == 200:
                if duration_ms > 150:
                    response.failure(f"Latency exceeded p95 threshold: {duration_ms:.2f}ms > 150ms")
                else:
                    response.success()
            else:
                response.failure(f"Transaction returned status {response.status_code}")
