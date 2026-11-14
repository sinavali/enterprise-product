# E2E Test Infrastructure Specification: Enterprise-Product (EP-OS)

## 1. Executive Overview & Methodology
This document defines the end-to-end (E2E) opaque-box test infrastructure for the `enterprise-product` (EP-OS) skill refactoring project.
All test cases are derived strictly and authoritatively from:
- `ORIGINAL_REQUEST.md` (R1: Skill Unification & Minimal Design; R2: File Footprint, Dedicated Directory & Docs; R3: Enterprise Pattern Enforcement; R4: Security & Performance Governance; R5: Domain Pruning, Change Surface & Graphing Resolution).
- `PROJECT.md` (18 Features: F1 to F18, Architectural Profiles A-D, Value-Driven Testing Matrix, 10-Dimension Audit Checklist, Dedicated `.ep/` Workspace).

### Core Testing Principles
1. **Opaque-Box Execution**: All tests exercise EP-OS externally via subprocess CLI invocations (`scripts/ep.py` or executable wrapper `scripts/bin/ep`), filesystem state inspections, environment configurations, and verifiable process exit codes.
2. **Deterministic Isolation**: Every test creates its own sandboxed temporary workspace (`tempfile.mkdtemp()`), initializes isolated git repositories where necessary, and tears down state cleanly on exit.
3. **No Facade Tests**: Assertions verify genuine business logic, structural integrity, and contract violations rather than static mocks.
4. **Adversarial & Boundary Verification**: Deliberately malformed inputs, missing sections, path escapes, deep directory hierarchies, non-UTF8 characters, and boundary limits are tested across all tiers.

---

## 2. Test Architecture & Directory Layout

```
tests/e2e/
├── conftest.py               # Reusable fixtures: CLI runner, temporary git repo manager, sample projects
├── test_tier1_features.py    # Tier 1: Core Feature Coverage (>=5 tests per feature, F1 through F18)
├── test_tier2_boundaries.py  # Tier 2: Boundary & Corner Cases (>=5 tests per feature, F1 through F18)
├── test_tier3_combinations.py# Tier 3: Pairwise Cross-Feature Interactions
└── test_tier4_scenarios.py   # Tier 4: Real-World Enterprise Workflows
```

---

## 3. Test Tier Breakdown & Scope

### Tier 1: Feature Coverage (F1 to F18)
Validates primary happy paths and core operational contracts for each of the 18 features defined in `PROJECT.md`:
- **F1 (Single Unified `SKILL.md`)**: Single canonical skill file existence, elimination of `references/` fragmentation, LOC $\le 400$, mandatory sections present.
- **F2 (Minimal & Actionable Content)**: Elimination of abstract tutorial essays, retention of concrete rules, patterns, syntax, and commands.
- **F3 (Compaction & Wake Re-Read Protocol)**: Top-level Session Restoration Mandate in `AGENT.md`, projection synchronization (`CLAUDE.md`, `.cursorrules`, `.windsurfrules`).
- **F4 (Consolidated Documentation Architecture)**: Dual-file documentation (`README.md` explanatory, `docs/ARCHITECTURE.md` technical), cross-linking integrity.
- **F5 (Elimination of File-Based Versioning)**: Absence of dated changelog files (`docs/changes/`), absence of `docs/releases/`, reliance on Git VCS.
- **F6 (Dedicated Directory Isolation `.ep/`)**: All caches, active surfaces, sessions, and release artifacts isolated in `.ep/`; absence of root clutter (`Packed.zip`, stray artifacts).
- **F7 (Template and Domain Pruning)**: Pruning of dead governance templates, unified project scaffolding.
- **F8 (Per-Branch Change Surface Resolution)**: Active surface scoped to `.ep/surfaces/<branch>.json` or `.ep/surfaces/active.json`, elimination of historical accumulation.
- **F9 (Graphing Excision & Boundary Decoupling)**: Absence/deprecation of brittle Mermaid topology generator; promotion of architectural boundary checks to `ep verify` / `ep quality`.
- **F10 (Domain-Driven Design Enforcement)**: Pure domain rules (`RULE-DDD-01` to `RULE-DDD-05`), zero ORM/web frameworks in `domain/`, immutable value objects.
- **F11 (Hexagonal Architecture Enforcement)**: Port/adapter separation (`RULE-HEX-01` to `RULE-HEX-04`), inward dependency flow, ephemeral real containers.
- **F12 (Test-Driven Development Enforcement)**: Prohibition of tautological assertions (`RULE-10.1`), zero skipped tests (`RULE-10.2`), non-happy-path failure suites.
- **F13 (Endpoint Protection Audit Checks)**: Mandatory authentication guards on route handlers (`RULE-SEC-01`).
- **F14 (Forbidden Unrestricted User Listings)**: Blocking unauthenticated/unpaginated user collection endpoints (`RULE-SEC-02`).
- **F15 (API Route Permission Checks)**: Mandatory authorization scopes/roles on mutating and sensitive routes (`RULE-SEC-03`).
- **F16 (Performance Review Checks)**: Static unbounded query detection (`RULE-1.1`), execution speed budget ($\le 1.0\text{s}$).
- **F17 (Single CLI Script Consolidation)**: Master executable `scripts/ep.py` handling all subcommands, backward-compatible module shims.
- **F18 (Comprehensive Test Suite & Final Pass)**: Full verification suite passing across all components, regression prevention.

### Tier 2: Boundary & Corner Cases (F1 to F18)
Exposes edge conditions, extreme parameters, malformed configurations, and error paths:
- Empty repositories, corrupted JSON/YAML configurations, missing directories.
- Highly nested package structures, maximum line length limits, non-ASCII Unicode paths.
- Extreme change surfaces (0 files, 10,000 files, non-existent branches, special characters in branch names).
- Malformed route definitions, partial decorators, commented-out auth guards, shadowed variable scopes.
- SQL queries with edge case whitespace, mixed-case SQL syntax, complex nested subqueries without LIMIT.
- CLI argument injection, missing required arguments, unknown flags, non-zero exit code determinism.

### Tier 3: Cross-Feature Combinations (Pairwise Interactions)
Validates interactions between disparate system features:
- Surface Validation + Boundary Checking (`F8` + `F9`).
- Init Subproject + DDD/Hexagonal Quality Gate (`F7` + `F10` + `F11`).
- Endpoint Protection + Permission Verification on Scaffolds (`F13` + `F15`).
- Fast-path verification under dirty Git state with Performance Budget (`F8` + `F16`).
- Manifest Re-Read Protocol + CLI Session Checkpointing (`F3` + `F6`).
- Single CLI Executable + Brownfield Onboarding + Audit Runner (`F17` + `F14` + `F16`).

### Tier 4: Real-World Enterprise Workflows
Validates complete multi-stage developer journeys:
- **Scenario 1: Brownfield Enterprise Monorepo Onboarding**: Initializing EP-OS, baseline generation, preflight checks, doctor diagnostics, and initial quality pass.
- **Scenario 2: Multi-Stack Full-Lifecycle Verification**: Scaffolding Profile A (Go), Profile B (Next.js), Profile C (Flutter), and Profile D (Contracts) and executing cross-stack validation.
- **Scenario 3: CI/CD Pull Request Promotion Gate**: Feature branch creation, per-branch surface declaration, diff verification, boundary checks, and security audit.
- **Scenario 4: Security Incident & Audit Remediation**: Injecting vulnerable routes (unprotected endpoints, unpaged user lists) and verifying automated gate blockage and subsequent remediation.
- **Scenario 5: Performance Degradation & Unbounded Query Block**: Injecting unbounded table scans and verifying gate failure with suggested remediation.

---

## 4. Execution Commands

```bash
# Execute entire E2E suite
pytest tests/e2e -v

# Execute specific tiers
pytest tests/e2e/test_tier1_features.py -v
pytest tests/e2e/test_tier2_boundaries.py -v
pytest tests/e2e/test_tier3_combinations.py -v
pytest tests/e2e/test_tier4_scenarios.py -v

# Execute with parallel workers (if pytest-xdist is installed)
pytest tests/e2e -n auto
```
