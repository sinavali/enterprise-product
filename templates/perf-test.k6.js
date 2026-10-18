// Standard k6 Performance & Stress Testing Script
// Conforms to Check 1.1, Check 1.2, Check 3.1, and Performance Efficiency standards

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metric definitions
const errorRate = new Rate('custom_error_rate');
const transactionDuration = new Trend('custom_txn_duration');

// Test Execution Configuration: Multi-stage Ramp-up, Sustained Load & Stress Spikes
export const options = {
  stages: [
    { duration: '30s', target: 20 },  // Ramp up to 20 virtual users
    { duration: '1m', target: 50 },   // Normal sustained load at 50 VUs
    { duration: '30s', target: 100 }, // Stress surge to 100 VUs
    { duration: '30s', target: 0 },   // Graceful ramp down
  ],
  thresholds: {
    // Quality Gates for Performance Verification
    'http_req_duration': ['p(95)<150', 'p(99)<300'], // 95% of requests must resolve under 150ms
    'custom_error_rate': ['rate<0.01'],              // Error rate must remain strictly below 1%
    'http_req_failed': ['rate<0.01'],                // HTTP failure rate below 1%
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080';
const TENANT_ID = __ENV.TENANT_ID || 'tenant-perf-001';

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    'X-Tenant-ID': TENANT_ID,
    'traceparent': `00-${Math.random().toString(16).substring(2, 34)}-${Math.random().toString(16).substring(2, 18)}-01`,
  };

  // 1. Health Probe Check
  const healthRes = http.get(`${BASE_URL}/healthz`, { headers });
  check(healthRes, {
    'healthz status is 200': (r) => r.status === 200,
  });

  // 2. Primary Query Transaction
  const queryStart = Date.now();
  const queryRes = http.get(`${BASE_URL}/api/v1/resources?limit=20&page=1`, { headers });
  const queryDuration = Date.now() - queryStart;
  transactionDuration.add(queryDuration);

  const querySuccess = check(queryRes, {
    'query status is 200': (r) => r.status === 200,
    'query latency <= 150ms': (r) => r.timings.duration <= 150,
  });

  errorRate.add(!querySuccess);

  // Think time between transactions (bounded jitter)
  sleep(0.1 + Math.random() * 0.2);
}
