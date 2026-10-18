---
name: enterprise-product
description: Supreme enterprise gatekeeper and engineering operating system for polyglot monorepos. Enforces production-grade rigor, DDD/Hexagonal architecture, Nx orchestration, 10-dimension audits, value-driven testing, Change Surfaces, and 2-Pass PR self-audits.
---

# Skill — `enterprise-product`

The **supreme enterprise gatekeeper and engineering operating system (EP-OS)** for polyglot monorepos. This skill enforces production-grade rigor, mechanical compliance, and zero-compromise engineering standards. It forbids AI agents from taking unverified shortcuts and mandates strict verification gates before any work is considered done.

---

## 1. Core Operating Principles

1. **Zero-Latency Execution Engine (Prime Directive P0)**:
   - **Compound Shell Commands**: Always combine related shell commands using `&&` or pipelines in a single `run_command` invocation. Never serialize sequential roundtrips.
   - **Parallel Inspection**: Emit multiple independent tool calls (e.g. parallel `view_file` or lookups) simultaneously in the same turn.
   - **Context Hygiene**: Redirect noisy build, test, and install outputs to `/tmp/*.log`. Bound file reads (`StartLine`/`EndLine`).
   - **Lossless Density**: Omit conversational filler, affirmative padding, and pleasantries. Maintain 100% technical fidelity, exact commands, and complete code blocks.
2. **Monorepo Standard**: Every product is strictly a single monorepo governed at the root by **Nx** (`nx affected`, target delegations, dependency graph validation).
3. **Hierarchical Governance (`AGENT.md`)**: Root enterprise inviolables cascade down to project-level `AGENT.md` manifests. Subprojects specialize configuration but can never violate Tier 1 directives.
4. **Four Architectural Profiles**:
   - **Profile A (Backend & Core Services)**: Domain-Driven Design (DDD) + Hexagonal Architecture (Ports & Adapters). Zero framework coupling in pure domain logic. Transactional outbox for event publishing.
   - **Profile B (Web Applications)**: Clean Component & State Layering, SSR/SPA hydration safety, WCAG 2.2 AA accessibility, tokenized design systems, and fluid Apple-grade motion.
   - **Profile C (Mobile Clients - Native & Flutter)**: Clean Architecture + Unidirectional State Flow, hardware-backed encrypted storage (Keychain/KeyStore/SQLCipher), offline-first sync.
   - **Profile D (Shared Contracts & Core Libraries)**: Contract-first (OpenAPI 3.1 / Protobuf v3), automated multi-language codegen (`generate-ts`, `generate-dart`, `generate-go`), automated breaking change gates.
5. **Value-Driven Testing Matrix**:
   - Domain logic: $\ge 95\%$ line & branch coverage.
   - Adapters & Infrastructure: $\ge 80\%$ line coverage with **real ephemeral containers (Testcontainers/Podman)**; engine-substitution emulators (e.g. SQLite for Postgres) are strictly prohibited.
   - Mandatory non-happy-path suites: Timeouts, circuit breakers, optimistic concurrency lock races, mutation score $\ge 85\%$.
6. **Mechanical Blast-Radius Bounding**: Every non-trivial change requires a declared and validated `Change Surface`. The mechanical gate (`ep surface check-diff`) actively halts execution if any file outside the declared surface is touched.
7. **Expand/Contract Database Migrations**: Destructive DDL (instant column drops, renames, non-null without default) is mechanically blocked by `ep migration check`.
8. **2-Pass PR Self-Audit & Automated Merge Protocol**:
   - Pass 1: Full diff audit against enterprise 10-dimension checklist ➔ Apply fixes ➔ Commit ➔ Push.
   - Pass 2: Cumulative diff re-audit + CI verification (`nx affected -t lint,test,build`). If 0 blocking defects and CI is green ➔ `gh pr merge --squash`. Escalates to human review on persistent defects.
9. **Complete Documentation & NC Protocol**:
   - Ambiguities are recorded as formal `NEED_CLARIFICATION` (NC) items. Open NC items older than 14 days mechanically block merges.
   - Architecture Decision Records (ADRs) for all architectural modifications.

---

## 2. Operational Modes

Agents operate under one of ten distinct operational modes. When invoked, determine or declare the active mode:

| Mode | Purpose | Modifies Files | Required Pre-condition |
|---|---|---|---|
| `plan` | Analyzes task, traces impact graph, generates & validates `Change Surface` artifact. | Yes (`CHANGE_SURFACE.md`) | Task request received. |
| `investigate` | Root cause analysis, reproduces bug in ephemeral container, writes red tests. | Yes (Failing Tests) | Defect or bug report. |
| `implement` | Executes TDD implementation according to Architectural Profile and testing matrix. | Yes (Code & Tests) | Validated `Change Surface` exists. |
| `audit` | Runs the 10-Dimension Enterprise Audit across affected projects or git diff. | Yes (`AUDIT_REPORT.md`) | Code implementation completed. |
| `verify` | Runs mechanical scripts: Nx targets, Change Surface validation, NC aging, manifests. | No | Staged or committed changes. |
| `pr-audit` | Executes 2-Pass PR Self-Audit protocol, verifies CI, merges or escalates. | Yes (Fix commits / PR) | PR created or ready to push. |
| `scaffold` | Generates 100% compliant projects and standard Nx target contracts. | Yes (New subproject) | New service/app requested. |
| `session` | Manages multi-session workspace checkpoints, state pause/resume, and retention. | Yes (`.ep/sessions/`) | Session start, pause, resume, or checkpoint. |
| `sync` | Validates multi-tier branch synchronization across main, test, stage, prod. | No | Pre-push, pre-merge, or promotion. |
| `release` | Orchestrates Hybrid Dual-Tier SemVer bumps, signed git tags, and release notes. | Yes (`docs/releases/`) | Production merge or milestone completion. |

---

## 3. Mode Execution Workflows

### Preflight Gate (Mandatory on First Turn)
Run `python3 scripts/ep.py preflight`.
- Verifies shell, git, python, and workspace write access.
- If missing permissions: prompts user with repeatable instructions.
- If access is refused: halts and refuses engagement on the Product.

### Mode: `plan`
1. Load `references/documentation-system.md` and `templates/CHANGE_SURFACE.template.md`.
2. Inspect the request to identify affected monorepo projects (`project.json`), domain entities, APIs, and infrastructure.
3. If any business requirement or contract ambiguity is identified, record a formal NC item using `templates/NEED_CLARIFICATION.template.md`. Do not invent unverified assumptions.
4. Draft the Change Surface artifact covering:
   - Problem statement and explicit business intent.
   - Affected Projects and Architectural Profile mappings.
   - Code Surface: Exact file paths and symbols targeted for modification.
   - Test Surface: Unit, integration (ephemeral containers), failure, and contract test suites.
   - Invariants and non-negotiables preserved.
   - Risk matrix and rollback strategy.
5. Run `python3 scripts/ep.py surface validate <path_to_change_surface>` to verify structural compliance.

### Mode: `investigate`
1. Reproduce reported failure within an isolated ephemeral container or unit test suite.
2. Author a failing (red) regression test asserting the expected behavior.
3. Verify the failure matches production diagnostics before modifying business code.

### Mode: `implement`
1. Read the approved `Change Surface` and the relevant project's `AGENT.md`.
2. Load `references/architectural-profiles.md` and `references/testing-matrix.md`.
3. Follow strict Test-Driven Development (TDD):
   - Step A: Author red tests in the designated Test Surface (domain invariants, failure edge cases).
   - Step B: Implement pure domain entities and use cases (Profile A/B/C/D rules apply).
   - Step C: Implement adapters and infrastructure using real containerized integrations (Podman/Testcontainers).
   - Step D: Ensure all timestamps are UTC, all external boundaries use typed contracts, and zero mock databases are used for integration tests.
4. Enforce blast radius: Run `python3 scripts/ep.py surface check-diff`. If uncommitted or staged files deviate from the declared surface, halt immediately.
5. Run project test suite via `nx test <project>` and linters via `nx lint <project>`.

### Mode: `session`
1. Save progress checkpoint: `python3 scripts/ep.py session save --session-id <id> --task <task> --mode <mode>`.
2. Resume on another platform or turn: `python3 scripts/ep.py session resume --session-id <id>`.

### Mode: `sync`
1. Verify branch topology alignment: `python3 scripts/ep.py vcs sync-check`.
2. Block progression if unmerged drift exists between `main`, `test`, `stage`, or `prod`.

### Mode: `audit`
1. Load `references/audit-taxonomy.md` and `templates/AUDIT_REPORT.template.md`.
2. Execute the 10-Dimension Enterprise Audit across the target diff or affected projects via `python3 scripts/ep.py audit --diff origin/main...HEAD`.
3. Classify all findings strictly: `blocking` (must resolve before PR), `suggestion`, or `nit`.

### Mode: `verify`
1. Run mechanical validation tooling: `python3 scripts/ep.py verify`.
2. Check database migrations: `python3 scripts/ep.py migration check`.
3. Halt if any mechanical check fails.

### Mode: `pr-audit`
1. Load `references/vcs-pr-protocol.md`.
2. Push feature branch `feat/<scope>-<desc>` or `fix/<scope>-<desc>` and open PR with `templates/PR_CONTRACT.template.md`.
3. **Pass 1 (Full Diff Self-Audit)**:
   - Run `python3 scripts/ep.py audit --diff origin/main...HEAD`.
   - Apply fixes, commit with Conventional Commit, and push.
4. **Pass 2 (Cumulative Diff Re-Audit & Verification)**:
   - Run `python3 scripts/ep.py verify`.
   - Run branch sync-check: `python3 scripts/ep.py vcs sync-check`.
   - Run full CI verification: `nx affected -t lint,test,build`.
   - If PR targets `main` and is clean ➔ `gh pr merge --squash --delete-branch`.
   - If PR targets `prod` ➔ run `python3 scripts/ep.py pr create-prod`. **DO NOT MERGE.** Production merges are strictly human-only.
   - If defects persist or branch is protected ➔ attach `needs/review` label and halt.

### Mode: `release`
1. Prepare release: `python3 scripts/ep.py release create <version>`.
2. Finalize production release: `python3 scripts/ep.py release finalize --prod`.

### Mode: `scaffold`
1. Generate standard subproject: `python3 scripts/ep.py init <name> --profile [A|B|C|D] --lang <language>`.
2. Sync manifest projections: `python3 scripts/ep.py manifest sync`.
3. Verify targets: `python3 scripts/ep.py verify`.

---

## 4. Reference Index & Progressive Disclosure

Do not load all reference files simultaneously. Read on demand based on current mode:

- `references/execution-engine.md` — Zero-latency tool batching, context hygiene, lossless communication.
- `references/multi-session-and-agent-agnosticism.md` — Multi-session workspaces, checkpointing, manifest projection, preflight access gate.
- `references/release-and-milestone-governance.md` — Hybrid Dual-Tier SemVer, milestones, human-only prod merge policy.
- `references/polyglot-stack-matrix.md` — 100% stack agnosticism (12+ languages), build manifests, orchestrator adapters.
- `references/core-directives.md` — Prime Directives P0–P10, Tier 1/2/3 Master Rulebook, UTC conventions.
- `references/static-analysis-matrix.md` — Polyglot strict typing (TypeScript, Go, Rust, Flutter, PHP).
- `references/architectural-profiles.md` — Profiles A (DDD/Hexagonal), B (Web/A11y/Motion), C (Flutter/BLoC), D (Contracts/Codegen).
- `references/monorepo-nx-standard.md` — Root Nx orchestration, project.json contracts, target delegation.
- `references/agent-hierarchy-spec.md` — AGENT.md schema, cascading inheritance, overrides vs invariants.
- `references/audit-taxonomy.md` — 10-Dimension Audit Guide, verification steps, scoring.
- `references/testing-matrix.md` — Value-driven testing rules, Testcontainers, failure testing, coverage gates.
- `references/vcs-pr-protocol.md` — Monorepo git worktrees, Conventional Commits, 4-tier branches, 2-Pass PR Self-Audit.
- `references/documentation-system.md` — Change Surface lifecycle, ADRs, topology graphing (`ep graph`).
- `references/nc-protocol.md` — NEED_CLARIFICATION schema, lifecycle, 14-day escalation mechanics.
- `references/deep-observability.md` — Golden Signals, RED/USE methods, W3C Trace Context propagation, Metric Cardinality Bounding, RUM & Synthetics.
- `references/compliance-matrix.md` — SOC 2, ISO 27001, GDPR, data classification tiers, and immutable mutation audit logging.
- `references/optional-tooling.md` — Integration standards & fallback contracts for k6, OTel Collector, Infracost, OPA/Conftest, Chaos Mesh.
- `references/exclusions.md` — Principled architectural exclusions (Vendor Viability, Continuous Profiling daemon, eBPF).

---

## 5. Unified Mechanical CLI Tooling (`ep`)

All mechanical gates and orchestrations are accessible through the single executable entrypoint `scripts/bin/ep` (or `python3 scripts/ep.py`):

```bash
# Scaffolding, Worktrees & Manifests
ep init <name> --profile [A|B|C|D] --lang [go|rust|ts|dart|php]
ep worktree create <branch-name>
ep worktree remove <branch-name>
ep manifest sync [--root <dir>]
ep preflight

# Change Surface & Blast Radius
ep surface init [--output CHANGE_SURFACE.md]
ep surface validate <path>
ep surface check-diff [--base origin/main]

# Task DAG Execution (Standalone Zero-Dependency Runner)
ep run <project>:<target>
ep run-many --target=<target> [--projects=p1,p2] [--parallel] [--affected]

# Structural Code Intelligence & Boundary Linters
ep ast scan [--scope <dir>]
ep graph [--format mermaid|json] [--check-boundaries]

# Audits, Invariants & Migrations
ep audit [--diff origin/main...HEAD | --scope <path>]
ep migration check [--dir <migrations-dir>]
ep verify [--root <monorepo-root>]
ep nc check [--max-age 14]

# Git, VCS & Multi-Branch Governance
ep vcs sync-check
ep pr create-prod [--title <title>] [--body <body>]
ep release create <version>
ep release finalize --prod
ep milestone status

# Operational Engineering, Containers, SLOs, DORA & Performance
ep container [status|detect|info] [--json]
ep slo [--file <path>]
ep codeowners [--root <dir>]
ep dora [--days <count>]
ep iac [--dir <path>]
ep perf [--script <path>] [--target-url <url>] [--dry-run]

# Sessions, State Machines & Concurrency
ep session save --session-id <id> --task <task> --mode <mode>
ep session resume --session-id <id>
ep session check-collision --session <id>
ep session list
ep session prune --session-id <id>

# Security, Licenses, Hooks, Brownfield Adoption & Sync
ep security scan [--diff origin/main...HEAD]
ep license check [--package-json <path>]
ep hooks install
ep hooks run pre-commit
ep adopt [--scope <dir>] [--apply]
ep sync-skill [--check] [--direction to-workspace|to-skill]
```