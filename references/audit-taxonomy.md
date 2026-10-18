# The 10-Dimension Enterprise Audit Taxonomy

This specification defines the complete 10-Dimension Enterprise Audit Suite. Every proposed change or milestone must be evaluated against this taxonomy during the PR Self-Audit and automated quality gates.

---

## 1. Defect Severity Classification

Every finding discovered during an audit must be categorized into one of three strict severity tiers:

| Severity | Definition | Action Required |
|---|---|---|
| `blocking` | Violates Tier 1 directives, introduces security flaws, risks data corruption, breaks contracts, lacks required container/failure tests, or has unhandled errors. | **Must be resolved immediately.** Blocks PR merge. |
| `suggestion` | Architectural enhancements, performance optimizations, non-critical code hygiene, or refactoring opportunities. | Documented in report; may be deferred to follow-up tasks if non-blocking. |
| `nit` | Minor ergonomic or typographical improvements. | Non-blocking. Resolve if trivial. |

---

## 2. The 10 Dimensions

### Dimension 1: Scalability & Capacity
- **Check 1.1 (Algorithmic Complexity)**: Ensure no $O(n^2)$ or unindexed operations exist on unbounded collections.
- **Check 1.2 (Database Access)**: Verify no N+1 query patterns; all queries must utilize indexes, bounded limits, and pagination (`LIMIT`/`OFFSET` or cursor-based).
- **Check 1.3 (Connection Pooling)**: Database, HTTP client, and messaging connections must be reused via pools; verify idle connection timeouts and max pool sizing.
- **Check 1.4 (Memory & Buffering)**: Large file uploads or stream processing must use streaming pipes/chunks rather than reading entire payloads into memory.
- **Check 1.5 (Statelessness)**: Services must hold no in-memory client session state between requests; all persistent or shared session state must reside in external stores (e.g. Redis, DB) to allow horizontal scaling.
- **Check 1.6 (Container Resource Envelopes)**: Container manifests (Pod, Compose, Helm) must specify deterministic CPU and memory requests and limits to prevent noisy-neighbor starvation.

### Dimension 2: Structural Maintainability & Modularity
- **Check 2.1 (Profile Conformance)**: Verify that the codebase strictly adheres to its declared Profile (A, B, C, or D).
- **Check 2.2 (Layer Isolation)**: Pure domain entities and use cases must have zero dependencies on infrastructure, ORM, or UI frameworks.
- **Check 2.3 (Dependency Graph)**: No circular dependencies between modules or packages.
- **Check 2.4 (Single Responsibility)**: Functions and classes must remain focused; flag "god classes" or sprawling controllers.
- **Check 2.5 (Directory Nesting Depth Ceiling)**: Maximum directory hierarchy depth must not exceed 6 levels from project root. Flag over-nested paths.
- **Check 2.6 (File Line Count Ceiling)**: Files must not exceed 800 lines of code (hard limit, excluding auto-generated code and lockfiles). Recommend $\le 400$ lines.
- **Check 2.7 (Anti-Fragmentation & Co-Location)**: Prohibit hyper-fragmentation into microscopic files ($< 20$ lines) when types are tightly coupled. Co-locate subordinate value objects, DTOs, and domain events.
- **Check 2.8 (Known Directory Taxonomy)**: All source files must reside within recognized architectural directories (`domain/`, `application/`, `infrastructure/`, `components/`, etc.). Generic dumping grounds (`utils/`, `helpers/`, `misc/`, `common/`) are strictly flagged.
- **Check 2.9 (API-First Contract Definition)**: All public and inter-service interfaces must be defined via formal schema contracts (`OpenAPI`, `Protobuf`, or `JSON Schema`) before code implementation.
- **Check 2.10 (Feature Flag Hygiene & Lifespan)**: Temporary feature flags must define an expiration date ($\le 30$ days), an owner, and a cleanup ticket. Permanent toggles must be documented as operational controls.

### Dimension 3: Fault Tolerance & Resilience
- **Check 3.1 (Timeout Enforcement)**: Every network request (HTTP, gRPC, DB, Cache) must have an explicit client-side timeout configured.
- **Check 3.2 (Retry Strategy)**: Retries must apply only to idempotent operations, must incorporate exponential backoff with randomized jitter, and must have a capped retry limit.
- **Check 3.3 (Circuit Breakers & Fallbacks)**: Critical dependencies must degrade gracefully or trip circuit breakers under sustained failure.
- **Check 3.4 (Dead Letter Queues)**: Message consumers must handle unprocessable messages via DLQs rather than infinitely crashing or dropping messages silently.
- **Check 3.5 (Graceful Shutdown & Drain)**: Process must trap `SIGTERM`/`SIGINT`, stop accepting new inbound connections, drain in-flight requests within a 15–30s window, and cleanly terminate connection pools.
- **Check 3.6 (Multi-Replica HA & Redundancy)**: Production deployments must configure $\ge 2$ replicas with anti-affinity across failure domains/availability zones.
- **Check 3.7 (Consumer Pool Backpressure)**: Streaming and message consumers must implement bounded concurrency, prefetch limits, and explicit rate-matched consumption to prevent OOM under upstream surges.
- **Check 3.8 (Bulkhead Isolation)**: External client dependencies and internal worker threadpools must be partitioned into isolated resource pools so saturation in one dependency does not cascade.

### Dimension 4: Data Integrity & Concurrency
- **Check 4.1 (Race Conditions & Locking)**: Concurrent state updates must utilize optimistic concurrency control (version checks) or explicit row-level locking.
- **Check 4.2 (Transaction Boundaries)**: Database mutations spanning multiple tables or aggregate roots must be enclosed within atomic transactions.
- **Check 4.3 (Idempotent Consumers)**: Event handlers and webhook receivers must track idempotent transaction keys to avoid duplicate processing.
- **Check 4.4 (UTC Storage)**: All persisted timestamps and wire dates must strictly adhere to the UTC Storage Convention (`TIMESTAMP WITH TIME ZONE` or ISO-8601 UTC with `Z`).
- **Check 4.5 (Transactional Outbox)**: Domain events emitted during aggregate mutations must be stored to a local database outbox table within the same transaction to guarantee reliable message publishing.
- **Check 4.6 (Expand/Contract Zero-Downtime Migrations)**: Database schema alterations must follow the expand/contract pattern. Instant breaking renames or non-null columns without defaults that fail rolling deployments are blocking defects.
- **Check 4.7 (Idempotency Keys on Mutating APIs)**: Mutating business endpoints (payments, orders, billing state) must accept and enforce an `Idempotency-Key` header with TTL deduplication.
- **Check 4.8 (Immutable Mutation Audit Logging)**: State-mutating administrative or financial actions must generate append-only, tamper-evident audit records capturing actor, timestamp, prior state, and new state.
- **Check 4.9 (Restore Verification Frequency)**: Database backups must undergo scheduled automated restoration drills with RTO/RPO measurement; untested backups are considered non-existent.

### Dimension 5: Security & Zero-Trust
- **Check 5.1 (Injection Prevention)**: All SQL/NoSQL queries must use parameterized statements. Zero string concatenation of user input into queries.
- **Check 5.2 (Authentication & Authorization)**: Every endpoint must verify identity and evaluate granular permission scopes before executing domain logic.
- **Check 5.3 (Secret Hygiene)**: Zero hardcoded credentials, API keys, private keys, or passwords. All secrets injected via environment variables or secret vaults.
- **Check 5.4 (Web Security - Profile B)**: Output encoding to prevent XSS, strict Content Security Policy (CSP), anti-CSRF protections, and `SameSite`/`Secure` cookie flags.
- **Check 5.5 (Data Encryption - Profile C)**: Mobile local caches and tokens must use hardware-backed encryption (KeyStore/Keychain/SQLCipher).
- **Check 5.6 (Multi-Tenancy Isolation)**: Queries and tenant data access must enforce tenant context scoping (e.g. Row-Level Security or mandatory `tenant_id` query filters) to prevent cross-tenant data leakage.
- **Check 5.7 (Supply Chain Security)**: Dependency lockfiles must be immutable and checked in; automated scanning must detect known CVEs in external dependencies.
- **Check 5.8 (Public Ingress Rate Limiting)**: All public-facing ingress points must enforce IP, user, or token-bucket rate limiting to mitigate DoS, brute-force, and credential stuffing.
- **Check 5.9 (Zero-Downtime Secret Rotation)**: Application secret consumers must support dynamic reloading or dual-token overlap windows to allow rotation without process restarts or client errors.
- **Check 5.10 (KMS Envelope Encryption)**: Sensitive customer data and PII at rest must be encrypted using envelope encryption with managed master keys (AWS KMS, GCP KMS, Vault Transit).

### Dimension 6: Observability & Operability
- **Check 6.1 (Structured Logging)**: Logs must be formatted as structured JSON containing timestamp, severity level, message, and contextual metadata.
- **Check 6.2 (Distributed Tracing)**: Inbound request trace IDs / correlation IDs must propagate through asynchronous jobs and downstream API calls.
- **Check 6.3 (Health Probes)**: Applications must expose `/healthz` (liveness) and `/readyz` (readiness) probes assessing critical dependencies.
- **Check 6.4 (Metrics)**: Critical business operations and error rates must expose OpenTelemetry or Prometheus counters/histograms.
- **Check 6.5 (PII & Secret Scrubbing)**: Log formatters must automatically redact sensitive fields (passwords, auth tokens, bearer headers, credit cards, emails) before outputting logs.
- **Check 6.6 (OpenTelemetry Semantic Conventions)**: Spans, metrics, and log attributes must adhere to standard OTel semantic naming conventions.
- **Check 6.7 (W3C Trace Context Propagation)**: All distributed network calls (HTTP headers `traceparent`/`tracestate`, gRPC metadata, queue message headers) must propagate W3C standard trace context.
- **Check 6.8 (Metric Cardinality Bounding)**: Metric labels/tags must have bounded, finite values. Unbounded identifiers (user IDs, email addresses, order IDs) in metric labels are strictly prohibited.

### Dimension 7: Contract & Schema Drift
- **Check 7.1 (Schema Alignment)**: Code implementations must match OpenAPI / Protobuf schemas exactly.
- **Check 7.2 (Backward Compatibility)**: No breaking changes to existing API schemas without a major SemVer bump and deprecation notice.
- **Check 7.3 (Client SDK Regeneration)**: Ensure generated client libraries are synchronized with updated schemas without manual drift.

### Dimension 8: Code Quality & Typing Strictness
- **Check 8.1 (Strict Typing)**: No untyped `any`, raw `Object`, or suppressed compiler warnings.
- **Check 8.2 (Null Safety)**: Proper handling of nullable and optional values; zero unprotected dereferencing.
- **Check 8.3 (Error Handling)**: No empty catch blocks (`catch (e) {}`), swallowed errors, or generic `throw new Error()`. Custom, typed error definitions must be used.
- **Check 8.4 (Immutability)**: Domain value objects and event payloads must be immutable.
- **Check 8.5 (Anti-MVP & Zero-Stub Mandate)**: Prohibit 'MVP', 'Proof-of-Concept', 'mock-first', or 'phased hardening' shortcuts. Zero incomplete stubs or deferred resilience logic. Every deliverable must be finalized and production-ready.
- **Check 8.6 (12-Factor Typed Configuration Validation)**: Application configuration must be strictly typed, validated at startup, and loaded from environment variables. Missing or malformed configuration must cause fast failure on boot.

### Dimension 9: Documentation & Spec Drift
- **Check 9.1 (Change Surface Conformance)**: The implementation diff must strictly correspond to the approved `CHANGE_SURFACE.md`.
- **Check 9.2 (ADR Required)**: Any architectural shift or Tier 2 deviation must have a corresponding accepted ADR in `docs/adr/`.
- **Check 9.3 (NC Lifecycle)**: No unaddressed open NC items older than 14 days exist.
- **Check 9.4 (File-Level Documentation)**: Complex algorithms and aggregate invariants must have clear, maintainable inline documentation.
- **Check 9.5 (Operational Runbook Requirement)**: Every production service must have an operational runbook in `docs/runbooks/` or root detailing health probe remediation, alerting thresholds, dependencies, and rollback procedures.

### Dimension 10: Test Fidelity & Assertion Quality
- **Check 10.1 (No Happy-Path-Only)**: Every feature must have explicit tests for edge cases, invalid inputs, and failure paths.
- **Check 10.2 (Real Ephemeral Containers)**: Database and messaging tests must execute against real containers (Testcontainers/Podman); in-memory SQL emulators are strictly forbidden.
- **Check 10.3 (No Tautological Assertions)**: Assertions must test actual business outcomes and state changes (ban assertions like `expect(true).toBe(true)` or testing mocks).
- **Check 10.4 (Coverage Thresholds)**: Verify $\ge 95\%$ Line/Branch coverage on pure domain packages, and $\ge 80\%$ on adapters.
- **Check 10.5 (Concurrency Tests)**: Asynchronous and multi-threaded logic must have concurrency tests verifying race-free operation.

---

## 3. Audit Execution Protocol

1. **Scaffold Report**: Agent initializes `AUDIT_REPORT.md` using `templates/AUDIT_REPORT.template.md`.
2. **Systematic Evaluation**: Agent systematically reviews the changes across each of the 10 dimensions.
3. **Finding Attribution**: Every finding lists:
   - Dimension ID and Check ID (e.g. `Dim 4.4`).
   - File path and line number reference.
   - Evidence snippet.
   - Severity rating (`blocking`, `suggestion`, `nit`).
   - Remediation requirement.
4. **Pass/Fail Decision**:
   - If `count(blocking) == 0` ➔ Audit Status: **PASS**.
   - If `count(blocking) > 0` ➔ Audit Status: **FAIL** (requires remediation before PR merge).
