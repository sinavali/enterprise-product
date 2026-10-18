# Chaos Engineering Experiment Plan: [EXPERIMENT_TITLE]

**Experiment ID**: `CHAOS-{{YYYYMMDD}}-{{ID}}`  
**Target Service**: `{{SERVICE_NAME}}`  
**Owner / Engineer**: `{{OWNER_NAME}}`  
**Environment**: Staging / Production (Canary)  
**Status**: `Draft` / `Approved` / `In Progress` / `Completed` / `Rolled Back`

---

## 1. Hypothesis & Background
- **System Under Test**: `{{SYSTEM_UNDER_TEST}}`
- **Architectural Component Tested**: [e.g. Database failover, Downstream Circuit Breaker, Redis Cache Cluster failure, Network Latency injection]
- **Hypothesis**:  
  *Under [failure condition], the system will continue to serve traffic with [graceful degradation behavior], keeping overall error rate $< 0.1\%$ and p95 latency $< 250\text{ms}$, without data corruption or cascading failure.*

---

## 2. Steady State Definition (Baseline)
Prior to injecting failure, the system must meet the following steady-state criteria for at least 15 minutes:

- **Availability / Success Rate**: $\ge 99.9\%$ HTTP 2xx/3xx.
- **Latency (p95)**: $\le 80\text{ms}$.
- **Throughput**: Between $200$ and $500$ RPS.
- **System Resources**: CPU $< 50\%$, Memory $< 65\%$.
- **Database Active Connections**: $\le 30\%$ of maximum pool capacity.

---

## 3. Failure Injection Method (Fault Model)

| Parameter | Configuration |
|---|---|
| **Fault Type** | Latency Injection / Pod Kill / Packet Loss / DNS Failure / Connection Drop |
| **Tooling** | Chaos Mesh / Toxiproxy / Podman CLI / Network TC |
| **Target Scope** | Exactly 1 of 3 database read replicas OR 30% of payment adapter traffic |
| **Fault Duration** | 5 minutes (300 seconds) |
| **Blast Radius** | Constrained to canary tenant or staging cluster |

### Fault Injection Command / Manifest
```bash
# Example: Inject 500ms latency to downstream payment gateway via toxiproxy / chaos-mesh
curl -X POST http://localhost:8474/proxies/payment_gateway/toxics \
  -d '{"type":"latency","attributes":{"latency":500,"jitter":50}}'
```

---

## 4. Blast Radius Containment & Abort Criteria
The experiment will **IMMEDIATELY ABORT** and initiate automatic rollback if any of the following triggers fire:

- [ ] Global error rate exceeds $1.0\%$ across a 30-second sliding window.
- [ ] p99 latency exceeds $1,000\text{ms}$ on primary business transactions.
- [ ] Any data corruption or unhandled panic is detected in logs.
- [ ] Manual abort button triggered by On-Call Incident Commander.

### Immediate Rollback Procedure
```bash
# Emergency rollback command:
curl -X DELETE http://localhost:8474/proxies/payment_gateway/toxics/latency_downstream
# Or kill chaos pod:
kubectl delete chaos -n chaos-testing --all
```

---

## 5. Experiment Execution & Observations

### 5.1. Execution Log
- `T+00:00`: Baseline steady state confirmed.
- `T+01:00`: Fault injection started.
- `T+01:30`: Observed behavior: Circuit breaker tripped from CLOSED to OPEN after 10 failed probes.
- `T+01:35`: Fallback cache activated; degraded response returned with `Cache-Control: stale-while-revalidate`.
- `T+05:00`: Fault injection removed.
- `T+05:45`: Circuit breaker entered HALF-OPEN state, probed downstream service, and transitioned back to CLOSED.

### 5.2. Metrics Recorded

| Metric | Steady State | During Chaos | Target Limit | Pass / Fail |
|---|---|---|---|---|
| **Error Rate (5xx)** | $0.01\%$ | $0.04\%$ | $< 0.1\%$ | **PASS** |
| **p95 Latency** | $45\text{ms}$ | $112\text{ms}$ | $< 250\text{ms}$ | **PASS** |
| **Data Loss / DLQ** | 0 messages | 0 messages | 0 | **PASS** |

---

## 6. Action Items & Architectural Learnings
- **Finding 1**: Fallback cache TTL was slightly too short (30s), causing brief thundering herd on downstream recovery.
  - *Action*: Implement exponential backoff probe in circuit breaker half-open state.
- **Finding 2**: Circuit breaker transition metrics were missing Prometheus alerts.
  - *Action*: Add `CircuitBreakerStateTripped` alert in `monitoring/alerts.yaml`.
