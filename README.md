# Enterprise-Product (EP-OS)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release: v1.0.0 LTS](https://img.shields.io/badge/Release-v1.0.0%20LTS-blue.svg)](docs/releases/RELEASE_v1.0.0_LTS.md)
[![Monorepo: Nx & DAG](https://img.shields.io/badge/Orchestrator-Nx%20%2F%20EP--Runner-143055.svg)](references/monorepo-nx-standard.md)
[![Architecture: DDD + Hexagonal](https://img.shields.io/badge/Architecture-DDD%20%2B%20Hexagonal-8A2BE2.svg)](references/architectural-profiles.md)
[![Tests: 180 Passing](https://img.shields.io/badge/Tests-180%20Passing-brightgreen.svg)](tests/)

**The production-grade engineering operating system and mechanical gatekeeper for polyglot monorepos.**

`enterprise-product` (EP-OS) ensures that AI coding agents (and human contributors) uphold architectural integrity, zero-compromise testing standards, and disciplined software engineering practices. It replaces loose agent prompting with deterministic, mechanical verification gates.

---

## Why EP-OS?

Modern AI coding agents generate code at unprecedented velocity, but without strict guardrails, they frequently degrade codebases:
- **Architectural Erosion**: Leaking ORMs, database schemas, and web frameworks directly into core domain logic.
- **Fictitious Testing**: Using in-memory emulators (like SQLite mocks for PostgreSQL) that hide production deadlocks and race conditions.
- **Sprawl & Monoliths**: Writing massive unmaintainable files ($> 1,000$ lines) or dumping code into chaotic `utils/` folders.
- **Unbounded Blast Radius**: Modifying arbitrary files without declaring or calculating the impact on downstream systems.

**EP-OS turns the tables**: It acts as an autonomous engineering operating system. Every change is mechanically bounded, audited across 10 architectural dimensions, tested against real disposable containers, and gated before merging.

---

## Quick Start: Using EP-OS with AI Agents

You can use EP-OS with **any AI agent platform** (Antigravity, Claude Code, Cursor, Windsurf, Gemini CLI, Codex, etc.).

### 1. Install into Your Agent
Simply give the GitHub repository URL to your AI agent and ask it to install:

> *"Install the `enterprise-product` skill from https://github.com/sinavali/enterprise-product and activate it."*

Or install it directly via terminal:
```bash
git clone https://github.com/sinavali/enterprise-product.git ~/.gemini/config/skills/enterprise-product
```

### 2. Autonomous First-Turn Ingestion
The moment the skill is loaded, the agent follows the ingestion protocol defined in [`AGENT.md`](AGENT.md):
1. **Preflight Verification**: Automatically runs `ep preflight` to verify shell execution, git, and workspace permissions.
2. **Proactive Activation Greeting**: The agent asks:
   > *"I have detected the `enterprise-product` engineering operating system. Would you like to activate enterprise governance for this product?"*
3. **Workspace & Stack Auto-Detection**:
   Upon confirmation, EP-OS inspects your workspace and automatically selects the required workflow:
   - **Empty Workspace**: Launches `scaffold` mode (`ep init`).
   - **Existing Codebase**: Launches `adopt` mode (`ep adopt --apply`) to baseline and onboard without breaking existing builds.
   - **Active Task / Bug**: Launches `plan` mode to scaffold a `CHANGE_SURFACE.md` or `investigate` mode to reproduce defects in containers.
   - **Resumed Session**: Automatically restores state checkpoints (`ep session resume`).

---

## Core Engineering Pillars

### 🛡️ 1. The 10-Dimension Enterprise Audit
Changes are automatically audited against 10 critical enterprise dimensions:
1. **Scalability & Capacity**: Query pagination, algorithmic complexity, connection pooling.
2. **Structural Modularity**: Hexagonal Ports & Adapters, zero framework leakage in pure domain.
3. **Fault Tolerance & Resilience**: Mandatory timeouts, retries with exponential backoff & jitter, circuit breakers.
4. **Data Integrity & Concurrency**: Optimistic locking, transactional outbox, strict UTC timestamps.
5. **Security & Zero-Trust**: Injection prevention, zero hardcoded credentials, secret scanning.
6. **Observability & Operability**: Structured JSON logging, trace propagation, `/healthz` probes.
7. **Contract & Schema Drift**: OpenAPI 3.1 / Protobuf v3 sync, SemVer contract breaking gates.
8. **Code Quality & Typing Strictness**: Strict null safety, no raw `any` types, zero swallowed exceptions.
9. **Documentation & NC Protocol**: Verified Change Surfaces, 0 unresolved questions older than 14 days.
10. **Test Fidelity & Assertion Quality**: Real ephemeral containers, zero tautological assertions, failure path coverage.

### 🏛️ 2. Clean Architecture & Anti-Sprawl
- **Hexagonal Domain Isolation**: Core business logic has zero dependencies on databases or UI frameworks.
- **Rule 2.6 Line Ceilings**: Hard limit of $\le 800$ lines per file (soft target $\le 400$ lines).
- **Directory Depth**: Maximum 6 levels of nesting from project root. Zero generic dumping grounds (`utils/`, `helpers/`).

### 🐳 3. Real Ephemeral Containers (Testcontainers / Podman)
Mock databases are strictly forbidden for integration testing. All database tests run against disposable, real container instances (PostgreSQL, Redis, Kafka) using Podman or Testcontainers, guaranteeing zero engine-substitution surprises.

### 🎯 4. Pre-Implementation Change Surface
Before editing production code, the agent generates and validates a `CHANGE_SURFACE.md`. The mechanical gate (`ep surface check-diff`) halts execution if any file outside the declared blast radius is touched.

### ⚡ 5. Standalone DAG Runner & `ast-grep` Code Intelligence
- **Zero-Dependency Task DAG Runner**: Kahn's topological dependency ordering (`ep run <project>:<target>`) executes multi-project build graphs with cycle detection.
- **AST Structural Linting**: Wraps `ast-grep` (`ep ast scan`) to structurally detect tautological assertions, unhandled empty catch blocks, and infinite retry loops across TypeScript, Go, Rust, and Python.

### 🔒 6. Production Human-in-the-Loop Gate
AI agents are **strictly forbidden from merging into `prod`**. Agents prepare production release candidate PRs (`ep pr create-prod`) with auto-merge permanently disabled. Only human engineers can sign off and merge into production.

---

## Unified Mechanical CLI (`ep`)

All developer and agent operations are consolidated under the zero-dependency `ep` CLI (`scripts/bin/ep` or `python3 scripts/ep.py`):

| Category | Command | Description |
|---|---|---|
| **Diagnostic & Healing** | `ep doctor [--heal]` | Audit operating system prerequisites & autonomously heal missing items |
| | `ep skill [generate]` | Compile lean, product-specific tailored skill manifest (`PRODUCT_SKILL.md`) |
| | `ep preflight` | Verify agent execution capabilities & access permissions |
| **Scaffolding & CI** | `ep init <name> --profile A\|B\|C\|D --lang <stack>` | Scaffold compliant DDD subproject |
| | `ep ci [init] [--platform github\|gitlab]` | Stamp standardized CI/CD pipeline workflows |
| **Change Surface** | `ep surface init` | Auto-detect modified projects and generate `CHANGE_SURFACE.md` |
| | `ep surface validate <file>` | Validate syntax, frontmatter, and completeness of Change Surface |
| | `ep surface check-diff` | Halt execution if changes exceed declared blast radius |
| | `ep surface archive [<file>]` | Archive active surface to `docs/changes/` and reset to clean template |
| **Task Execution** | `ep run <project>:<target>` | Execute target in topological DAG dependency order |
| | `ep run-many --target=<target> --parallel` | Run target across affected projects concurrently |
| **Context & Speed** | `ep pack [--surface] [--diff] [--files ...]` | Batch-pack codebase context into single bundle (anti-slowness) |
| **Code Intelligence** | `ep ast scan [--scope <dir>]` | Structural AST syntax scanning via `ast-grep` |
| | `ep graph --check-boundaries` | Lint Hexagonal domain and library boundaries |
| **Audit & Gatekeeper** | `ep audit [--diff origin/main] [--scope <dir>]` | Run 10-Dimension Enterprise Audit with scorecard |
| | `ep verify [--heal]` | Run full parallel mechanical gatekeeper verification suite |
| | `ep nc check [--max-age 14]` | Audit `NEED_CLARIFICATION` items for 14-day merge block |
| | `ep migration check [--diff]` | Zero-downtime Expand/Contract database migration linter |
| **Security & Ops** | `ep security scan [--staged] [--diff]` | Pre-commit secret & credential scanner (Shannon entropy) |
| | `ep iac [--dir <dir>]` | Containerfile & orchestration security vulnerability gate |
| | `ep license check [--sbom]` | Dependency copyleft compliance & SBOM generator |
| | `ep slo [--file <path>]` | Validate SLO schemas, thresholds, and error budgets |
| | `ep container [status\|detect]` | Smart OCI container engine detector & socket resolver |
| **Git & Governance** | `ep vcs sync-check` | Validate alignment between `main`, `test`, `stage`, and `prod` |
| | `ep vcs init-branches` | Initialize multi-tier promotion branches (`test`, `stage`, `prod`) |
| | `ep pr create-prod` | Create human-only production PR with auto-merge blocked |
| | `ep hooks install` | Install zero-dependency native git pre-commit hooks |
| | `ep codeowners` | Audit monorepo code ownership and coverage mapping |
| | `ep dora [--days 30]` | Calculate git-derived DORA metrics (Deploy Frequency, CFR) |
| **Sessions & State** | `ep session save` / `ep session resume` | Checkpoint and restore agent working memory |
| | `ep session check-collision` | Detect cross-agent worktree collisions & concurrent edits |
| **Adoption & Sync** | `ep adopt [--apply] [--profile <profile>]` | Scan and onboard brownfield monorepos |
| | `ep sync-skill [--check] [--direction]` | Synchronize skill directory with workspace repository |

---

## Universal Manifest Projection

EP-OS maintains a single source of truth in [`AGENT.md`](AGENT.md). Running:
```bash
python3 scripts/ep.py manifest sync
```
automatically projects instructions into `CLAUDE.md`, `.cursorrules`, and `.windsurfrules`, ensuring 100% behavioral parity regardless of the IDE or agent platform your team uses.

---

## Repository Structure

```text
enterprise-product/
├── AGENT.md               # Root operational manifest for LLMs & AI coding agents
├── CLAUDE.md              # Auto-projected manifest for Claude Code
├── .cursorrules           # Auto-projected manifest for Cursor
├── .windsurfrules         # Auto-projected manifest for Windsurf
├── PRODUCT_SKILL.md       # Lean tailored product skill manifest
├── README.md              # Human-facing architecture & usage guide (this file)
├── SKILL.md               # Antigravity & agent skill declaration
├── LICENSE                # MIT License
├── project.json           # Monorepo root lifecycle targets (lint, test, build, audit)
├── references/            # In-depth architectural & operational standards
│   ├── architectural-profiles.md  # Profiles A (DDD), B (Web), C (Mobile), D (Contracts)
│   ├── audit-taxonomy.md          # Complete 10-Dimension audit guide & checklists
│   ├── core-directives.md         # Inviolable Tier 1 invariants & autonomous self-healing
│   ├── deep-observability.md      # Distributed tracing, SLOs, DORA metrics & FinOps
│   ├── documentation-system.md    # Change Surface, ADRs, NC protocol & template catalog
│   ├── execution-engine.md        # Zero-latency execution & tool call batching
│   ├── monorepo-nx-standard.md    # Task DAG & project.json target contracts
│   ├── testing-matrix.md          # Value-driven testing rules & ephemeral containers
│   └── vcs-pr-protocol.md         # Multi-branch governance & 2-Pass PR self-audits
├── templates/             # Production templates (Change Surface, ADR, project.json, etc.)
├── scripts/               # Zero-dependency mechanical CLI tooling (Python 3.10+)
│   ├── bin/ep             # Unified executable entrypoint
│   ├── ep.py              # Core CLI router & subcommand dispatcher
│   ├── ep_adopt.py        # Brownfield onboarding & baseline ratchets
│   ├── ep_ast.py          # ast-grep structural code intelligence
│   ├── ep_context.py      # LLM context packing & token budget bundling
│   ├── ep_doctor.py       # Operating system diagnostic & autonomous self-healer
│   ├── ep_hooks.py        # Zero-dependency native git hook manager
│   ├── ep_ops.py          # POSIX atomic writes, container engines, SLOs, DORA, k6
│   ├── ep_runner.py       # Standalone topological task DAG runner
│   ├── ep_scaffold.py     # Subproject generator & universal manifest projection
│   ├── ep_security.py     # Shannon entropy secret scanner & IaC security gate
│   ├── ep_session.py      # Multi-session state machine & collision checker
│   ├── ep_stack.py        # Stack detection & language definitions
│   ├── ep_sync.py         # Skill-workspace bidirectional synchronization
│   ├── ep_vcs.py          # Multi-tier VCS platform adapters (GitHub, GitLab, Local)
│   └── audit-runner.py    # 10-Dimension audit engine with baseline ratchets
└── tests/                 # Comprehensive self-test suite (164 automated tests across 19 suites)
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.