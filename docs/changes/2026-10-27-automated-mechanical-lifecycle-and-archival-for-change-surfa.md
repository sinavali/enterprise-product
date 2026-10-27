---
title: "Change Surface: Automated Mechanical Lifecycle and Archival for Change Surface"
author: "Antigravity EP-OS Agent"
created_date: "2026-10-27"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "enterprise-product"
---

# Change Surface: Automated Mechanical Lifecycle and Archival for Change Surface

## 1. Intent & Business Rationale
Implement automated mechanical lifecycle for `CHANGE_SURFACE.md` to eliminate stale surface bloat, branch pollution, and unarchived task accumulation:
1. Provide `ep surface archive` command to parse the active Change Surface, extract its ISO date and slug, persist it to `docs/changes/<date>-<slug>.md`, and reset root `CHANGE_SURFACE.md` to a clean baseline template (`CLEAN_SURFACE_TEMPLATE`).
2. Integrate auto-archival into `ep surface init`: automatically archives existing populated surfaces before scaffolding a new task surface.
3. Integrate auto-archival into `ep pr create-prod`: automatically archives active surfaces prior to production PR creation.
4. Update `SKILL.md`, `AGENT.md`, `references/documentation-system.md`, `references/vcs-pr-protocol.md`, and project manifests (`CLAUDE.md`, `.cursorrules`, `.windsurfrules`) to enforce pre-merge and pre-promotion archival.
5. Expand unit test suite with 6 new tests verifying archival, template reset, collision handling, CLI execution, and `init` auto-archiving.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `enterprise-product` | Profile D (Contracts & Libs) | Surface lifecycle implementation, CLI integration, gate enforcement, and unit tests |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- None

### Modified Files
- `scripts/ep_scaffold.py`: Implement `CLEAN_SURFACE_TEMPLATE`, `get_clean_surface_template`, `is_surface_unpopulated`, and `archive_change_surface`.
- `scripts/ep_vcs.py`: Auto-archive active surface in `cmd_pr` before creating production PRs.
- `scripts/ep.py`: Add `archive` action and options to `cmd_surface`, auto-archive in `init`, preserve line count ceiling $\le 800$.
- `scripts/audit-runner.py`: Exclude build artifact directories (`obj`, `bin`, `target`) from audit scans.
- `scripts/ep_security.py`: Exclude build artifact directories (`obj`, `bin`, `target`) from secret scans.
- `tests/test_validate_change_surface.py`: Add comprehensive unit tests for `archive_change_surface` and CLI `ep surface archive`.
- `SKILL.md`: Document `ep surface archive`, update Mode `pr-audit` with archival mandate.
- `AGENT.md`: Document Change Surface archival lifecycle in Rule 5 and Mode `pr-audit`.
- `CLAUDE.md`: Universal projection of AGENT.md.
- `.cursorrules`: Universal projection of AGENT.md.
- `.windsurfrules`: Universal projection of AGENT.md.
- `README.md`: Update test count badge to 170 passing, add `ep surface archive` to CLI table.
- `references/documentation-system.md`: Document section 2.3 for mechanical archival lifecycle.
- `references/vcs-pr-protocol.md`: Document pre-merge archival gate in Step 4.

## 4. Test Surface

### Unit & Domain Tests
- `tests/test_validate_change_surface.py`: Verify archival, collision handling, clean template reset, `--no-reset`, unpopulated template skipping, and CLI integration.
- Full regression suite across 170 unit tests (`pytest`).

### Integration Tests (Real Ephemeral Containers)
- N/A for pure CLI workflow logic.

### Failure & Resilience Tests
- Test unpopulated baseline template detection, missing surface handling, and file collision numbering.

### Concurrency Tests
- File collision suffix incrementation (`...-1.md`) when concurrent or repeated archives occur.

## 5. Invariants & Non-Negotiables Preserved
- [x] Tier 1: Zero-compromise verification gates and static typing (`mypy scripts` 0 errors).
- [x] Tier 1: Directory nesting depth does not exceed 6 levels from project root.
- [x] Tier 2: Files respect size ceilings ($\le 800$ lines hard, $\le 400$ lines soft); `scripts/ep.py` at 778 lines.
- [x] Tier 2: 100% test pass rate preserved (170/170 passing).
- [x] Tier 2: Atomic POSIX writes (`atomic_write`) for all generated and reset surface files.

## 6. Risk Matrix & Rollback Strategy
| Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|
| Accidental overwriting of historical change surfaces | Low | Low | Deterministic timestamp and slug prefix with collision indexing |
| Archival of unpopulated empty template | Low | Low | Explicit token pattern detection (`is_surface_unpopulated`) |

### Rollback Strategy
Revert commits via standard git rollback or branch reset.
