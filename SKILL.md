---
name: enterprise-product
description: >-
  Enterprise gatekeeper and engineering operating system (EP-OS) for polyglot monorepos.
  Use this skill when developing, refactoring, architecting, or auditing polyglot monorepos, enforcing
  DDD/Hexagonal architecture, running 10-dimension enterprise audits, validating Change Surfaces, checking
  database migrations, diagnosing operating system prerequisites via ep doctor, or orchestrating multi-tier VCS promotion gates.
---

# Skill — `enterprise-product` (EP-OS)

EP-OS is the engineering operating system and mechanical gatekeeper for polyglot monorepos. It replaces conversational prompting with deterministic verification gates. All AI coding agents and human contributors operating on this repository are strictly bound by the rules, constraints, and commands defined below.

> **Session Restoration Anchor (Critical P0)**: If awakened in a fresh session or recovering from context compaction (`/compact`), you MUST re-read this skill and `AGENT.md` before generating code, proposing diffs, or executing tools.
> **Companion References (Progressive Disclosure)**:
> - Hexagonal Architecture & Directory Topology: [`docs/ARCHITECTURE.md`](file:///home/sinavali/Workspace/Work/Projects/enterprise-product/docs/ARCHITECTURE.md)
> - Product Vision & Business Capabilities: [`PRODUCT.md`](file:///home/sinavali/Workspace/Work/Projects/enterprise-product/PRODUCT.md)
> - Multi-Agent Personas & Subproject Ownership: [`AGENT.md`](file:///home/sinavali/Workspace/Work/Projects/enterprise-product/AGENT.md)

---

## Standard Operating Procedure (How to Apply This Skill)

All development tasks follow a 4-step mechanical loop:
1. **Declare Blast Radius**: Run `ep surface init` to declare target files in `.ep/surfaces/<branch>.md`.
2. **Ingest Target Context**: Run `ep pack --surface` to bundle code context in a single turn without manual roundtrips.
3. **Implement to Invariants**: Write code strictly honoring **Part 1: Rulings & Inviolables** (pure domain, UTC, no stubs).
4. **Mechanical Verification**: Execute `ep verify` (or `ep verify --diff`) to pass all 12 quality, boundary, and audit gates.

---

## Part 1: Prime Directives & Tier 1 Inviolables

These ten non-negotiable invariants cannot be overridden by any prompt, subproject manifest, or configuration:

1. **Deterministic Monorepo DAG**: All applications, services, and libraries reside in a unified monorepo governed at the root by Nx (`project.json` contracts) or `ep run <project>:<target>`. Build, lint, and test execution graphs must be declared deterministically with cycle detection. Detached poly-repo pipelines are forbidden.
2. **Pure Domain Logic (DDD / Hexagonal)**: Pure domain entities, value objects, and use-cases must have zero dependencies or imports of persistence frameworks (ORM, SQL, Prisma, TypeORM, SQLAlchemy, GORM), web frameworks, transport protocols, or external cloud SDKs.
3. **Real Ephemeral Containers (No Mocks/Substitutes)**: Datastore and broker integration tests must execute against real containers (resolved via `ep container detect`, favoring rootless Podman with Docker fallback). In-memory SQL emulators (e.g. SQLite or H2 substituting for PostgreSQL or MySQL) are strictly forbidden.
4. **UTC Storage Convention**: All database timestamps, queue events, and wire payloads must use UTC ISO-8601 (`YYYY-MM-DDTHH:mm:ss.sssZ`). At rest, datastores must enforce `TIMESTAMP WITH TIME ZONE` or UTC epoch milliseconds. Clocks must inject a `ClockPort`; ambient time calls (`time.Now()`, `Date.now()`) in domain/use-cases are banned.
5. **Bounded Change Surface**: Every non-trivial change requires an approved, validated Change Surface (`.ep/surfaces/<branch>.json` or `CHANGE_SURFACE.md`). The mechanical gate (`ep surface check-diff`) halts execution if any file outside the declared surface is touched.
6. **Anti-Sprawl Ceilings (Rule 2.6)**: Hard ceiling $\le 800$ LOC (soft target $\le 400$ LOC); directory depth $\le 6$ levels from root; folder density 3–25 files (split if $> 35$ files); zero generic dumping grounds (`utils/`, `helpers/`, `common/`, `misc/`). Utilities must reside in domain- or capability-qualified modules (`src/crypto/`, `src/formatting/`).
7. **Expand/Contract Database Migrations**: Zero-downtime database migrations only. Destructive DDL (instant column drops, column renames, adding non-null columns without defaults) is blocked by `ep migration check`.
8. **14-Day NC Merge Block**: Ambiguities and missing domain specs must be recorded as formal `NEED_CLARIFICATION` items (`templates/NEED_CLARIFICATION.template.md`). Any open NC item older than 14 calendar days mechanically halts automated merges (`ep nc check`).
9. **Strict Human-Only Production Gate**: AI agents are strictly forbidden from merging into `prod`. Agents may only prepare release candidate PRs (`ep pr create-prod`) with auto-merge permanently disabled. Merging to `prod` requires human verification.
10. **Anti-MVP & Zero-Stub Mandate**: AI agents and developers are strictly forbidden from proposing or implementing "MVP", "PoC", mock-first, or phased hardening shortcuts. Every deliverable—regardless of how narrow its scope—must be the finalized, fully resilient, production-ready implementation with complete error handling, timeouts, retries, and ephemeral container verification from turn one.

---

## Part 2: Zero-Latency High-Velocity Execution Engine (P0)

1. **Compound Shell Commands**: Always combine related commands using `&&` or pipelines in a single `run_command` invocation (e.g. `cmd1 && cmd2`). Never serialize sequential roundtrips.
2. **Parallel Tool Batching**: Emit multiple independent tool calls (e.g. parallel `view_file` or lookups) simultaneously in the same turn.
3. **Single-Turn Context Ingestion**: Run `python3 scripts/ep.py pack --surface` or `ep pack --diff` to inject all target files into context in a single bash turn before editing. Never read codebase files sequentially one-by-one.
4. **Sub-Second Fast-Path Verification**: Use fast-path flags (`ep verify --diff`, `ep quality --diff`) during inner development loops to verify only touched files in $< 1.0\text{s}$.
5. **Context Hygiene**: Redirect verbose build/install logs to `/tmp/*.log`. Bound file views (`StartLine`/`EndLine`). Maintain lossless technical density (zero pleasantries or conversational filler).

---

## Part 3: Operational Modes Reference

| Mode | Trigger / Purpose | Primary Tooling & Command |
|---|---|---|
| `preflight` | First-turn environment & permission verification | `ep preflight && ep doctor` |
| `plan` | Analyze blast radius, declare & validate Change Surface | `ep surface init && ep surface validate <file>` |
| `investigate` | Root-cause analysis, reproduce bug in real container | `ep container detect &&` author red tests |
| `scaffold` | Scaffold compliant subprojects and Nx contracts | `ep init <name> --profile [A\|B\|C\|D] --lang <stack>` |
| `implement` | TDD implementation bounded to Change Surface (1-turn pack) | `ep pack --surface && ep quality --diff` |
| `audit` | Run 10-Dimension Enterprise Audit across diff | `ep audit --diff origin/main...HEAD` |
| `verify` | 12-Step unified mechanical compliance suite | `ep verify [--diff] [--surface]` |
| `pr-audit` | 2-Pass PR Self-Audit: Pass 1 audit -> fixes -> Pass 2 verify -> merge | `ep vcs sync-check && gh pr merge --squash` |
| `session` | Save / resume multi-session workspace checkpoints | `ep session save` / `ep session resume` |
| `sync` | Validate multi-tier branch alignment (`main`, `test`, `stage`, `prod`) | `ep vcs sync-check` |
| `release` | Orchestrate SemVer bumps and signed release tags via Git VCS | `ep release create` / `ep release finalize` |
| `ops` | Operational readiness: containers, SLOs, DORA, k6, IaC | `ep container status && ep slo --file <path>` |
| `adopt` | Brownfield monorepo onboarding and baseline ratchets | `ep adopt [--apply] --profile [A\|B\|C\|D]` |
| `manifest` | Universal manifest projection from `AGENT.md` | `ep manifest sync` |

---

## Part 4: Architectural Profiles (A – D)

### Profile A: Backend & Core Services (DDD + Hexagonal Architecture)
- **Layer Rings**: `domain/` (pure entities, value objects, events, errors; zero framework/ORM/SDK imports); `application/` (use-cases, command/query handlers, inbound/outbound ports); `infrastructure/` (primary adapters: HTTP/gRPC; secondary adapters: DB/queue, external APIs, DI config).
- **Distributed Integrity**: Mutating use-cases publishing events must use Transactional Outbox (`outbox_events` table in same ACID transaction; direct network publishing banned). Mutating endpoints (POST/PUT/PATCH) require `Idempotency-Key` with TTL deduplication. Graceful `SIGTERM`/`SIGINT` shutdown (15–30s drain).
- **Language Invariants**: Go: unexported struct fields, aggregate methods, consumer-site interfaces, typed errors. Rust: algebraic enums, newtype IDs (`struct OrderId(Uuid);`), `Result<(), DomainError>`.
- **Forbidden**: Anemic domain models, leaking ORM into domain, SQLite substitute for PostgreSQL/MySQL, ambient time (`time.Now()` without `ClockPort`), ORM annotations on domain types.

### Profile B: Web Applications (SSR, SSG, SPA)
- **Layering**: `routes/` (routing & page entrypoints); `components/` (design system `ui/`, `feedback/`); `features/<feature>/` (feature composition, state hooks, stores); `contracts/` (API clients, Zod/Valibot runtime validators).
- **Mandates**: SSR hydration safety (zero window/document/localStorage in SSR); WCAG 2.2 AA accessibility (automated Axe-core tests mandatory); centralized design tokens (4–6 semantic colors, consistent typography, spacing scale; AI clichés banned); fluid motion (pointer-down interactions with `setPointerCapture`, spring physics); zero-trust web security (strict CSP, XSS output sanitization, HTTP-only secure cookies).
- **Forbidden**: Direct API fetches inside presentation components, missing Loading/Empty/Error/Success states, parsing untyped external data without runtime schemas.

### Profile C: Mobile Clients (Native iOS, Android, Flutter)
- **Layering**: `core/` (network clients, encrypted storage wrappers, error handling); `features/<feature>/` (`domain/` pure entities & use-cases, `data/` datasources & repositories, `presentation/` screens, widgets, BLoC/view-models).
- **Mandates**: Clean mobile architecture with unidirectional state flow (BLoC/MVI/Redux); hardware-backed encrypted storage (iOS Keychain, Android KeyStore, SQLCipher); offline-first synchronization with idempotent conflict resolution; lifecycle & battery awareness (pause sync streams on app backgrounding).
- **Forbidden**: Business logic in UI view lifecycle, raw unencrypted local storage, importing UI frameworks (`UIKit`, `flutter`) into domain layer.

### Profile D: Shared Contracts & Core Libraries
- **Mandates**: Contract-first design (OpenAPI 3.1 YAML, Protobuf v3, JSON Schema); automated multi-target codegen in Nx (`generate-ts`, `generate-dart`, `generate-go`); mechanical breaking change gate (`oasdiff` or `buf breaking` against `origin/main` blocks PRs without major SemVer bump); pure functional transformations (zero ambient side-effects on import).
- **Forbidden**: Heavy transport or UI framework dependencies inside contract packages.

---

## Part 5: Value-Driven Testing Matrix

### 5.1 Coverage & Execution Gates
| Component / Scope | Min Line Coverage | Min Branch Coverage | Execution Environment |
|---|---|---|---|
| **Pure Domain Layer** | **$\ge 95\%$** | **$\ge 95\%$** | In-process, zero I/O, ultra-fast ($< 10\text{ms}$) |
| **Application Layer** | **$\ge 90\%$** | **$\ge 90\%$** | In-process with port fakes/in-memory aggregates |
| **Infrastructure Adapters** | **$\ge 80\%$** | **$\ge 80\%$** | **Real ephemeral containers** (Podman / Testcontainers) |
| **Web UI Components** | **$\ge 85\%$** | **$\ge 80\%$** | Headless browser / jsdom + Axe-core a11y checks |
| **Mobile State Machines** | **$\ge 90\%$** | **$\ge 85\%$** | Native unit & widget test runner |
| **Shared Contracts & SDKs** | **$\ge 95\%$** | **$\ge 95\%$** | Roundtrip schema serialization & compatibility checks |

### 5.2 Mandatory Five-Tier Test Architecture
1. **Domain Unit Tests**: Pure business invariants, state transitions, boundary edge cases, zero I/O.
2. **Ephemeral Container Integration Tests**: Real datastores (PostgreSQL, Redis, Kafka) running via Podman/Testcontainers. Verify migrations, SQL queries, transactional rollback, unique constraints. In-memory SQL emulators (`:memory:`) are banned.
3. **Contract & Compatibility Tests**: OpenAPI/Protobuf schema alignment and backward compatibility.
4. **Failure & Resilience Tests**: Client timeouts, upstream 500 exponential backoff with jitter, circuit breaker tripping and fallback, unprocessable message DLQ routing.
5. **Concurrency & Race Condition Tests**: Multi-threaded updates asserting optimistic lock collision handling (`stale_object_error`) or safe row-level serialization.
- **UI State Machine Matrix**: Dynamic views must explicitly test 4 states: Loading, Empty, Success, and Error (with retry).
- **Mocking Rules**: Banned for internal business logic. Permitted only at system edge for uncontainerizable 3rd parties (Stripe, Twilio). Clock virtualization via `ClockPort`. Mutation score $\ge 85\%$ on critical business logic.

---

## Part 6: The 10-Dimension Enterprise Audit Checklist

Evaluate every diff against these 10 dimensions. Blocking defects halt merges:

- **Dim 1: Scalability & Capacity**: No $O(n^2)$ on unbounded data (`RULE-1.1`). Queries indexed and paginated (`LIMIT`/cursor). Connection pooling with timeouts. Streaming I/O for large payloads. Stateless services. Container CPU/memory limits.
- **Dim 2: Structural Modularity**: Adherence to Profile A–D. Layer isolation (zero ORM in domain). No circular dependencies. Nesting depth $\le 6$. File size $\le 800$ LOC. Folder file count $\le 25$. Zero generic dumping grounds (`utils/`, `helpers/`). Contract-first APIs.
- **Dim 3: Fault Tolerance & Resilience**: Explicit timeouts on all network calls. Exponential backoff with jitter and retry caps on idempotent operations. Circuit breakers for critical dependencies. Dead Letter Queues for consumers. `SIGTERM` drain (15–30s). Multi-replica anti-affinity. Backpressure limits.
- **Dim 4: Data Integrity & Concurrency**: Optimistic locking / row locks on concurrent updates. Atomic multi-table transactions. Idempotent event consumers. Strict UTC storage (`TIMESTAMP WITH TIME ZONE`). Transactional outbox pattern. Zero-downtime expand/contract migrations. `Idempotency-Key` headers on mutating routes.
- **Dim 5: Security & Zero-Trust**: Parameterized SQL queries (zero concatenation). Mandatory endpoint protection (`RULE-SEC-01` authentication guards). Forbidden unrestricted user listings (`RULE-SEC-02` blocking open `/users`). API route permission checks (`RULE-SEC-03` explicit scopes). Zero hardcoded secrets (Shannon entropy scanner). Web CSP, XSS sanitization, HTTP-only secure cookies. Hardware-backed mobile encryption. Tenant isolation (RLS / `tenant_id`). Dependency CVE scans. Public rate limiting.
- **Dim 6: Observability & Operability**: Structured JSON logging. Distributed trace propagation (W3C `traceparent`). Health probes (`/healthz`, `/readyz`). OpenTelemetry metrics. Automatic PII/secret scrubbing. Bounded metric cardinality (no user IDs in metric tags).
- **Dim 7: Contract & Schema Drift**: Implementation matches OpenAPI/Protobuf specs. Zero direct cross-project relative imports bypassing published contracts (`RULE-7.1`). Backward compatibility preserved (no unversioned field drops). Automated SDK regeneration.
- **Dim 8: Code Quality & Typing**: Strict typing (zero `any`). Strict null safety. Custom typed errors with context (zero empty catch blocks or swallowed errors). Immutable value objects. Anti-MVP/zero-stub compliance. 12-factor typed config validated on boot.
- **Dim 9: Documentation & Spec Drift**: Implementation matches declared Change Surface. ADR recorded for any Tier 2 deviation (`docs/adr/`). Zero open NC items $> 14$ days. Complex domain logic documented. Operational runbook exists for all deployable services.
- **Dim 10: Test Fidelity & Quality**: Non-happy-path suites included. Real ephemeral containers for DB/broker tests. Zero tautological assertions. Coverage thresholds met ($\ge 95\%$ domain, $\ge 80\%$ adapters). Concurrency race tests present.

---

## Part 7: Unified Mechanical CLI Reference (ep)

All commands execute via `python3 scripts/ep.py <cmd>` or launcher `scripts/bin/ep <cmd>`:

| Command Category | Command Syntax | Description |
|---|---|---|
| **Diagnostic & System** | `ep doctor [--heal]` | Audit & autonomously heal 7 OS prerequisites |
| | `ep preflight` | Verify shell, git, python, and workspace write permissions |
| | `ep manifest sync` | Project canonical `AGENT.md` to `CLAUDE.md`, `.cursorrules`, `.windsurfrules` |
| **Change Surface** | `ep surface init` | Auto-detect modified projects and scaffold Change Surface |
| | `ep surface validate <file>` | Validate syntax, frontmatter, and completeness of Change Surface |
| | `ep surface check-diff [--base <ref>]` | Halt execution if changes touch files outside declared surface |
| **Velocity & Context** | `ep pack [--surface] [--diff] [--files ...]` | Batch-pack codebase files into single-turn context bundle |
| **Task Execution** | `ep run <project>:<target>` | Execute target in topological DAG order with cycle detection |
| | `ep run-many --target=<target> --parallel`| Run target across affected projects concurrently |
| **Code Intelligence** | `ep ast scan [--scope <dir>]` | Structural AST syntax scanning via `ast-grep` |
| | `ep verify --check-boundaries` | Lint Hexagonal domain and library boundaries |
| **Audits & Verification** | `ep audit [--diff <base>] [--scope <dir>]`| Execute 10-Dimension Enterprise Audit with scorecard |
| | `ep verify [--diff <base>] [--surface]` | Unified mechanical gatekeeper suite (12 gates) |
| | `ep quality [--diff <base>] [--surface]` | Check idempotency, graceful drain, ephemeral DBs & domain purity |
| | `ep migration check [--dir <dir>]` | Zero-downtime Expand/Contract database migration linter |
| | `ep nc check [--max-age 14]` | Audit `NEED_CLARIFICATION` items for 14-day merge block |
| **Security & Contracts** | `ep security scan [--diff <base>]` | Shannon entropy secret scanner & IaC security gate |
| | `ep contract verify [--file <path>]` | OpenAPI and Protobuf schema contract validation |
| | `ep license check [--package-json <path>]`| Dependency copyleft compliance scanner |
| **Git & Release Gates** | `ep vcs sync-check` | Validate alignment between `main`, `test`, `stage`, and `prod` |
| | `ep vcs init-branches` | Initialize multi-tier promotion branches |
| | `ep pr create-prod` | Create human-only production PR with auto-merge blocked |
| | `ep release create <version>` | Prepare release tag and notes via Git VCS |
| | `ep release finalize --prod` | Finalize production release in Git VCS |
| **Ops & Sessions** | `ep container [status\|detect]` | Smart OCI container engine detector & socket resolver |
| | `ep slo [--file <path>]` | Validate SLO schemas, thresholds, and error budgets |
| | `ep session save` / `ep session resume` | Checkpoint and restore agent working memory |
| | `ep adopt [--apply] --profile [A\|B\|C\|D]` | Scan and onboard brownfield monorepos |
| | `ep sync-skill [--check] [--direction]` | Synchronize skill with workspace repository |
