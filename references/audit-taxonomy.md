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
- **Check 7.1 (Schema Alignment & Contract Boundaries)**: Code implementations must match OpenAPI / Protobuf schemas exactly. Direct cross-project relative imports bypassing published package contracts (`RULE-7.1-DIRECT-CROSS-PROJECT-IMPORT`) are strictly forbidden; inter-service boundaries must be crossed via shared contracts (e.g. `libs/core-contracts`).
- **Check 7.2 (Backward Compatibility & Versioned Mutations)**: No breaking changes to existing API schemas without a major SemVer bump and deprecation notice. Direct unversioned deletion or dropping of schema fields (`RULE-7.2-UNVERSIONED-CONTRACT-MUTATION`) without deprecation markers violates contract stability.
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

---

## 4. Complete Enterprise Term Gap Assessment & Mechanical Enforcement Matrix

This matrix maps enterprise production qualities (Groups A through G) and Tooling Guidance to their mechanical enforcement mechanisms within EP-OS:

### 🏗️ Group A: Architectural & Design Qualities
| Term | Status | Enforcement Mechanism | Command / Gate |
|---|---|---|---|
| **Scalability** | Enforced | Dim 1 heuristic scanner (`RULE-1.1-UNBOUNDED-SCAN`), statelessness rules | `ep audit`, `ep perf` |
| **Modularity** | Enforced | Nx project contracts, boundary integrity checker, DAG task runner | `ep graph --check-boundaries`, `ep run` |
| **Loose Coupling & High Cohesion** | Enforced | Dim 7 cross-project import check (`RULE-7.1`), anti-dumping ground rule (`RULE-2.8`) | `ep graph`, `ep audit` |
| **Statelessness** | Enforced | Dim 1 mutable global state scanner (`RULE-1.5`), AST grep scanner | `ep ast scan`, `ep audit` |
| **API-First Design** | Enforced | Profile D contracts requirement, OpenAPI/AsyncAPI contract verification | `ep contract verify`, `ep init` |
| **Configurability** | Enforced | Dim 8 12-factor typed config check (`RULE-8.6-NAKED-ENV-IN-DOMAIN`) | `ep audit`, `ep quality` |

### 📡 Group B: Observability & Monitoring
| Term | Status | Enforcement Mechanism | Command / Gate |
|---|---|---|---|
| **Logging** | Enforced | Dim 6 structured JSON log checker (`RULE-6.1-BARE-CONSOLE-LOG`) | `ep audit` |
| **Telemetry** | Enforced | OTel collector config verification, telemetry command | `ep telemetry verify` |
| **Monitoring** | Enforced | Prometheus alert schema validation (`templates/monitoring/alerts.template.yaml`) | `ep slo`, `ep telemetry` |
| **Distributed Tracing** | Enforced | Dim 6 W3C `traceparent` context propagation check (`RULE-6.7`) | `ep audit` |
| **Health Checks** | Enforced | Contract testing health probe verification (`/healthz`, `/readyz`), IaC liveness | `ep contract verify`, `ep iac` |
| **Audit Trails** | Enforced | Dim 4 append-only audit trail migration template (`templates/audit-log-migration.sql`) | `ep migration` |

### 🛡️ Group C: Reliability & Resilience
| Term | Status | Enforcement Mechanism | Command / Gate |
|---|---|---|---|
| **High Availability** | Enforced | Multi-replica IaC checks, zero-downtime expand/contract migrations | `ep iac`, `ep migration` |
| **Disaster Recovery** | Enforced | Automated RTO/RPO drill guidance, immutable backups | `references/release-and-milestone-governance.md` |
| **Fault Tolerance** | Enforced | Timeouts, retries with backoff, circuit breaker, bulkhead isolation | `ep quality`, `ep audit` |
| **Graceful Degradation** | Enforced | Fallback handlers, optional tooling degradation protocol | `references/optional-tooling.md` |
| **Circuit Breaker** | Enforced | Profile A resilience standard, Half-Open state validation | `templates/CHAOS_EXPERIMENT.template.md` |
| **Data Consistency** | Enforced | Zero-downtime Expand/Contract migrations, Transactional Outbox | `ep migration`, `templates/outbox-migration.sql` |
| **Timeouts & Deadlines** | Enforced | Dim 3 remote network timeout enforcement | `ep audit` |
| **Retries with Jitter** | Enforced | Dim 3 infinite retry blocker (`RULE-3.1-INFINITE-RETRY`), capped backoff | `ep audit`, `ep ast scan` |
| **Idempotency** | Enforced | Mutating route idempotency checker (`QUALITY-MUTATING-ROUTE-IDEMPOTENCY`) | `ep quality check`, `ep verify` (Gate 11) |
| **Backpressure** | Enforced | Dim 3 queue prefetch limiter (`RULE-3.7-UNBOUNDED-QUEUE-PREFETCH`) | `ep audit` |
| **Rate Limiting / Quotas** | Enforced | Public ingress rate limiting check (Dim 5.8), gateway policies | `references/architectural-profiles.md` |
| **Bulkheads** | Enforced | Isolated threadpools / client connection pools per dependency | `references/architectural-profiles.md` |
| **Graceful Shutdown / Drain**| Enforced | Server entrypoint shutdown linter (`QUALITY-GRACEFUL-SHUTDOWN-DRAIN`) | `ep quality check`, `ep verify` (Gate 11) |
| **Outbox / Saga / DLQ** | Enforced | Transactional outbox migration (`templates/outbox-migration.sql`), DLQ check | `ep migration`, `ep audit` |

### 🔒 Group D: Security & Compliance
| Term | Status | Enforcement Mechanism | Command / Gate |
|---|---|---|---|
| **Authentication & RBAC** | Enforced | Dim 5 identity and least-privilege verification | `ep audit` |
| **Encryption at Rest/Transit**| Enforced | TLS/HTTPS and KMS envelope encryption validation | `ep security`, `ep audit` |
| **Secrets Management** | Enforced | Pre-commit entropy & regex secret scanner (`ep security scan`) | `ep verify` (Gate 5) |
| **Secrets Rotation** | Enforced | Dynamic reload / dual-token overlap verification | `references/compliance-matrix.md` |
| **Compliance (SOC2/GDPR)** | Enforced | Compliance matrix mapping, data residency hooks | `references/compliance-matrix.md` |
| **Supply Chain Security** | Enforced | License copyleft scanner (`ep license`) + SBOM generator/validator | `ep license check`, `ep sbom` |
| **Threat Modeling** | Enforced | Formal threat model template (`templates/THREAT_MODEL.template.md`) | `templates/` |
| **SAST / DAST / SCA** | Enforced | Ast-grep structural invariant scanner, 10-dimension audit | `ep ast scan`, `ep audit` |
| **Zero Trust / Least Priv** | Enforced | IaC non-root user (`IAC-DOCKER-ROOT-USER`), unprivileged K8s pods | `ep iac` (Gate 9) |
| **Policy as Code** | Enforced | Conftest / OPA policy test integration with static fallback | `ep policy test` |
| **PII & Data Classification**| Enforced | Dim 6 PII log scrubber (`RULE-6.5-PII-LOGGING`) | `ep audit` |
| **Key Management (KMS)** | Enforced | Unencrypted private key blocker in secret scanner | `ep security scan` |
| **Multi-Tenancy Isolation** | Enforced | Tenant context scoping and RLS query isolation | `references/architectural-profiles.md` |

### 🚀 Group E: Engineering & Delivery
| Term | Status | Enforcement Mechanism | Command / Gate |
|---|---|---|---|
| **CI/CD** | Enforced | Multi-platform workflow generator (`ep ci init`), pre-commit hooks | `ep ci`, `ep hooks install` |
| **Testability & Test Pyramid**| Enforced | Domain isolation, test assertion quality (`RULE-10.1`, `RULE-10.2`) | `ep quality`, `ep audit` |
| **IaC & Immutable Infra** | Enforced | Containerfile & K8s/Compose security scanner (`ep iac`) | `ep iac` (Gate 9) |
| **Quality Gates** | Enforced | 12-Step unified mechanical gatekeeper suite | `ep verify` |
| **Code Review & ADRs** | Enforced | ADR template (`templates/ADR.template.md`), `-- adr-ref:` in migrations | `ep migration check` |
| **Feature Flags / Toggles** | Enforced | Lifespan and expiration tagging protocol | `references/audit-taxonomy.md` |
| **Canary / Blue-Green** | Enforced | Expand/Contract zero-downtime migrations | `ep migration` (Gate 4) |
| **GitOps & Branch Promotion**| Enforced | Multi-tier branch promotion (`main` -> `test` -> `stage` -> `prod`) | `ep vcs promote` |
| **Environment Parity** | Enforced | Real ephemeral containers for integration tests (Podman/Docker) | `ep container`, `ep quality` |
| **Contract Testing** | Enforced | OpenAPI / Protobuf schema validator & breaking change detector | `ep contract verify` |
| **CODEOWNERS** | Enforced | Code ownership verification & directory mapping | `ep codeowners check` |
| **DORA Metrics** | Enforced | Automated git-derived DORA metric calculator | `ep dora` |
| **Operational Runbooks** | Enforced | Service runbook existence checker (`QUALITY-SERVICE-RUNBOOK-MISSING`) | `ep quality check`, `ep verify` (Gate 11) |

### 🧩 Group F: Maintainability & Operability
| Term | Status | Enforcement Mechanism | Command / Gate |
|---|---|---|---|
| **Maintainability** | Enforced | Hard file ceiling ($\le 800$ lines), folder depth ($\le 6$ levels) | `ep audit`, `ep quality` |
| **Manageability** | Enforced | Unified CLI orchestrator | `ep` |
| **Performance Efficiency** | Enforced | Bounded collections, streaming, k6/locust stress tests | `ep perf` |
| **Documentation** | Enforced | 4-tier documentation system (`docs/adr`, `docs/runbooks`, `docs/changes`, `docs/nc`) | `references/documentation-system.md` |
| **FinOps / Cost Observability**| Enforced | Cloud cost annotations, budget tracking | `ep finops` |

### 📈 Group G: Performance & Deep Observability
| Term | Status | Enforcement Mechanism | Command / Gate |
|---|---|---|---|
| **Instrumentation & OTel** | Enforced | OpenTelemetry collector config, telemetry verification | `ep telemetry verify` |
| **APM & End-to-End Tracing** | Enforced | Traceparent propagation, distributed transaction tracking | `references/deep-observability.md` |
| **Trace Context Propagation**| Enforced | W3C header checks on remote calls (`RULE-6.7`) | `ep audit` |
| **Golden Signals / RED / USE**| Enforced | Standard metric types (`latency`, `error_rate`, `saturation`, `traffic`) | `ep slo` |
| **SLI / SLO / Error Budgets** | Enforced | Zero-dependency SLO YAML validator & error budget calculator | `ep slo` (Gate 10) |
| **Continuous Profiling** | Optional | Continuous profiling guidance and flame-graph collectors | `references/optional-tooling.md` |
| **RUM & Synthetic Probes** | Enforced | Scripted health probes, synthetic user load tests | `ep perf` |
| **Chaos Engineering** | Enforced | Game-day experiment scaffold, plan verification, and runner | `ep chaos scaffold`, `ep chaos verify` |
| **Load & Stress Testing** | Enforced | Performance runner supporting k6 and Locust harnesses | `ep perf --tool [k6\|locust]` |

### 🛠️ Tooling Guidance Extensions
| Tooling | Supported Action | CLI Command |
|---|---|---|
| **k6 Load Testing** | Multi-stage ramp-up, sustained load & stress spikes | `ep perf --tool k6 --script <path>` |
| **Locust Load Testing** | Python-based HTTP load testing harness | `ep perf --tool locust --script <path>` |
| **Chaos Engineering** | Scaffold experiment, verify protocol, run dry-run | `ep chaos [scaffold\|verify\|run]` |
| **Contract Testing** | Validate OpenAPI 3.x / Protobuf schemas | `ep contract verify [--file <file>]` |
| **SBOM (Software Bill of Materials)** | Generate CycloneDX/SPDX JSON, verify provenance | `ep sbom [generate\|verify]` |
