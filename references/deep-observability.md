# Deep Observability & Performance Specification

This specification defines the deep observability, tracing, metrics, and application performance monitoring (APM) standards for all projects operating under EP-OS.

---

## 1. The Core Observability Pillars

Enterprise services must emit high-fidelity telemetry adhering to the **OpenTelemetry (OTel)** standard across traces, metrics, and structured logs.

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Traces: W3C Distributed Context & Span Lineage           │
│    traceparent (version-trace_id-parent_id-flags)           │
├─────────────────────────────────────────────────────────────┤
│ 2. Metrics: Golden Signals, RED & USE Conventions          │
│    Rate, Errors, Duration, Utilization, Saturation          │
├─────────────────────────────────────────────────────────────┤
│ 3. Logs: Structured JSON with Correlation Lineage           │
│    timestamp, level, trace_id, span_id, message, attributes │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Distributed Tracing & W3C Context Propagation

### 2.1 The W3C `traceparent` Standard
All outbound network calls from Secondary Adapters (HTTP clients, gRPC stubs, message broker publishers) must propagate distributed trace context using the standard W3C header:
```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
              │  └───────────────┬──────────────┘ └───────┬──────┘ └─ flags (sampled=01)
              │                  │                        └─ parent_span_id (16 hex)
              │                  └─ trace_id (32 hex)
              └─ version (00)
```

### 2.2 Trace Invariants
1. **Trace Continuity**: Inbound request `trace_id` values must be extracted at the primary adapter ingress and injected into asynchronous background workers, transactional outbox payloads, and downstream API requests.
2. **Error Span Tagging**: When an exception or domain error occurs, the active span must set its status to `Error` and record an exception event containing the error type and message (with PII redacted).
3. **Baggage & Correlation**: Request correlation IDs (`X-Correlation-ID` or `X-Request-ID`) must mirror or attach to the active trace span.

---

## 3. Metrics Conventions: Golden Signals, RED & USE

### 3.1 The 4 SRE Golden Signals
All backend services (Profile A) must collect and export the four golden signals:
1. **Latency**: Time taken to service requests (measured via histogram with standard bucketing, e.g. `[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]` seconds).
2. **Traffic**: Demand on the system (request rate, active sessions, operations per second).
3. **Errors**: Rate of requests that fail (HTTP 5xx, gRPC error codes, unhandled exceptions).
4. **Saturation**: Utilization of constrained resources (connection pool usage, queue depth, memory buffer utilization).

### 3.2 The RED Method (Request-Driven Services)
For HTTP/gRPC ingress controllers:
- **Rate**: `http_server_requests_total{method, route, status}`
- **Errors**: `http_server_errors_total{method, route, error_type}`
- **Duration**: `http_server_request_duration_seconds_bucket{method, route}`

### 3.3 The USE Method (Resource-Driven Infrastructure)
For internal server nodes, worker pools, and persistence engines:
- **Utilization**: Percentage of time the resource was busy (e.g. CPU busy %, thread pool active threads / capacity).
- **Saturation**: Degree to which the resource has extra work queued (e.g. thread pool queue depth, outbox pending count).
- **Errors**: Count of error events (e.g. connection pool exhaustion errors, disk I/O errors).

---

## 4. Metric Cardinality Bounding & Exemplars

### 4.1 Cardinality Bounding Rule
Putting high-cardinality values into metric label dimensions causes exponential memory growth and crashes metrics backends:
- **Strictly Banned in Metric Labels**: User IDs, account numbers, IP addresses, email addresses, order IDs, full request query strings, raw stack traces.
- **Allowed in Metric Labels**: Bounded enumerations ($\le 50$ distinct values: HTTP method, status code, route template e.g. `/orders/{id}`, tenant class, region).

### 4.2 Exemplars
Prometheus and OpenTelemetry exemplars link metrics directly to traces:
- When a latency histogram bucket records an observation $> 99$th percentile, it must attach an exemplar containing the active `trace_id`.
- This enables one-click transitions in Grafana/APM from a latency spike in a metric dashboard directly to the exact distributed trace waterfall.

---

## 5. Client Real User Monitoring (RUM) & Synthetics

### 5.1 Profile B (Web Application) Core Web Vitals RUM
Web applications must instrument and report Google Core Web Vitals to the telemetry collector:
- **LCP (Largest Contentful Paint)**: Target $\le 2.5\text{s}$.
- **INP (Interaction to Next Paint)**: Target $\le 200\text{ms}$.
- **CLS (Cumulative Layout Shift)**: Target $\le 0.1$.

### 5.2 Synthetic Monitoring (Canary Probes)
Critical user flows (authentication, payment checkout, core search) must define synthetic monitoring probe scripts running against production and staging environments on a 1-to-5 minute schedule to detect outages before customers report them.
