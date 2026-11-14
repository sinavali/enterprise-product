# Enterprise-Product (EP-OS)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Architecture: DDD + Hexagonal](https://img.shields.io/badge/Architecture-DDD%20%2B%20Hexagonal-8A2BE2.svg)](docs/ARCHITECTURE.md)
[![Versioning: Git VCS](https://img.shields.io/badge/Versioning-Git%20VCS-orange.svg)](docs/ARCHITECTURE.md#vcs-governance)
[![Tests: 225 Passing](https://img.shields.io/badge/Tests-225%20Passing-brightgreen.svg)](tests/)

**The production-grade engineering operating system and mechanical gatekeeper for polyglot monorepos.**

`enterprise-product` (EP-OS) ensures that AI coding agents and human engineers uphold architectural integrity, zero-compromise testing standards, and disciplined software engineering practices. It replaces loose conversational prompting with deterministic, mechanical verification gates.

For comprehensive technical and architectural specifications, see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**. For the unified agent skill declaration, see **[SKILL.md](SKILL.md)**.

---

## Why EP-OS?

Modern AI coding agents generate code at unprecedented velocity, but without strict mechanical guardrails, they frequently degrade production codebases:
- **Architectural Erosion**: Leaking ORMs, database schemas, and web transport layers directly into pure domain logic.
- **Fictitious Testing**: Using in-memory emulators (like SQLite mocks for PostgreSQL) that hide production deadlocks, dialect mismatches, and race conditions.
- **Sprawl & Monoliths**: Writing massive unmaintainable files ($> 800$ lines) or dumping code into chaotic `utils/` and `helpers/` folders.
- **Unbounded Blast Radius**: Modifying arbitrary files across the monorepo without declaring or calculating the impact on downstream systems.
- **Context Drift & Amnesia**: Forgetting core engineering rules after context window memory compaction (`/compact`).

**EP-OS turns the tables**: It acts as an autonomous engineering operating system. Every change is mechanically bounded, audited across 10 architectural dimensions, tested against real disposable containers, and gated before merging.

---

## Quick Start: Using EP-OS with AI Agents

EP-OS is engineered for 100% parity across **all major AI agent platforms** (Antigravity, Claude Code, Cursor, Windsurf, Gemini CLI, Codex).

### 1. Install or Activate the Skill
Clone into your agent skill configuration or point your agent to this repository:
```bash
git clone https://github.com/sinavali/enterprise-product.git ~/.gemini/config/skills/enterprise-product
```

### 2. Autonomous First-Turn Ingestion & Wake Mandate
The moment an agent awakens in this workspace, it executes the protocol defined in [`AGENT.md`](AGENT.md):
1. **Skill Re-Read**: The agent re-reads [`SKILL.md`](SKILL.md) to ensure all operational rules and architectural profiles are anchored in context.
2. **Preflight Verification**: Automatically runs `python3 scripts/ep.py preflight` to verify shell execution, git binary, Python 3.10+, and workspace write access.
3. **Workspace State Auto-Detection**:
   - **Blank Workspace**: Launches `scaffold` mode (`ep init`).
   - **Existing Monorepo**: Launches `adopt` mode (`ep adopt --apply`) to baseline and onboard without breaking existing builds.
   - **Active Task / Feature**: Launches `plan` mode to declare a bounded `Change Surface`.
   - **Bug / Defect**: Launches `investigate` mode to reproduce defects in real containers.
   - **Resumed Session**: Restores state checkpoints (`ep session resume`).

---

## Core Engineering Pillars

### 🛡️ 1. The 10-Dimension Enterprise Audit
Every proposed change is audited against 10 critical enterprise dimensions (`ep audit`):
1. **Scalability & Capacity**: Bounded algorithmic complexity, query pagination, connection pooling, stateless services.
2. **Structural Modularity**: Ports & Adapters layer isolation, file line count $\le 800$, directory depth $\le 6$, zero dumping grounds.
3. **Fault Tolerance & Resilience**: Explicit client timeouts, exponential backoff with jitter, circuit breakers, DLQs, graceful shutdown.
4. **Data Integrity & Concurrency**: Optimistic locking, atomic transactions, idempotent consumers, strict UTC ISO-8601 storage, transactional outbox.
5. **Security & Zero-Trust**: Mandatory endpoint authentication (`RULE-SEC-01`), forbidden open `/users` listings (`RULE-SEC-02`), API permission scopes (`RULE-SEC-03`), Shannon entropy secret scanning.
6. **Observability & Operability**: Structured JSON logging, W3C trace context propagation, `/healthz` & `/readyz` probes, bounded metric cardinality.
7. **Contract & Schema Drift**: OpenAPI 3.1 / Protobuf v3 sync, zero cross-project import bypassing, breaking change detection.
8. **Code Quality & Typing**: Strict null safety, zero untyped `any`, custom typed errors (no swallowed catches), immutable value objects.
9. **Documentation & Spec Drift**: Bounded Change Surface match, mandatory ADRs for deviations, 0 open NC items $> 14$ days.
10. **Test Fidelity & Quality**: Real ephemeral containers, zero tautological assertions, failure path testing, $\ge 85\%$ mutation score.

### 🏛️ 2. Clean Architecture & Four Architectural Profiles
Every monorepo package declares one of four architectural profiles:
- **Profile A (Backend & Core Services)**: Pure Domain-Driven Design (DDD) + Hexagonal Architecture. Pure domain entities and use-cases have zero imports of persistence frameworks or web frameworks.
- **Profile B (Web Applications)**: SSR hydration safety, WCAG 2.2 AA accessibility (Axe-core tests), tokenized design system, fluid spring motion.
- **Profile C (Mobile Clients - Native & Flutter)**: Clean mobile architecture, unidirectional state flow, hardware-backed encrypted storage (Keychain/KeyStore/SQLCipher), offline-first sync.
- **Profile D (Shared Contracts & Core Libraries)**: Contract-first schemas, automated multi-language codegen (`generate-ts`, `generate-dart`, `generate-go`), mechanical breaking change gates.

### 🐳 3. Real Ephemeral Containers (Podman / Testcontainers)
Mock datastores are strictly forbidden for integration testing. All database and messaging tests run against disposable, real container instances (PostgreSQL, Redis, Kafka) using Podman or Testcontainers, guaranteeing zero engine-substitution surprises.

### 🎯 4. Pre-Implementation Change Surface
Before editing production code, the agent generates and validates a Change Surface. The mechanical gate (`ep surface check-diff`) halts execution if any file outside the declared blast radius is touched.

### 🔒 5. Human-Only Production Gate
AI agents are **strictly forbidden from merging into `prod`**. Agents prepare production release candidate PRs (`ep pr create-prod`) with auto-merge permanently disabled. Only human engineers can sign off and merge into production.

---

## Unified Mechanical CLI (`ep`)

All developer and agent operations are consolidated under the zero-dependency `ep` CLI (`scripts/bin/ep` or `python3 scripts/ep.py`):

| Category | Command | Description |
|---|---|---|
| **System & Health** | `ep doctor [--heal]` | Audit operating system prerequisites & autonomously heal missing items |
| | `ep preflight` | Verify agent execution capabilities & access permissions |
| | `ep manifest sync` | Synchronize canonical `AGENT.md` to `CLAUDE.md`, `.cursorrules`, `.windsurfrules` |
| **Change Surface** | `ep surface init` | Auto-detect modified projects and scaffold Change Surface |
| | `ep surface validate <file>` | Validate syntax, frontmatter, and completeness of Change Surface |
| | `ep surface check-diff` | Halt execution if changes exceed declared blast radius |
| **Context & Speed** | `ep pack [--surface] [--diff]` | Batch-pack codebase context into single turn (anti-slowness bundle) |
| **Task Execution** | `ep run <project>:<target>` | Execute target in topological DAG dependency order |
| | `ep run-many --target=<target> --parallel` | Run target across affected projects concurrently |
| **Code Intelligence** | `ep ast scan [--scope <dir>]` | Structural AST syntax scanning via `ast-grep` |
| | `ep verify --check-boundaries` | Lint Hexagonal domain and library boundaries |
| **Audit & Gates** | `ep audit [--diff origin/main]` | Run 10-Dimension Enterprise Audit with scorecard |
| | `ep verify [--diff <base>] [--surface]` | Run full unified mechanical gatekeeper suite |
| | `ep quality [--diff <base>] [--surface]` | Enforce idempotency, graceful drain, ephemeral DBs & domain purity |
| | `ep nc check [--max-age 14]` | Audit `NEED_CLARIFICATION` items for 14-day merge block |
| | `ep migration check [--dir <dir>]` | Zero-downtime Expand/Contract database migration linter |
| **Security & Tooling** | `ep security scan [--diff <base>]` | Pre-commit secret & credential scanner (Shannon entropy) |
| | `ep contract verify [--file <path>]` | OpenAPI and Protobuf schema contract validation |
| | `ep license check [--package-json <path>]` | Dependency copyleft compliance scanner |
| | `ep container [status\|detect]` | Smart OCI container engine detector & socket resolver |
| | `ep slo [--file <path>]` | Validate SLO schemas, thresholds, and error budgets |
| **Git & Governance** | `ep vcs sync-check` | Validate alignment between `main`, `test`, `stage`, and `prod` |
| | `ep vcs init-branches` | Initialize multi-tier promotion branches (`test`, `stage`, `prod`) |
| | `ep pr create-prod` | Create human-only production PR with auto-merge blocked |
| | `ep release create <version>` | Prepare release tag and notes via Git VCS |
| | `ep release finalize --prod` | Finalize production release in Git VCS |
| **Sessions & State** | `ep session save` / `ep session resume` | Checkpoint and restore agent working memory |
| | `ep adopt [--apply] --profile [A\|B\|C\|D]` | Scan and onboard brownfield monorepos |
| | `ep sync-skill [--check] [--direction]` | Synchronize skill directory with workspace repository |

---

## Universal Manifest Projection

EP-OS maintains a single canonical source of truth in [`AGENT.md`](AGENT.md). Running:
```bash
python3 scripts/ep.py manifest sync
```
automatically projects instructions into `CLAUDE.md`, `.cursorrules`, and `.windsurfrules`, ensuring 100% behavioral parity regardless of the IDE or agent platform your team uses.

---

## Repository Structure

```text
enterprise-product/
├── .ep/                   # Dedicated EP-OS workspace (ALL generated caches, surfaces, sessions)
│   ├── cache/            # AST and dependency caches
│   ├── surfaces/         # Ephemeral per-branch change surfaces
│   └── sessions/         # Workspace session snapshots
├── docs/
│   └── ARCHITECTURE.md   # Consolidated technical & architectural documentation
├── scripts/
│   ├── ep.py             # Unified zero-dependency executable CLI router
│   └── bin/
│       └── ep            # Executable bash launcher wrapper
├── tests/                # Comprehensive test suites (225+ passing tests)
├── templates/            # Standardized enterprise templates (Change Surface, ADR, PR Contract)
├── AGENT.md              # Root operational manifest for LLMs & AI coding agents
├── CLAUDE.md             # Auto-projected manifest for Claude Code
├── .cursorrules          # Auto-projected manifest for Cursor
├── .windsurfrules        # Auto-projected manifest for Windsurf
├── project.json          # Monorepo root lifecycle targets (lint, test, build, audit)
├── README.md             # Explanatory documentation for humans & agents (this file)
├── SKILL.md              # Unified, minimal, actionable enterprise-product skill
└── LICENSE               # MIT License
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.