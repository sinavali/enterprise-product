# Enterprise Core Directives & Master Rulebook

This specification defines the foundational laws of the `enterprise-product` engineering operating system. All AI agents, contributors, and automated pipelines are bound by these directives.

---

## 1. Prime Directives (P1 – P10)

### P1: Deterministic Monorepo Orchestration
Every enterprise product is strictly contained within a single monorepo governed by a deterministic DAG task orchestrator (with **Nx** as the standard reference implementation). Cross-boundary dependencies, project boundaries, and CI/CD task graphs must be declared deterministically. No rogue repositories or detached poly-repo pipelines are permitted.

### P2: Hierarchical Governance via `AGENT.md`
Governance cascades strictly from the repository root to project subdirectories:
$$\text{Enterprise Inviolables} \implies \text{Root AGENT.md} \implies \text{Subproject AGENT.md}$$
Subproject manifests configure local toolchains, build targets, and domain profiles, but can never dilute or override Tier 1 directives.

### P3: Strict Architectural Boundary Isolation
Every codebase component must declare and adhere to an approved **Architectural Profile** (Profile A: Backend DDD/Hexagonal, Profile B: Web Applications, Profile C: Mobile Clients, Profile D: Shared Contracts). Domain logic must remain pure, isolated from frameworks, databases, and UI presentation concerns.

### P4: Value-Driven & Real-World Testing
Happy-path-only testing is strictly prohibited. Integration and adapter tests must execute against **real ephemeral containers (Testcontainers/Podman)**; engine-substitution emulators (e.g., in-memory SQLite replacing PostgreSQL/MySQL) are banned. (Testing against SQLite is permitted only when SQLite is the actual production engine). Boundary invariants, race conditions, resilience timeouts, and error paths must be tested.

### P5: Impact Before Implementation (Change Surface)
No non-trivial modification to code, configuration, or contracts may begin without an approved and mechanically validated **Change Surface** artifact (`CHANGE_SURFACE.md` or `docs/changes/YYYYMMDD-<slug>.md`). Agents must discover the blast radius before altering files.

### P6: 2-Pass PR Self-Audit & Zero-Drift Gates
Every Pull Request must undergo a mandatory 2-Pass Self-Audit against the 10-Dimension Enterprise Audit Suite before merge eligibility. Automated squash-merging (`gh pr merge --squash`) is permitted only when 0 blocking defects remain and CI is fully green; otherwise, immediate escalation occurs.

### P7: Complete Documentation & NC Transparency
Ambiguities and missing domain knowledge must not be guessed or invented. They must be registered immediately as formal **`NEED_CLARIFICATION` (NC)** items. Unresolved NC items older than 14 days mechanically block PR merges. Architectural decisions must be preserved as Architecture Decision Records (ADRs).

### P8: Sovereign & Zero-Trust Infrastructure
Systems prioritize self-hosted, vendor-agnostic infrastructure (Podman, Docker, Kubernetes, PostgreSQL, Redis, MinIO). All data storage, event streaming, and API wire formats must strictly enforce the **UTC Storage Convention** and zero-trust security postures.

### P9: Structural Bounding & Anti-Sprawl Hygiene
AI agents and developers must maintain disciplined file and folder boundaries. Codebase bloat, hyper-fragmentation into microscopic files, deeply nested hierarchies, and uncohesive dumping grounds are strictly forbidden:
- **File Size Ceilings**: Files must not exceed 800 lines of code (hard ceiling), with a recommended target of $\le 400$ lines (excluding auto-generated code and lockfiles).
- **Directory Nesting Depth**: Directories must not exceed 6 levels of nesting from project root.
- **Micro-File Anti-Fragmentation**: Avoid creating single-class or single-function files with $< 20$ lines when types are tightly cohesive. Co-locate closely related value objects, commands, queries, or helper types within a single cohesive module.
- **Known Directory Taxonomy**: Code must reside strictly within declared architectural layer directories (`domain/`, `application/`, `infrastructure/`, `components/`, `features/`, etc.). Generic dumping grounds (`utils/`, `helpers/`, `misc/`, `common/`) are prohibited.

### P10: Zero-Downtime Evolution & Distributed Integrity
Enterprise products must remain reliable across deployments and distributed boundaries:
- **Expand/Contract Database Migrations**: Breaking database changes must follow a phased expand/contract pattern. Instant breaking schema alterations during rolling updates are forbidden.
- **Transactional Outbox for Domain Events**: In distributed architectures, publishing domain events must occur atomically via a transactional outbox table rather than risky dual-write patterns.
- **Idempotency on Mutating Endpoints**: Mutating API boundaries (POST/PUT/PATCH for billing, orders, money transfer) must support and enforce an `Idempotency-Key` header with TTL caching.
- **Graceful Shutdown & Drain**: All server processes must trap `SIGTERM`/`SIGINT`, halt accepting inbound traffic, drain active requests within a 15–30s window, and gracefully release database pools.

### P11: Single-Turn Context Ingestion (Anti-Serialization Mandate)
AI agents operating on enterprise products are **strictly prohibited from reading codebase files sequentially one-by-one across multiple conversational turns**. Sequential file reading introduces compounding network and turn latency. Agents and developers must use single-turn compound ingestion:
- **Change Surface Packing**: Run `python3 scripts/ep.py pack --surface` to bundle all declared target files into stdout in a single command.
- **Git Diff Packing**: Run `python3 scripts/ep.py pack --diff` to ingest all modified and staged files in one turn.
- **Direct Terminal Bundling**: Execute `tail -n +1 <file1> <file2> ...` in a single compound command to inject files directly into the model context before editing.

---

## 2. The Tiering Map

All architectural and engineering rules are categorized into three hierarchical tiers:

```text
┌────────────────────────────────────────────────────────┐
│  Tier 1: Enterprise Inviolables (Zero-Overridable)     │
│  - Monorepo DAG Standard  - Real DB Containers (No Sub)│
│  - Pure Domain (DDD)      - 2-Pass PR Self-Audit       │
│  - UTC Storage Convention - 14-Day NC Merge Block      │
│  - Expand/Contract Rule   - Max Directory Depth ≤ 6    │
│  - Anti-MVP / Zero-Stub   - Human-Only Prod Merges     │
├────────────────────────────────────────────────────────┤
│  Tier 2: Strong Defaults (ADR & AGENT.md Justified)    │
│  - Coverage Targets (≥95% Domain, ≥80% Adapters)       │
│  - File Line Ceiling (≤800 Lines per File)             │
│  - Port-Adapter Separation & Transactional Outbox      │
│  - OpenAPI / Protobuf Contract Generation              │
│  - Idempotency-Key Enforcement on Mutating Boundaries  │
├────────────────────────────────────────────────────────┤
│  Tier 3: Context-Dependent / Advisory (Local Ergonomics)│
│  - Framework UI component styling / UI state nuance    │
│  - Internal file co-location grouping decisions        │
│  - Local dev caching / tooling ergonomics              │
└────────────────────────────────────────────────────────┘
```

### Tier 1: Enterprise Inviolables (Non-Negotiable)
These rules cannot be relaxed, bypassed, or overridden by any project, developer, or agent:
1. **Single Monorepo via Deterministic DAG**: Root orchestration manages `lint`, `test`, `build`, and `audit` across all packages.
2. **Pure Domain Logic**: Domain entities, value objects, and domain services must have zero imports from frameworks, ORMs, transport layers, or external third-party SDKs.
3. **No Engine-Substitution Emulation**: Integration tests must execute against the exact database engine and major version utilized in production via real ephemeral containers (Podman/Testcontainers). Replacing PostgreSQL/MySQL with in-memory SQLite is strictly forbidden. The active container engine is automatically and intelligently resolved across platforms via `ep container detect` (preferring rootless Podman with seamless Docker fallback).
4. **UTC Storage Convention**: All database timestamps, queue messages, events, and API payloads must be persisted and exchanged in UTC (ISO 8601 with `Z` or UTC timestamp).
5. **Mandatory Change Surface**: No non-trivial implementation without an approved and validated Change Surface.
6. **Anti-Sprawl Hygiene (Rule 2.6)**: Files must not exceed 800 lines (soft target $\le 400$ lines), directory nesting must not exceed 6 levels, and zero generic dumping grounds (`utils/`, `helpers/`, `common/`) are allowed.
7. **Zero-Downtime Expand/Contract Migrations**: Destructive database alterations that break rolling blue/green deployments are strictly forbidden.
8. **14-Day NC Merge Block**: Any open `NEED_CLARIFICATION` item older than 14 calendar days mechanically halts automated merges and triggers review escalation.
9. **Strict Human-Only Production Gate**: AI agents are strictly forbidden from merging into `prod`. Agents may only prepare release candidate PRs (`ep pr create-prod`) with auto-merge disabled.
10. **Anti-MVP & Zero-Stub Mandate**: AI agents and developers are **strictly forbidden from proposing or implementing 'MVP', 'Proof-of-Concept', 'mock-first', or 'phased hardening' shortcuts**. Every deliverable—regardless of how narrow or bounded its scope—must be the finalized, fully resilient, production-ready implementation with complete error handling, timeouts, retries, and ephemeral container verification from the outset. Deferring production hardening to future steps or versions is a blocking violation.

### Tier 2: Strong Defaults (Requires ADR & `AGENT.md` Override)
These are standard enterprise requirements. Deviations are permitted only with an accepted Architecture Decision Record (ADR) and explicit declaration in the subproject's `AGENT.md`:
1. **Coverage Thresholds**: $\ge 95\%$ Line/Branch coverage for domain packages; $\ge 80\%$ Line coverage for adapters and HTTP handlers.
2. **File Size Ceiling ($\le 800$ lines)**: Files must remain modular. Files exceeding 800 lines require refactoring or an ADR justifying monolithic grouping (e.g. complex mathematical state machines).
3. **Transactional Outbox Pattern**: Mutating operations publishing domain events to message brokers must persist events to a transactional outbox table within the same atomic database transaction.
4. **Contract-First APIs**: External APIs must derive from OpenAPI or Protobuf schemas.
5. **Idempotency-Key Support**: Critical mutating REST/gRPC endpoints must implement idempotency key tracking.
6. **Strict Hexagonal Isolation**: Use cases access external services through interface ports. (See YAGNI carve-out below).

### Tier 3: Context-Dependent / Advisory
Ergonomic guidelines determined by project teams:
1. Internal folder structure for UI widgets within component libraries.
2. Selection of client-side cache utilities (React Query, SWR, TanStack) within Profile B applications.
3. Local development seed script syntax and test fixtures.

---

## 3. Operational Protocols & Carve-Outs

### 3.1 Self-Hosted Infrastructure Preference
Enterprise products must remain deployable on sovereign infrastructure without proprietary vendor cloud lock-in:
- **Compute**: Standard container images (OCI compliant) orchestratable via Kubernetes, Docker Compose, or Podman quadlets.
- **Data Persistence**: Standard open-source datastores (PostgreSQL, Redis, ClickHouse, MinIO S3-compatible storage).
- **Vendor SDK Ban in Domain**: Proprietary cloud SDKs (AWS SDK, Azure SDK, Firebase) must be completely encapsulated behind secondary adapters. Domain logic must never reference cloud vendor symbols.

### 3.2 The Hexagonal Port YAGNI Carve-Out
While Profile A mandates Hexagonal Architecture (Ports and Adapters), premature interface bloat violates simplicity:
- **Port Required**: Whenever a dependency crosses an external boundary (Databases, Third-Party APIs, Message Brokers, Email Services, Clock/Time, Filesystem, Authentication providers).
- **YAGNI Carve-Out (Direct Dependency Allowed)**: Internal pure domain utilities, mathematical functions, string parsers, and in-process stateless value objects do **not** require an abstract interface/port if there is only ever one in-memory implementation. Do not create an `IStringManipulator` for standard library utilities.

### 3.3 The UTC Storage Convention
Timezone mishandling is a critical class of enterprise defects:
1. **At Rest**: Every timestamp column in PostgreSQL/MySQL must use `TIMESTAMP WITH TIME ZONE` (PostgreSQL) or UTC `DATETIME`/`BIGINT` milliseconds. Storing local timezone offsets or string representations like `EST` is forbidden.
2. **In Motion**: All JSON/REST and Protobuf contracts must serialize timestamps in ISO 8601 UTC format: `YYYY-MM-DDTHH:mm:ss.sssZ` or Unix epoch milliseconds UTC.
3. **In Logic**: Domain calculations must utilize UTC clock ports (`Clock.UtcNow()`). The local timezone of the running server or container is irrelevant and must be treated as `UTC`.
4. **Presentation**: Conversion to user-local timezone occurs strictly at the edge UI display layer (Profile B or Profile C).

### 3.4 Zero-Downtime Database Migration Protocol (Expand/Contract)
All schema migrations in enterprise production must follow the Expand/Contract phased lifecycle:
```text
┌────────────────────────────────────────────────────────┐
│ Phase 1: Expand                                        │
│ - Add new column as NULLABLE or with DEFAULT           │
│ - Create new tables and non-blocking indexes           │
├────────────────────────────────────────────────────────┤
│ Phase 2: Dual-Write (Application Layer)                │
│ - Application writes to BOTH old and new structures    │
│ - Application continues reading from old structure     │
├────────────────────────────────────────────────────────┤
│ Phase 3: Backfill                                      │
│ - Asynchronous script backfills old data into new      │
├────────────────────────────────────────────────────────┤
│ Phase 4: Read Switch                                   │
│ - Application switches reads to new structure          │
├────────────────────────────────────────────────────────┤
│ Phase 5: Contract (Cleanup)                            │
│ - Old structure is deprecated, decoupled, then dropped │
└────────────────────────────────────────────────────────┘
```
Direct destructive operations (e.g., dropping or renaming an active column in a single migration) are strictly classified as **blocking defects** during audit.

### 3.5 Structural Anti-Sprawl & File/Folder Bounding Protocol
To prevent codebase fragmentation and cognitive overhead:
1. **File Merging & Co-Location**: When defining tightly coupled domain artifacts (e.g. an Aggregate Root and its 2-3 small Value Objects, or a Command and its Response DTO), co-locate them in the same file rather than creating multiple 10-line files.
2. **File Splitting**: When any file exceeds 400 lines, evaluate splitting into cohesive sub-units. When it exceeds 800 lines, splitting is mandatory unless justified by an ADR.
3. **Directory Depth Limit**: Deep nesting beyond 6 directory levels (e.g. `src/a/b/c/d/e/f/g/file.ts`) is mechanically rejected. Keep hierarchies flat and cohesive.
4. **Zero Dumping Grounds**: Folders named `utils`, `helpers`, `misc`, `common`, or `shared-utils` with vague purposes are rejected. Utilities must be categorized by domain or technical concern (e.g. `src/crypto/`, `src/telemetry/`, `src/validation/`).

### 3.6 Operating System Self-Healing & Free-Tier/Sovereign Governance
EP-OS operates as an autonomous operating system rather than a passive documentation standard:
1. **Prerequisite Diagnostic & Self-Healing (`ep doctor [--heal]`)**: Validates 7 core operating system prerequisites:
   - Git Hooks: Native client-side pre-commit, pre-push, and commit-msg hooks.
   - VCS Promotion Topology: Full presence of promotion branches (`main`, `test`, `stage`, `prod`).
   - Ownership: Deterministic `.github/CODEOWNERS` mapping every monorepo subproject.
   - Task Contracts: Valid `project.json` declaring `lint`, `test`, `build`, and `audit` Nx targets.
   - Governance Manifest: Active root `AGENT.md`.
   - OCI Container Engine: Available rootless Podman or Docker engine.
   - Tailored Product Skill: Compiled `PRODUCT_SKILL.md`.
   Running `ep doctor --heal` autonomously creates, installs, and configures all missing components.
2. **Sovereign & Free-Tier Governance**:
   In environments lacking paid cloud branch protection rulesets (such as GitHub Free private repositories or air-gapped sovereign environments), EP-OS enforces zero-compromise multi-tier governance locally via zero-dependency native git hooks. Force-pushes, direct rogue commits to `test`/`stage`/`prod`, and agent production merges are mechanically blocked by client-side hooks without requiring any paid SaaS subscription.
3. **Tailored Product Skill Generation (`ep skill generate`)**:
   To prevent AI agent context memory exhaustion and eliminate sequential file-reading latency, EP-OS inspects monorepo subprojects and compiles a dedicated, compact `< 150` line `PRODUCT_SKILL.md`. This localized skill includes project-to-profile mappings, active architectural invariants, and single-turn ingestion commands (`ep pack`), allowing agents to execute at peak velocity.
