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
3. **Ephemeral Real Containers for Datastores**: All database integration tests must run against real disposable containers (resolved intelligently via `ep container detect`, preferring rootless Podman with Docker fallback). In-memory SQL emulators (e.g. SQLite for PostgreSQL) are strictly banned.
4. **UTC Storage Convention**: All datastore timestamps, network contracts, and internal clocks must store and exchange UTC ISO-8601 timestamps.
5. **Pre-Implementation Change Surface**: Every modification must have an approved, mechanically validated Change Surface (`CHANGE_SURFACE.md`). Touching files outside the declared surface is blocked by `ep surface check-diff`. Upon task completion, active surfaces are mechanically archived to `docs/changes/YYYY-MM-DD-<slug>.md` via `ep surface archive` and the root file is reset to template.
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

- **Zero-Serialization File Ingestion Mandate (Anti-One-by-One Slowness)**: AI agents are **strictly forbidden from reading codebase files sequentially one-by-one across multiple conversational turns**. When planning, investigating, or modifying code, agents MUST run `ep pack` (e.g. `python3 scripts/ep.py pack --surface` or compound `tail -n +1 <files...>`) in a single bash command to inject all target files into context in a single turn before editing.
- **Fast-Path Sub-Second Verification (`--diff` / `--surface`)**: During inner development loops, agents MUST use fast-path flags (e.g. `python3 scripts/ep.py verify --diff` or `python3 scripts/ep.py quality --diff`) to verify only touched files rather than re-running full monorepo re-audits.
- **Persistent Analysis Caching**: Static analysis and AST grep scans automatically cache clean file hashes in `.ep/cache/ast_cache.json`. Repeated scans on unchanged files execute in milliseconds.
- **Compound Shell Commands**: Always combine related shell commands using `&&` or pipelines in a single invocation. Never serialize sequential roundtrips.
- **Batch Independent Reads**: If reading non-repo files, emit multiple parallel tool calls in the same turn.
- **Context Hygiene**: Redirect noisy build, test, and dependency install output to temporary logs (`/tmp/*.log`). Use `/compact` when conversation history grows long.
- **Lossless Technical Density**: Eliminate conversational fluff and filler. Provide exact paths, clickable links, precise diffs, and mechanical test results.

---

## 4. Operational Modes Reference

| Mode | Trigger / Purpose | Primary Tooling |
|---|---|---|
| `plan` | Analyze requirements, map blast radius, create Change Surface | `ep surface init` && `ep surface validate` |
| `investigate` | Root-cause analysis, reproduce bug in real container | `ep ast scan --diff` && author red tests |
| `scaffold` | Initialize compliant subprojects and Nx contracts | `ep init <name> --profile [A\|B\|C\|D] --lang <stack>` |
| `implement` | TDD implementation bounded to Change Surface (pack context in 1 turn) | `ep pack --surface --summary` && `ep quality --diff` && `ep run <project>:test` |
| `audit` | Execute 10-Dimension Enterprise Audit on diff | `ep audit --diff origin/main` |
| `verify` | 12-Step unified mechanical compliance suite (Fast-path: `--diff`) | `ep verify [--diff]` (Gates: Nx, AGENT, NC, Migration, Secrets, Surface, Boundaries, License, IaC, SLO, Quality, Audit) |
| `pr-audit` | 2-Pass PR Self-Audit: Pass 1 audit -> fixes -> Pass 2 verify -> archive surface | `ep surface archive` && `gh pr merge --squash` (or `ep pr create-prod`) |
| `session` | Save / resume checkpoint state across agent sessions | `ep session save` / `ep session resume` |
| `sync` | Validate multi-tier branch alignment (`main`, `test`, `stage`, `prod`) | `ep vcs sync-check` |
| `release` | Orchestrate SemVer bumps and signed release tags | `ep release create` / `ep release finalize` |
| `adopt` | Brownfield monorepo onboarding and baseline ratcheting | `ep adopt --apply` |
| `ops` | Operational readiness, container resolver, SLO validation, code ownership, DORA & perf | `ep container`, `ep slo`, `ep codeowners`, `ep dora`, `ep iac`, `ep perf --tool [k6\|locust]` |
| `tooling` | Chaos drills, API contract testing, and SBOM supply-chain validation | `ep chaos [scaffold\|verify]`, `ep contract verify`, `ep sbom [generate\|verify]` |
| `doctor` | Operating system prerequisite diagnostic & autonomous self-healing | `ep doctor [--heal]` |
| `skill` | Generate compact product-specific tailored skill manifest | `ep skill generate` |

---

## 5. Universal Manifest Projection

When project configurations or `AGENT.md` rules are updated, run:
```bash
python3 scripts/ep.py manifest sync
```
This automatically projects canonical `AGENT.md` instructions into platform-specific files (`CLAUDE.md`, `.cursorrules`, `.windsurfrules`), guaranteeing identical agent behavior across Claude Code, Cursor, Windsurf, Antigravity, and Gemini CLI.
