# Operational Runbook: [SERVICE_NAME]

## 1. Service Overview
- **Service Name**: `{{SERVICE_NAME}}`
- **Owner Team**: `{{TEAM_NAME}}` (`{{ONCALL_ROTATION}}`)
- **Repository Path**: `{{REPO_PATH}}`
- **Architectural Profile**: `{{PROFILE}}` (A: Backend Hexagonal / B: Web / C: Mobile / D: Library)
- **Runtime Environment**: Containerized / Kubernetes / Podman Quadlet
- **Upstream Dependencies**: [e.g. Auth Gateway, Ingress]
- **Downstream Dependencies**: [e.g. PostgreSQL, Redis, Kafka]

---

## 2. Health & Readiness Probes
- **Liveness Probe**: `GET /healthz` (Port `{{METRICS_PORT}}`)
  - Threshold: Fails if internal deadlock occurs or runtime process hangs.
  - Expected Response: `200 OK` `{"status":"ok"}`
  - Remediation on Failure: Automatic container restart via kubelet/quadlet.
- **Readiness Probe**: `GET /readyz` (Port `{{METRICS_PORT}}`)
  - Threshold: Fails if primary database or mandatory message broker connection pool is disconnected.
  - Expected Response: `200 OK` `{"status":"ready","dependencies":{"db":"ok","cache":"ok"}}`
  - Remediation on Failure: Traffic removed from load balancer pool. Investigate downstream connectivity.

---

## 3. Golden Signals & Alerting Thresholds

| Metric | Target / SLO | Warning Threshold | Critical / Pager Threshold | Dashboard Link |
|---|---|---|---|---|
| **Latency (p95)** | $\le 100\text{ms}$ | $> 150\text{ms}$ for 5m | $> 300\text{ms}$ for 2m | `[Grafana Dashboard]` |
| **Error Rate (5xx)** | $< 0.1\%$ | $> 0.5\%$ for 5m | $> 1.0\%$ for 2m | `[Grafana Dashboard]` |
| **Traffic / RPS** | Normal: $100\text{–}1000$ rps | $< 10$ rps or $> 2000$ rps | $> 5000$ rps (DoS alert) | `[Grafana Dashboard]` |
| **Saturation (CPU/Mem)**| CPU $< 70\%$, Mem $< 80\%$ | Mem $> 80\%$ | Mem $> 90\%$ (OOM risk) | `[Grafana Dashboard]` |

---

## 4. Common Failure Modes & Step-by-Step Remediation

### 4.1. Database Connection Pool Starvation
- **Symptoms**: Readiness probe fails (`readyz` 503), error log spikes with `ConnectionPoolTimeoutException`.
- **Diagnosis**: Run `SELECT count(*), state FROM pg_stat_activity GROUP BY state;`. Inspect long-running locks.
- **Mitigation**:
  1. If orphaned transactions are blocking: terminate idle-in-transaction connections.
  2. Scale horizontal replicas temporarily if read replica lag is minimal.
  3. Drain slow background workers sharing the database pool.

### 4.2. Downstream Dependency Outage (Degradation Mode)
- **Symptoms**: Circuit breaker trips open for downstream client `{{DEPENDENCY_NAME}}`.
- **Diagnosis**: Check status page and latency metrics for downstream service.
- **Mitigation**:
  1. Confirm fallback cache is serving cached/stale data gracefully.
  2. If fallback queue is filling up, verify DLQ has sufficient storage capacity.
  3. Do not disable circuit breakers manually during active downstream incidents.

### 4.3. Consumer Lag / Backpressure Spike
- **Symptoms**: Event consumer group lag exceeds 10,000 messages; processing latency increases.
- **Diagnosis**: Check if worker processing is blocked on I/O or if message format has poison payloads.
- **Mitigation**:
  1. Verify whether poisoned messages are routed to Dead Letter Queue (DLQ).
  2. Increase consumer partition concurrency up to the topic partition limit.
  3. If rate-limited by downstream API, enable backpressure throttle to match downstream capacity.

---

## 5. Deployment, Rollback & Draining

### 5.1. Graceful Draining
- Service handles `SIGTERM` by stopping new ingress connections and waiting 20s for in-flight requests to finish.
- If pods fail to terminate cleanly, verify `terminationGracePeriodSeconds` is set to $\ge 30\text{s}$.

### 5.2. Rapid Rollback Procedure
1. Identify the last known good commit hash or container image tag: `vX.Y.Z-hash`.
2. Execute rollback command:
   ```bash
   # Kubernetes rollback:
   kubectl rollout undo deployment/{{SERVICE_NAME}} -n production
   # Or via GitOps:
   git revert HEAD -m "revert: rollback due to incident INC-XXXX" && git push origin main
   ```
3. Verify canary pods pass `/readyz` before completing rollout.
4. Verify database schema backward-compatibility: Expand/Contract migrations guarantee schema compatibility across $N-1$ versions.
