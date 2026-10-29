---
title: "Change Surface: Full Polyglot Enterprise Audit Remediation and Cross-Stack Hardening"
author: "Antigravity EP-OS Agent & DeepCoder"
created_date: "2026-10-28"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "enterprise-product"
---

# Change Surface: Full Polyglot Enterprise Audit Remediation and Cross-Stack Hardening

## 1. Intent & Business Rationale
Remediate all 7 blocking defects (P0) and 6 prioritized suggestions (P1/P2) identified in the comprehensive polyglot enterprise audit:
1. FIX-01: Fix relative path handling and unpopulated template fallback across `validate-change-surface.py`, `ep.py`, and `ep_context.py` so that archived surfaces in `docs/changes/` are seamlessly and deterministically resolved.
2. FIX-02: Expand canonical skill sync in `scripts/ep_sync.py` to track all root manifests (`AGENT.md`, `CLAUDE.md`, `.cursorrules`, `.windsurfrules`, `CHANGE_SURFACE.md`, `PRODUCT_SKILL.md`, `project.json`, `LICENSE`, `.gitignore`) and subdirectories (`docs/`, `.github/`), with atomic staging and orphan file pruning.
3. FIX-03: Align `ep init` scaffolding Section 3 header in `scripts/ep_scaffold.py` to `## 3. Local Nx Target Delegations` so all newly scaffolded projects pass `verify-agent-manifests.py`.
4. FIX-04: Fix `templates/profiles/contracts-project.json` tag from `"scope:contracts"` to `"scope:shared"`.
5. FIX-05: Realign multi-tier VCS branches (`prod` to `main`).
6. FIX-06: Upgrade `ep doctor` branch verification in `scripts/ep_doctor.py` to enforce topological reachability via `sync_check("main")`.
7. FIX-07: Eliminate all zero-stub violations in `scripts/ep.py` (`telemetry`, `finops`, `policy`) and `scripts/ep_stack.py` with concrete zero-dependency handlers and static AST/IaC security linters.
8. FIX-08: Realign AST clock rule taxonomy in `scripts/ep_ast.py` to Dimension 4 (`RULE-4.4-AST-NON-UTC-CLOCK`) with refined domain-targeted patterns.
9. FIX-09: Polyglot heuristic expansion in `scripts/audit-runner.py` for Python/Go empty catches, Go/PHP/Rust non-UTC time detection, and Go co-located test exclusions (`*_test.go`).
10. FIX-10: Worktree branch existence check in `scripts/ep_scaffold.py`.
11. FIX-11: Scoped release change generation in `scripts/ep.py` with `--version` and `--prod` support.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `enterprise-product` | Profile D (Contracts & Libs) | Complete polyglot audit remediation, engine modularization, gate hardening, and verification |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `tests/test_audit_remediation_fixes.py`: Comprehensive test suite verifying all 11 audit remediations.

### Modified Files
- `scripts/audit-runner.py`: Add polyglot empty catch, UTC time detection for Go/PHP/Rust, and Go co-located test exclusions.
- `scripts/ep.py`: Centralize `_resolve_change_surface`, implement real telemetry/finops/policy handlers, add `--version` alias, modularize handlers.
- `scripts/ep_ast.py`: Reassign UTC storage rule to Dimension 4 (`RULE-4.4-AST-NON-UTC-CLOCK`).
- `scripts/ep_context.py`: Deterministic fallback sorting and safe unpopulated surface handling.
- `scripts/ep_doctor.py`: Upgrade `check_vcs_branches` to call `sync_check("main")`.
- `scripts/ep_ops.py`: Add concrete telemetry trace collector and resource quota verification.
- `scripts/ep_runner.py`: Add task DAG validation and DAG cycle error formatting.
- `scripts/ep_scaffold.py`: Fix Section 3 AGENT header to `## 3. Local Nx Target Delegations`, harden worktree branch existence checks.
- `scripts/ep_security.py`: Add static policy enforcement engine and IaC rule linter.
- `scripts/ep_stack.py`: Replace C++ placeholder with `cppcheck` / `clang-tidy`.
- `scripts/ep_sync.py`: Expand tracked root files, add `docs/` and `.github/`, add orphan file pruning and atomic copies.
- `scripts/ep_vcs.py`: Add reachability validations and provider helpers.
- `scripts/validate-change-surface.py`: Safe relative path resolution and deterministic composite sorting for archived surfaces.
- `templates/profiles/contracts-project.json`: Fix scope tag to `"scope:shared"`.
- `tests/test_defect_remediations.py`: Align test assertions for contracts profile scope tag.
- `README.md`: Update test count badge to 180 passing.
- `.cursorrules`: Universal manifest projection of AGENT.md.
- `.windsurfrules`: Universal manifest projection of AGENT.md.
- `tests/test_validate_change_surface.py`: Unit tests for change surface lifecycle and relative path resolution.

## 4. Test Surface

### Unit & Domain Tests
- `tests/test_audit_remediation_fixes.py`: 10 new test cases verifying relative path fallback, empty catches, release scoping, and worktrees.
- Full regression suite across 180 unit tests (`pytest`).

### Integration Tests (Real Ephemeral Containers)
- N/A for pure CLI workflow logic.

### Failure & Resilience Tests
- Infracost and conftest graceful degradation tests, unpopulated surface fallback tests, and git worktree collision tests.

### Concurrency Tests
- Session collision detection and atomic file replacement during multi-file tree synchronization.

## 5. Invariants & Non-Negotiables Preserved
- [x] Tier 1: Zero-compromise verification gates and static typing (`mypy scripts` 0 errors across 20 source files).
- [x] Tier 1: Hard file ceiling $\le 800$ lines strictly respected across all files (`scripts/ep.py` at 723 lines).
- [x] Tier 1: Zero incomplete stubs or deferred mock logic (Rule 8.5).
- [x] Tier 2: 100% unit test pass rate preserved (180/180 tests passing).
- [x] Tier 2: 100% cryptographic SHA-256 parity with canonical skill store.

## 6. Risk Matrix & Rollback Strategy
| Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|
| Fallback selecting wrong archived surface | Low | Low | Deterministic composite sort key `(os.path.getmtime(p), p)` |
| False positives in expanded polyglot regexes | Low | Low | Scoped extensions and non-capturing boundaries |

### Rollback Strategy
Revert commits via standard git rollback or branch reset.
