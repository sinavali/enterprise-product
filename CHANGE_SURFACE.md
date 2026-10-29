---
title: "Change Surface: EP-OS Minimalized Release Binary Packaging & v1.0.0 Asset Generation"
author: "Antigravity"
created_date: "2026-10-29"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "enterprise-product"
---

# Change Surface: EP-OS Minimalized Release Binary Packaging & v1.0.0 Asset Generation

## 1. Intent & Business Rationale
Provide an automated, deterministic release packaging task for EP-OS itself (`ep release pack` / `nx package`) that compiles an absolutely minimalized release zip binary (`Packed.zip`) containing strictly $\le 30$ files with zero extraneous documentation, caches, or tests, while remaining 100% executable and self-contained. Re-release `v1.0.0` with the `Packed.zip` asset attached to GitHub Releases.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `.` | Profile D (Shared Contracts & Core Libraries) | EP-OS CLI & Packaging Task |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `tests/test_ep_release_pack.py`
- `docs/changes/2026-10-29-ep-os-minimal-release-binary-package.md`
- `Packed.zip`

### Modified Files
- `scripts/ep_vcs.py`
- `scripts/ep.py`
- `project.json`
- `SKILL.md`
- `docs/releases/RELEASE_v1.0.0_LTS.md`
- `.gitignore`

## 4. Test Surface

### Unit & Domain Tests
- `tests/test_ep_release_pack.py`

### Integration Tests (Real Ephemeral Containers)
- N/A (CLI Packaging & Artifact Verification)

### Failure & Resilience Tests
- `tests/test_ep_release_pack.py` (file count ceiling enforcement > 30 files, missing files, archive integrity)

### Concurrency Tests
- N/A

## 5. Invariants & Non-Negotiables Preserved
- [x] Tier 1: Pure domain logic remains 100% free of framework or ORM imports.
- [x] Tier 1: Zero swallowed exceptions; typed arguments and deterministic exits.
- [x] Tier 1: Atomic file writes via temporary files and `os.replace`.
- [x] Tier 2: File count ceiling strictly enforced ($\le 30$ files).
- [x] Tier 2: Files respect size ceilings ($\le 800$ lines hard).

## 6. Risk Matrix & Rollback Strategy
| Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|
| Missing files in packed distribution | Low | Medium | Automated extraction test verifying CLI execution |
| Exceeding 30 files limit | Low | Low | Hard assertion and error exit in `pack_release` |

### Rollback Strategy
Revert commits via git rollback.
