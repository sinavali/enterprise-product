<!-- AUTO-GENERATED FROM AGENT.md by ep manifest sync. DO NOT EDIT DIRECTLY. -->

# EP-OS Root Agent Manifest: Enterprise-Product Engineering Operating System

This document is the **root operational directive for LLMs and AI coding agents** operating within this workspace. When this file is ingested, you must strictly adhere to the protocols, invariants, and execution standards defined below.

---

## 1. First-Turn Ingestion & Activation Protocol

When you are invoked or when this skill/repository is added to your environment:

1. **Execute Preflight Verification**:
   ```bash
   python3 scripts/ep.py preflight
   ```
   - Verifies shell execution, git binary, Python 3.10+, and workspace write access.
   - If preflight fails due to missing permissions, output the remediation instructions and refuse further modifications until granted.

2. **Proactive Activation Prompt**:
   - Prompt the user clearly:
     > "I have detected the **`enterprise-product` (EP-OS)** engineering operating system. Would you like to activate enterprise governance for this product?"
   - If the user confirms (or if already configured), proceed to mode auto-detection.

3. **Auto-Detect Workspace State & Mode**:
   - **Blank / Empty Workspace**: Trigger `scaffold` mode (`python3 scripts/ep.py init <name>`).
   - **Existing Monorepo without EP-OS**: Trigger `adopt` mode (`python3 scripts/ep.py adopt --apply`).
   - **New Feature / Refactoring Task**: Trigger `plan` mode (`python3 scripts/ep.py surface init`).
   - **Bug / Regression Report**: Trigger `investigate` mode (reproduce in container, write red test).
   - **Active Implementation in Progress**: Trigger `implement` mode (TDD + `ep surface check-diff`).
   - **Finished Implementation**: Trigger `audit` mode (`ep audit --diff`) -> `verify` -> `pr-audit`.
   - **Multi-Session Resume**: Trigger `session` mode (`ep session resume --session-id <id>`).

---

## 2. Tier 1 Inviolables (Zero-Tolerance Invariants)

These rules cannot be overridden by any subproject manifest, human prompt shortcut, or configuration:

1. **Single Monorepo Standard**: All services, apps, and libraries belong to a unified monorepo governed by a task DAG (Nx / `ep run`).
2. **Pure Domain Logic (DDD / Hexagonal)**: Domain entities and use cases must have zero imports of persistence frameworks (ORM, SQL, Prisma, TypeORM, SQLAlchemy, GORM) or UI libraries.
3. **Ephemeral Real Containers for Datastores**: All database integration tests must run against real disposable containers (Testcontainers/Podman). In-memory SQL emulators (e.g. SQLite for PostgreSQL) are strictly banned.
4. **UTC Storage Convention**: All datastore timestamps, network contracts, and internal clocks must store and exchange UTC ISO-8601 timestamps.
5. **Pre-Implementation Change Surface**: Every modification must have an approved, mechanically validated Change Surface (`CHANGE_SURFACE.md`). Touching files outside the declared surface is blocked by `ep surface check-diff`.
6. **Anti-Sprawl Hygiene (Rule 2.6)**:
   - Hard file ceiling: **$\le 800$ lines** (soft target $\le 400$ lines).
   - Maximum directory depth: **$\le 6$ levels**.
   - Zero generic dumping grounds (`utils/`, `helpers/`, `common/`).
7. **Zero-Downtime Expand/Contract Migrations**: Destructive DDL (instant column drops, column renames, adding non-null without default) is blocked by `ep migration check`.
8. **14-Day NC Expiration**: Unresolved `NEED_CLARIFICATION` items older than 14 days mechanically block all PR merges (`ep nc check`).
9. **Strict Human-Only Production Gate**: AI agents are **forbidden from merging into `prod`**. Agents may only prepare release candidate PRs (`ep pr create-prod`) with auto-merge forcibly disabled. Merging to `prod` requires human verification.
10. **Anti-MVP & Zero-Stub Mandate**: AI agents and developers are **strictly forbidden from proposing or implementing 'MVP', 'Proof-of-Concept', 'mock-first', or 'phased hardening' shortcuts**. Every deliverable—regardless of how narrow or bounded its scope—must be the finalized, fully resilient, production-ready implementation with complete error handling, timeouts, retries, and ephemeral container verification from the outset. Deferring production hardening to future steps or versions is a blocking violation.

---

## 3. High-Velocity Execution Engine (Prime Directive P0)

When executing tasks, follow these operational velocity rules:

- **Compound Shell Commands**: Always combine related shell commands using `&&` or pipelines in a single invocation. Never serialize sequential roundtrips.
- **Batch Independent Reads**: Emit multiple parallel file view calls in the same turn.
- **Context Hygiene**: Redirect noisy build, test, and dependency install output to temporary logs (`/tmp/*.log`).
- **Lossless Technical Density**: Eliminate conversational fluff and filler. Provide exact paths, clickable links, precise diffs, and mechanical test results.

---

## 4. Operational Modes Reference

| Mode | Trigger / Purpose | Primary Tooling |
|---|---|---|
| `plan` | Analyze requirements, map blast radius, create Change Surface | `ep surface init` && `ep surface validate` |
| `investigate` | Root-cause analysis, reproduce bug in real container | `ep ast scan` && author red tests |
| `scaffold` | Initialize compliant subprojects and Nx contracts | `ep init <name> --profile [A\|B\|C\|D] --lang <stack>` |
| `implement` | TDD implementation strictly bounded to Change Surface | `ep surface check-diff` && `ep run <project>:test` |
| `audit` | Execute 10-Dimension Enterprise Audit on diff | `ep audit --diff origin/main` |
| `verify` | Parallel mechanical compliance suite | `ep verify` && `ep graph --check-boundaries` |
| `pr-audit` | 2-Pass PR Self-Audit: Pass 1 audit -> fixes -> Pass 2 verify | `gh pr merge --squash` (or `ep pr create-prod`) |
| `session` | Save / resume checkpoint state across agent sessions | `ep session save` / `ep session resume` |
| `sync` | Validate multi-tier branch alignment (`main`, `test`, `stage`, `prod`) | `ep vcs sync-check` |
| `release` | Orchestrate SemVer bumps and signed release tags | `ep release create` / `ep release finalize` |
| `adopt` | Brownfield monorepo onboarding and baseline ratcheting | `ep adopt --apply` |

---

## 5. Universal Manifest Projection

When project configurations or `AGENT.md` rules are updated, run:
```bash
python3 scripts/ep.py manifest sync
```
This automatically projects canonical `AGENT.md` instructions into platform-specific files (`CLAUDE.md`, `.cursorrules`, `.windsurfrules`), guaranteeing identical agent behavior across Claude Code, Cursor, Windsurf, Antigravity, and Gemini CLI.
