# Change Surface: EP-OS Minimalized Release Binary Packaging & v1.0.0 Asset Generation

## 1. Intent & Business Rationale
Implement a release packaging task (`ep release pack`) for EP-OS itself that creates an absolutely minimalized binary distribution (`Packed.zip`) capped at a maximum of 30 files. Re-generate the `v1.0.0` GitHub release with the newly generated `Packed.zip` attached.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `.` | Profile D (Shared Contracts & Core Libraries) | EP-OS CLI & Packaging Task |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `tests/test_ep_release_pack.py`
- `docs/changes/2026-10-29-ep-os-minimal-release-binary-package.md`

### Modified Files
- `scripts/ep_vcs.py`
- `scripts/ep.py`
- `project.json`
- `SKILL.md`
- `docs/releases/RELEASE_v1.0.0_LTS.md`

## 4. Test Surface
- `tests/test_ep_release_pack.py` (Tests file count $\le 30$, structure, executable launcher, and max-files error handling).
