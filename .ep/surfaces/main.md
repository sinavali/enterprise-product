---
title: "Change Surface: EP-OS Skill Finalization, Polyglot Boundaries & Production-Grade Governance (Cycle 2)"
author: "Antigravity"
created_date: "2026-11-12"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "enterprise-product"
---

# Change Surface: EP-OS Skill Finalization, Polyglot Boundaries & Production-Grade Governance (Cycle 2)

## 1. Intent & Business Rationale
Finalize and harden the `enterprise-product` (EP-OS) skill repository into a minimal, high-quality, production-grade system across 5 iterative review-and-fix cycles. In Cycle 2, enforce Domain-Driven Design (DDD) and Hexagonal Architecture boundary integrity across polyglot languages (Python, TypeScript, Go, C#, Dart, Java, Kotlin), block inward domain-to-application imports, block cloud SDK and transport imports in pure domain, expand polyglot copyleft license scanning (Composer, Go, Pubspec, Pip, Csproj), harden E2E assertions for F9–F11 to eliminate all weak compound assertions, and maintain strict <= 800 LOC limits across all files.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `.` | Profile D (Shared Contracts & Core Libraries) | EP-OS CLI, Boundary Enforcement & Governance |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `.ep/surfaces/main.md`
- `tests/README.md`
- `tests/e2e/__init__.py`
- `tests/e2e/conftest.py`
- `tests/e2e/test_tier1_features.py`
- `tests/e2e/test_tier1_features_part2.py`
- `tests/e2e/test_tier2_boundaries.py`
- `tests/e2e/test_tier3_combinations.py`
- `tests/e2e/test_tier4_scenarios.py`
- `tests/test_boundary_checks.py`
- `tests/test_concurrency.py`
- `tests/test_ep_scaffold.py`
- `tests/test_license_scanner.py`

### Modified Files
- `.cursorrules`
- `.gitignore`
- `.windsurfrules`
- `AGENT.md`
- `CLAUDE.md`
- `README.md`
- `SKILL.md`
- `scripts/audit-runner.py`
- `scripts/ep.py`
- `scripts/ep_context.py`
- `scripts/ep_doctor.py`
- `scripts/ep_ops.py`
- `scripts/ep_quality.py`
- `scripts/ep_runner.py`
- `scripts/ep_scaffold.py`
- `scripts/ep_security.py`
- `scripts/ep_session.py`
- `scripts/ep_sync.py`
- `scripts/ep_vcs.py`
- `scripts/validate-change-surface.py`
- `scripts/verify-agent-manifests.py`
- `tests/e2e/conftest.py`
- `tests/e2e/test_tier1_features.py`
- `tests/e2e/test_tier1_features_part2.py`
- `tests/test_audit_remediation_fixes.py`
- `tests/test_audit_runner.py`
- `tests/test_defect_remediations.py`
- `tests/test_ep_quality.py`
- `tests/test_ep_security.py`
- `tests/test_ep_vcs_and_sessions.py`

### Deleted Files / Pruned Domains
- `CHANGE_SURFACE.md`
- `references/agent-hierarchy-spec.md`
- `references/architectural-profiles.md`
- `references/audit-taxonomy.md`
- `references/compliance-matrix.md`
- `references/core-directives.md`
- `references/deep-observability.md`
- `references/documentation-system.md`
- `references/exclusions.md`
- `references/execution-engine.md`
- `references/monorepo-nx-standard.md`
- `references/multi-session-and-agent-agnosticism.md`
- `references/nc-protocol.md`
- `references/optional-tooling.md`
- `references/polyglot-stack-matrix.md`
- `references/release-and-milestone-governance.md`
- `references/static-analysis-matrix.md`
- `references/testing-matrix.md`
- `references/vcs-pr-protocol.md`
- `templates/profiles/contracts-project.json`
- `templates/profiles/flutter-mobile-project.json`
- `templates/profiles/go-service-project.json`
- `templates/profiles/next-web-project.json`
- `templates/profiles/node-service-project.json`
- `templates/profiles/python-service-project.json`
- `templates/profiles/rust-service-project.json`
- `docs/changes/2026-10-13-audit-findings-and-governance-hardening.md`
- `docs/changes/2026-10-13-comprehensive-audit-remediations.md`
- `docs/changes/2026-10-13-pre-commit-enforcement.md`
- `docs/changes/2026-10-13-robustness-and-edge-case-hardening.md`
- `docs/changes/2026-10-18-anti-mvp-and-zero-stub-mandate.md`
- `docs/changes/2026-10-18-canonical-enterprise-catalog-gap-closure.md`
- `docs/changes/2026-10-18-comprehensive-27-defect-remediation.md`
- `docs/changes/2026-10-18-comprehensive-epos-audit-and-gap-closure.md`
- `docs/changes/2026-10-18-smart-container-engine-resolution.md`
- `docs/changes/2026-10-19-single-turn-context-pack-anti-slowness.md`
- `docs/changes/2026-10-20-apply-epos-to-itself-and-vcs-init.md`
- `docs/changes/2026-10-25-v1.0.0-lts-audit-remediation-and-governance.md`
- `docs/changes/2026-10-27-automated-mechanical-lifecycle-and-archival-for-change-surfa.md`
- `docs/changes/2026-10-28-expand-polyglot-cross-stack-static-analysis-and-dimension-7.md`
- `docs/changes/2026-10-28-full-polyglot-enterprise-audit-remediation-and-cross-stack-h.md`
- `docs/changes/2026-10-29-enterprise-enforcements-and-agent-speed-acceleration.md`
- `docs/changes/2026-10-29-ep-os-minimal-release-binary-package.md`
- `docs/releases/RELEASE_v1.0.0_LTS.md`

## 4. Test Surface

### Unit & Domain Tests
- `tests/test_boundary_checks.py` (Inverted dependency, cloud SDK, transport, and polyglot boundary checks)
- `tests/test_concurrency.py` (Atomic file operations, process/thread race condition tests)
- `tests/test_license_scanner.py` (Polyglot supply chain copyleft license scanner)
- `tests/test_ep_scaffold.py`
- `tests/test_ep_quality.py`
- `tests/test_ep_security.py`
- `tests/test_audit_runner.py`
- `tests/test_audit_remediation_fixes.py`
- `tests/test_defect_remediations.py`
- `tests/test_ep_vcs_and_sessions.py`
- Full unittest suite (`python3 -m unittest discover tests`)

### Integration & E2E Tests (Real Ephemeral Containers)
- `tests/e2e/test_tier1_features.py` (50 tests, hardened F9–F10 assertions)
- `tests/e2e/test_tier1_features_part2.py` (40 tests, hardened F11 assertions)
- `tests/e2e/test_tier2_boundaries.py` (90 tests)
- `tests/e2e/test_tier3_combinations.py` (15 tests)
- `tests/e2e/test_tier4_scenarios.py` (6 tests)
- Full pytest test suite (201 E2E tests passing)

### Failure & Resilience Tests
- Inverted domain-to-application dependency failure injection tests
- Cloud SDK (`boto3`, `@aws-sdk`, `google.cloud`, `azure`) in domain failure tests
- Low-level transport (`http`, `urllib`, `requests`) in domain failure tests
- Polyglot boundary violation tests (C#, Dart, Java, Kotlin)
- Copyleft license contagion detection (GPL/AGPL) across Composer, Go, Pubspec, Pip, and Csproj

## 5. Invariants & Non-Negotiables Preserved
- [x] Tier 1: Pure domain logic remains 100% free of framework, ORM, application, cloud SDK, or transport imports.
- [x] Tier 1: Real ephemeral containers for DB testing (Podman/Testcontainers).
- [x] Tier 1: Atomic file writes via temporary files and `os.replace`.
- [x] Tier 1: Single unified `SKILL.md` (< 200 lines).
- [x] Tier 2: File line ceiling strictly enforced (<= 800 lines across all scripts and tests).
- [x] Dedicated `.ep/` isolation for runtime caches, sessions, dist, and surfaces.
- [x] Zero external PyPI runtime dependencies (standard library only).

## 6. Risk Matrix & Rollback Strategy
| Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|
| Polyglot boundary false positives on clean domain entities | Low | High | Strictly scope boundary checks to files under `/domain` directories and test on clean Profile A/B/C/D entities. |
| `scripts/ep_quality.py` exceeding 800 LOC ceiling | High | High | Keep boundary logic compact using table-driven regex patterns; isolate license logic in `scripts/ep_security.py`. |
| Unintended blast radius failure in Gate 6 | Low | High | Pre-declare all added and modified files in `.ep/surfaces/main.md` before code modification. |

### Rollback Strategy
Revert commits via git rollback (`git checkout HEAD~1 -- <files>`).
