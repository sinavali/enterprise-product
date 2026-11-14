# Enterprise-Product (EP-OS) Technical Architecture Specification

**Document Version**: 2.0.0 (Consolidated Technical Specification)  
**Target Audience**: Software Engineers, System Architects, and AI Coding Agents  
**Companion Documents**: [README.md](../README.md) (General Overview), [SKILL.md](../SKILL.md) (Agent Skill Manifest)

---

## 1. Architectural System Overview

The Enterprise-Product Engineering Operating System (EP-OS) provides mechanical, deterministic governance for polyglot monorepos. EP-OS enforces rigorous engineering invariants across architectural boundaries, test fidelity, security postures, and release workflows.

### 1.1 Core System Components

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        AI Agent / Contributor                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Ingests
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│   SKILL.md (< 400 LOC)  &  AGENT.md (with Wake/Compaction Re-Read)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Commands
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Unified Mechanical CLI (`ep`)                         │
│               scripts/ep.py  (Zero-Dependency Python 3.10+)            │
├───────────────────────────────────┬────────────────────────────────────┤
│  Mechanical Verification Gates    │  Autonomous Engineering Workflows  │
│  - 10-Dimension Audit Suite       │  - Preflight & Doctor Self-Healing │
│  - Hexagonal Boundary Linter      │  - Pre-Impl Change Surface         │
│  - Shannon Entropy Secret Scan    │  - Single-Turn Context Packer      │
│  - Expand/Contract Migration Check│  - Ephemeral Container Detector    │
│  - 14-Day NC Aging Blocker        │  - Task DAG Kahn Runner            │
└───────────────────────────────────┴────────────────────────────────────┘
                                    │ Operates On
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Dedicated Workspace Isolation: `.ep/`                    │
│   ├── cache/ (AST hashes)   ├── surfaces/ (Branch surfaces)            │
│   └── sessions/ (Snapshots) └── dist/ (Release packages)               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Four Architectural Profiles

Every package in the monorepo must declare and strictly adhere to one of four architectural profiles in its manifest (`AGENT.md`):

### Profile A: Backend & Core Services (DDD + Hexagonal Architecture)

Profile A governs backend services, event-driven workers, and microservices across all languages (Go, Rust, TypeScript/Node, Python, C#, PHP/Laravel).

#### 1. Concentric Layer Model (Ports & Adapters)
```text
┌─────────────────────────────────────────────────────────────┐
│  Infrastructure Layer (Primary & Secondary Adapters)         │
│  - Primary: HTTP Routers, gRPC Controllers, Queue Consumers │
│  - Secondary: DB Repositories, Redis, Kafka, Clock, Auth    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Application Layer (Use Cases & Ports)                │  │
│  │  - Command & Query Handlers, Orchestration, DTOs      │  │
│  │  - Inbound Ports (Use Case Interfaces)                │  │
│  │  - Outbound Ports (Repository & Gateway Interfaces)   │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Pure Domain Layer (Entities & Invariants)      │  │  │
│  │  │  - Aggregate Roots, Entities, Value Objects    │  │  │
│  │  │  - Pure Domain Events, Business Rule Exceptions │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Dependency Inversion Rules
- **Domain Invariance**: The Domain layer imports nothing outside itself. It has zero dependencies on ORMs (Prisma, TypeORM, SQLAlchemy, GORM, Hibernate), web frameworks (Express, Fastify, Gin, Axum, FastAPI), or external cloud SDKs.
- **Port Definition**: Outbound ports (e.g. `UserRepositoryPort`, `EventPublisherPort`, `ClockPort`) are interfaces defined within the Application/Domain layer at the consumer site.
- **Adapter Implementation**: Secondary adapters in Infrastructure implement outbound ports (e.g. `PostgresUserRepository` implements `UserRepositoryPort`).

#### 3. Canonical Directory Layout
```text
services/<service-name>/
├── project.json                      # Nx / EP task targets
├── AGENT.md                          # Profile A manifest
├── src/
│   ├── domain/                       # Pure Domain Core
│   │   ├── entities/                 # Aggregates & entities with guarded state
│   │   ├── value-objects/            # Immutable value objects
│   │   ├── events/                   # Pure domain events
│   │   └── exceptions/               # Typed business domain errors
│   ├── application/                  # Application Use Cases
│   │   ├── ports/
│   │   │   ├── inbound/              # Use-case interfaces
│   │   │   └── outbound/             # Repository, messaging, clock interfaces
│   │   ├── use-cases/                # Command & query orchestrators
│   │   └── dto/                      # Boundary Data Transfer Objects
│   └── infrastructure/               # Infrastructure Adapters
│       ├── adapters/
│       │   ├── primary/              # HTTP controllers, gRPC, CLI, consumers
│       │   └── secondary/            # DB persistence, messaging, 3rd party APIs
│       └── config/                   # DI wiring, environment validation
└── tests/
    ├── unit/                         # Pure domain & use case tests (< 10ms, no I/O)
    ├── integration/                  # Real container tests (PostgreSQL/Redis/Kafka)
    └── contract/                     # API schema & wire compatibility tests
```

#### 4. Distributed Resilience Directives
- **Transactional Outbox**: Any use-case mutating aggregate state and publishing events must write to an `outbox_events` table within the same ACID database transaction.
- **Idempotency Keys**: Mutating ingress routes (POST, PUT, PATCH) must enforce an `Idempotency-Key` header with TTL-based deduplication (`RULE-4.7`).
- **Graceful Shutdown**: Server entrypoints must trap `SIGTERM`/`SIGINT`, stop accepting new traffic, drain in-flight connections within a 15–30s grace window, and cleanly terminate connection pools.

---

## Profile B: Web Applications (SSR, SSG, SPA)

Profile B governs client-facing web applications across all frameworks (Next.js, React, Vue, Nuxt, SvelteKit, Astro, Solid).

#### 1. Layering & Clean State Model
- `routes/`: Routing and page entrypoints. Zero business logic.
- `components/ui/`: Atomic design system primitives consuming centralized design tokens.
- `components/feedback/`: Explicit visual states: Loading skeletons, Error boundaries, Empty states, and Success states.
- `features/<feature>/`: Cohesive feature slices grouping composition components, state hooks, and stores.
- `contracts/`: Auto-generated API client bindings and runtime schema validators (Zod/Valibot).

#### 2. Non-Negotiable Web Mandates
- **SSR Hydration Safety**: Zero window/document access during SSR execution.
- **Accessibility (WCAG 2.2 AA)**: Interactive elements have accessible labels, full keyboard navigation, and proper ARIA semantics. Automated Axe-core test suites are mandatory.
- **Design Tokens**: Strict 4–6 semantic color hexes, consistent typographic scale, and spacing steps. Generic AI clichés (tracked-out all-caps, gradient washes) are banned.
- **Fluid Motion**: Interactions trigger on pointer-down with `setPointerCapture`. Animations use spring physics with interruptible velocity inheritance.
- **Zero-Trust Web Security**: Strict Content Security Policy (CSP), sanitized outputs against XSS, HTTP-only secure cookies.

---

## Profile C: Mobile Clients (Native iOS/Android, Flutter)

Profile C governs mobile applications (Swift/SwiftUI, Kotlin/Compose, Flutter/Dart, React Native).

#### 1. Layering & State Flow
- Clean architecture with Unidirectional State Flow (BLoC, MVI, or Redux).
- `core/`: Network clients, encrypted storage wrappers, error handling.
- `features/<feature>/`: Divided into `domain/` (pure entities & use-cases), `data/` (models & repositories), and `presentation/` (screens, widgets, BLoC).

#### 2. Mobile Mandates
- **Hardware-Backed Encrypted Storage**: All sensitive data, offline databases, and session tokens must use platform hardware enclaves (iOS Keychain, Android KeyStore, SQLCipher).
- **Offline-First Synchronization**: Mutating operations queue securely offline with idempotent sync and conflict resolution.
- **Battery & Lifecycle Awareness**: Timers, sync streams, and location listeners pause when the app is backgrounded.

---

## Profile D: Shared Contracts & Core Libraries

Profile D governs shared schemas, client SDKs, common utilities, and serialization protocols.

#### 1. Contract-First Architecture
- All schemas originate in machine-readable formats: OpenAPI 3.1 YAML, Protobuf v3, or JSON Schema.
- Automated Nx codegen targets:
  - `generate-ts`: TypeScript types and runtime Zod schemas for Profile B.
  - `generate-dart`: Dart models and client bindings for Profile C.
  - `generate-go`: Go structs and server interfaces for Profile A.
- **Mechanical Breaking Change Gate**: CI runs schema diffing (`oasdiff` or `buf breaking`) against `origin/main`. Breaking changes without a major SemVer bump trigger an immediate merge block.
- **Zero Ambient Side-Effects**: Shared libraries must not read environment variables, open network connections, or write to disk upon module import.

---

## 3. Universal Structural Boundaries & Anti-Sprawl Rules (Rule 2.6)

Regardless of profile, all code must respect strict structural boundaries:
1. **File Line Ceilings**:
   - Soft Target: $\le 400$ LOC.
   - Hard Limit: $800$ LOC (excluding generated code and lockfiles). Crossing 800 LOC without an accepted ADR is a blocking audit violation.
2. **Directory Nesting Depth**: Maximum 6 levels from project root. Over-nested procedural paths are rejected.
3. **Folder Density**: 3–25 files per directory. Folders containing $> 35$ files must be subdivided into logical sub-slices.
4. **Zero Generic Dumping Grounds**: Files must reside under recognized domain or architectural directories. Banned folders: `utils/`, `helpers/`, `common/`, `misc/`. Utilities must be domain- or capability-scoped (`src/crypto/`, `src/telemetry/`).

---

## 4. Value-Driven Testing Architecture

EP-OS enforces testing under realistic production conditions. Happy-path-only testing is strictly prohibited.

### 4.1 Coverage Matrix & Test Environments
| Layer / Component | Min Line Coverage | Min Branch Coverage | Execution Environment |
|---|---|---|---|
| Pure Domain Layer | $\ge 95\%$ | $\ge 95\%$ | In-process, zero I/O, ultra-fast ($< 10\text{ms}$) |
| Application Layer | $\ge 90\%$ | $\ge 90\%$ | In-process with port fakes/in-memory aggregates |
| Infrastructure Adapters | $\ge 80\%$ | $\ge 80\%$ | **Real ephemeral containers** (Podman / Testcontainers) |
| Web UI Components | $\ge 85\%$ | $\ge 80\%$ | Headless browser / jsdom + Axe-core a11y checks |
| Mobile State Machines | $\ge 90\%$ | $\ge 85\%$ | Native unit & widget test runner |
| Shared Contracts & SDKs | $\ge 95\%$ | $\ge 95\%$ | Roundtrip schema serialization & compatibility checks |

### 4.2 The Ephemeral Container Mandate
Substituting PostgreSQL or MySQL with in-memory SQLite in integration tests is strictly prohibited. Engine differences in transaction isolation, indexing, locking, and JSON operators introduce silent production defects. Tests must use real disposable container instances managed via Testcontainers or Podman quadlets.

### 4.3 Mandatory Five-Tier Suite
1. **Domain Unit Tests**: Pure invariants, state machines, boundary edge cases, zero network/disk I/O.
2. **Ephemeral Container Integration Tests**: Real datastores verifying migrations, complex SQL, transaction rollbacks, unique constraints.
3. **Contract & Compatibility Tests**: Schema alignment and wire compatibility.
4. **Failure & Resilience Tests**: Simulating network timeouts, 500 errors with exponential backoff & jitter, circuit breaker trips, DLQ message routing.
5. **Concurrency & Race Condition Tests**: Multi-threaded updates testing optimistic locking conflicts (`stale_object_error`) or safe row serialization.

---

## 5. Security & Performance Governance

### 5.1 Mandatory Security Audits
- **Endpoint Protection (`RULE-SEC-01`)**: All API routes and ingress endpoints must declare explicit authentication guards. Unprotected handlers trigger blocking audit defects.
- **Forbidden Unrestricted User Listings (`RULE-SEC-02`)**: Open `/users` endpoints exposing unrestricted tenant user directories without pagination, scoping, or administrative authorization are mechanically blocked.
- **API Route Permissions (`RULE-SEC-03`)**: Endpoints must declare granular permission scopes (e.g. `users:read`, `billing:write`).
- **Shannon Entropy Secret Scanner**: Scans staged diffs for high-entropy tokens, API keys, and credentials before commit.

### 5.2 Performance Governance
- **Unbounded Scan Prevention (`RULE-1.1`)**: Detects unindexed, unpaginated $O(n^2)$ scans across unbounded data collections.
- **Sub-Second Inner Loop**: Fast-path verification (`ep verify --diff`, `ep quality --diff`) must complete in $\le 1.0\text{s}$ using persistent AST hashing in `.ep/cache/ast_cache.json`.

---

## 6. VCS Governance & Zero-Drift Promotion Protocol

### 6.1 Multi-Tier Branch Hierarchy
Promotion follows a deterministic 4-tier pipeline:
$$\text{feat/* or fix/*} \implies \text{main (development)} \implies \text{test} \implies \text{stage} \implies \text{prod (production)}$$

`ep vcs sync-check` validates topology alignment across tiers, blocking unmerged drift.

### 6.2 The 2-Pass PR Self-Audit
1. **Pass 1 (Full Diff Self-Audit)**: Diff inspected against the 10-Dimension Audit Suite (`ep audit --diff origin/main`). Fixes applied, committed, and pushed.
2. **Pass 2 (Cumulative Re-Audit & Verification)**: CI verification (`nx affected -t lint,test,build`), branch sync check, and gate validation.
3. **Automated Merge vs Escalation**:
   - If 0 blocking defects and CI is green ➔ `gh pr merge --squash`.
   - If PR targets `prod` ➔ `ep pr create-prod` prepares a release candidate PR with auto-merge permanently disabled. Merges to `prod` are strictly human-only.

### 6.3 Elimination of File-Based Versioning
Historical file-based tracking (`docs/changes/` and `docs/releases/`) is completely eliminated. Versioning is governed exclusively by:
- Native Git commit history (Conventional Commits).
- Git diff trees between branches.
- Cryptographically signed Git tags (`git tag -s vX.Y.Z`).
- GitHub / GitLab Releases (`gh release create`).

---

## 7. Dedicated EP-OS Workspace (`.ep/`)

All generated artifacts, caches, and ephemeral state are confined strictly to `.ep/` on the project root:
- `.ep/cache/`: AST syntax hashes and dependency caches.
- `.ep/surfaces/`: Ephemeral per-branch Change Surfaces (`<branch>.json`).
- `.ep/sessions/`: Multi-session agent state machine checkpoints.
- `.ep/dist/`: Built release packages (replacing root `Packed.zip`).

The project root remains clean and uncluttered.
