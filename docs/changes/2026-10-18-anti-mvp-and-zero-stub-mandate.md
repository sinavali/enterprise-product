---
title: "Change Surface: Anti-MVP and Zero-Stub Enterprise Mandate"
author: "Antigravity"
created_date: "2026-10-18"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "root"
---

# Change Surface: Anti-MVP and Zero-Stub Enterprise Mandate

## 1. Intent & Business Rationale
Enforce an explicit, non-negotiable Tier 1 Inviolable directive forbidding AI coding agents and human contributors from proposing, developing, or landing "MVP", "Proof-of-Concept", "mock-first", or "phased hardening" solutions. 

In enterprise environments, every unit of work—regardless of how narrow or bounded its scope—must be delivered as a finalized, fully hardened, production-ready implementation with complete error handling, timeouts, retries, and ephemeral container verification from the outset.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `root` | Root Governance | Manifests, core directives, audit taxonomy, manifest verifier, and test suites |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `docs/changes/2026-10-18-anti-mvp-and-zero-stub-mandate.md`: Change Surface specification.

### Modified Files
- `AGENT.md`: Add Tier 1 Inviolable #10: "Anti-MVP & Zero-Stub Mandate".
- `references/core-directives.md`: Declare Tier 1 Inviolable #10 and Anti-MVP protocol in Section 1 and Section 2.
- `references/audit-taxonomy.md`: Add Check 8.5 ("Anti-MVP & Zero-Stub Mandate") to Dimension 8.
- `scripts/verify-agent-manifests.py`: Add `anti-mvp` and `zero-stub` to `TIER_1_BANNED_OVERRIDES`.
- `templates/AGENT.template.md`: Add Anti-MVP invariant to Project Invariants.
- `tests/test_verify_agent_manifests.py`: Add unit test for Anti-MVP override refusal.
- `.cursorrules`: Manifest projection from AGENT.md.
- `.windsurfrules`: Manifest projection from AGENT.md.

## 4. Test Surface

### Unit & Domain Suites
- `tests/test_verify_agent_manifests.py`: Add test asserting that attempting to override `anti-mvp` or `zero-stub` in subproject manifests is mechanically rejected.
- Run full suite: `python3 -m unittest discover tests`

## 5. Invariants Preserved
- All Tier 1 enterprise inviolables remain strictly preserved.
- No backward compatibility breaks to existing subprojects or scripts.
- Single source of truth in `AGENT.md` maintained via `ep manifest sync`.

## 6. Risk Matrix
- **Risk Level**: LOW. Documentation and rule addition with mechanical verification test.
- **Rollback Strategy**: Revert git commit via standard VCS rollback.
