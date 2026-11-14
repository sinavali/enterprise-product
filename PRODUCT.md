# Enterprise-Product (EP-OS) — Product Context & Ubiquitous Language

**Living Product Context for Humans and AI Coding Agents**

---

## 1. Product Vision & Value Proposition

**Enterprise-Product (EP-OS)** is the engineering operating system and mechanical gatekeeper for polyglot monorepos. It replaces conversational prompting and loose agent guidelines with deterministic, mechanical verification gates.

### Core Problems Solved
- **Architectural Erosion**: Prevents leaking ORMs, SQL schemas, and web frameworks into pure business domain logic.
- **Fictitious Testing**: Bans in-memory SQL emulators (e.g. SQLite for PostgreSQL) that hide production deadlocks and concurrency defects; mandates real ephemeral containers (Podman/Docker via Testcontainers).
- **Unbounded Blast Radius**: Restricts changes to declared per-branch change surfaces in `.ep/surfaces/<branch>.json`.
- **Agent Memory Loss & Context Bloat**: Provides persistent cross-session memory (`.ep/memory.json`) and single-turn context bundling (`ep pack`) to prevent conversational latency.
- **Unprotected Endpoints**: Enforces mandatory authorization guards across all API endpoints, strictly forbidding open, unauthenticated data exposure (such as unrestricted user listings).

---

## 2. Ubiquitous Language (Domain Dictionary)

| Term | Definition |
|---|---|
| **Bounded Context** | A formal boundary within which a domain model applies and all terms in the Ubiquitous Language have a single unambiguous meaning. |
| **Pure Domain** | The core business model (Entities, Value Objects, Domain Events). Has zero dependencies on databases, ORMs, transport layers, or UI frameworks. |
| **Hexagonal Architecture** | Ports & Adapters pattern where business logic interacts with external systems exclusively through abstract ports (interfaces), implemented by infrastructure adapters. |
| **Inbound Port** | An application-layer interface defining use-case operations callable by driving actors (HTTP controllers, gRPC handlers, CLI commands). |
| **Outbound Port** | An application-layer interface defining secondary dependencies required by use cases (repositories, event publishers, clock, identity providers). |
| **Primary Adapter** | Driving adapters (HTTP controllers, queue consumers) that translate external wire protocols into use-case invocations. |
| **Secondary Adapter** | Driven adapters (Postgres repository, Kafka producer, Redis cache) implementing outbound port interfaces. |
| **Ephemeral Container** | Real, disposable container instances (PostgreSQL, Redis, Kafka) spawned dynamically during integration tests via Podman or Testcontainers. |
| **Change Surface** | A declared blast-radius contract (`.ep/surfaces/<branch>.json`) listing the exact files and symbols permitted to be modified for a task. |
| **Expand/Contract** | A zero-downtime database migration pattern: expand schema additively, dual-write, backfill, read switch, and finally contract (drop deprecated elements). |
| **NC Item** | A formal `NEED_CLARIFICATION` record capturing missing domain specs or ambiguities. Unresolved items older than 14 days mechanically block merges. |
| **Product Memory** | Persistent operational context stored in `.ep/memory.json`, allowing agents to instantly understand product state on a fresh session or post-compaction. |

---

## 3. Subdomains & Architectural Layering

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Primary Adapters (Edge)                         │
│  - HTTP API Controllers  - gRPC Handlers  - Event/Queue Consumers     │
├────────────────────────────────────────────────────────────────────────┤
│                     Application Layer (Use Cases)                      │
│  - Command/Query Handlers  - Inbound Ports  - Outbound Port Interfaces │
├────────────────────────────────────────────────────────────────────────┤
│                       Pure Domain Layer (Core)                         │
│  - Aggregate Roots  - Entities  - Value Objects  - Pure Domain Events  │
├────────────────────────────────────────────────────────────────────────┤
│                       Secondary Adapters (Infra)                       │
│  - Database Repositories  - Message Brokers  - Real OCI Containers     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Inviolable Engineering Invariants (Tier 1)

1. **Deterministic Monorepo DAG**: Unified monorepo governed by `project.json` contracts (`lint`, `test`, `build`, `audit`).
2. **Pure Domain Isolation**: Zero persistence (ORM/SQL) or transport framework imports in pure domain files.
3. **Real Ephemeral Containers**: All datastore and broker integration tests must execute against real containers (Podman/Docker). In-memory SQL emulators (`:memory:` SQLite) are banned.
4. **UTC Storage Convention**: All database timestamps and wire payloads must be UTC ISO-8601 (`YYYY-MM-DDTHH:mm:ss.sssZ`).
5. **Anti-Sprawl Ceilings**: Maximum 800 lines per file (soft target $\le 400$), maximum 6 levels of directory depth, zero generic dumping grounds (`utils/`, `helpers/`, `common/`).
6. **Mandatory Endpoint Protection**: Every ingress API endpoint must declare explicit authorization guards. Unprotected data listings (e.g. unrestricted `/users`) trigger immediate blocking defects.
7. **Expand/Contract Database Migrations**: Destructive DDL (instant column drops, column renames) during rolling updates is strictly forbidden.
8. **Anti-MVP & Zero-Stub Mandate**: Stubs, temporary hacks, and phased hardening are forbidden. Every deliverable must be production-ready from turn one.
9. **Human-Only Production Merges**: AI agents can never merge into `prod`. Agents only prepare release candidate PRs with auto-merge permanently disabled.
10. **Dedicated Workspace Confinement**: All EP-OS generated state, memory, caches, and surfaces reside exclusively in `.ep/`.

---

## 5. Agent Operational Directives

- **On Session Wake / Post-Compaction**: Re-read [`SKILL.md`](SKILL.md) and [`AGENT.md`](AGENT.md) immediately, and inspect `.ep/memory.json` to restore product context.
- **Single-Turn Context Ingestion**: Never read files one-by-one. Use `python3 scripts/ep.py pack` to bundle target files in a single command.
- **Inner-Loop Verification**: Run `python3 scripts/ep.py quality --diff` and `python3 scripts/ep.py verify --diff` during active editing loops for sub-second verification.
- **Documentation Over File Creation**: Prioritize updating existing documentation files over creating new files. Rely on Git VCS for version history.
