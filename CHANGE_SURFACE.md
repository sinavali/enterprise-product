---
title: "Change Surface: Enterprise Enforcements and Agent Speed Acceleration"
author: "Antigravity OS Engineer"
created_date: "2026-10-29"
target_branch: "main"
risk_level: "LOW"                    # LOW | MEDIUM | HIGH | CRITICAL
affected_projects:
  - "scripts"
---

# Change Surface: Enterprise Enforcements & Agent Speed Acceleration

## 1. Intent & Business Rationale
Implement complete Gap Assessment for Groups A through G and Tooling Guidance, connect standalone checkers into ep verify, implement mechanical quality invariants (idempotency, graceful shutdown, runbooks, ephemeral DBs, layer coverage), add tooling guidance extensions (ep chaos, ep contract, ep sbom, ep perf locust), and accelerate agent development cycle speed.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `services/core` | Profile A (DDD/Hexagonal) | Target project |

## 3. Code Surface (Targeted Symbols & Files)
Declare the exact files and symbols that will be modified or created. Modifying files outside this surface requires updating this document.

### Added Files
- `scripts/ep_quality.py`
- `scripts/ep_tooling.py`
- `templates/openapi-contract.template.yaml`
- `templates/service-contract.template.proto`
- `templates/perf-test.locust.py`
- `tests/test_ep_quality.py`
- `tests/test_ep_tooling.py`
- `tests/test_ep_fast_paths.py`


### Modified Files
- `scripts/ep.py`
- `scripts/ep_ops.py`
- `scripts/ep_ast.py`
- `scripts/ep_context.py`
- `AGENT.md`
- `CLAUDE.md`
- `.cursorrules`
- `.windsurfrules`
- `.gitignore`
- `references/core-directives.md`
- `references/audit-taxonomy.md`
- `references/optional-tooling.md`

## 4. Test Surface
Every code change must have a corresponding test surface. Happy-path-only tests are prohibited.

### Unit & Domain Tests
- `tests/test_ep_quality.py`
- `tests/test_ep_tooling.py`
- `tests/test_ep_fast_paths.py`

## 5. Invariants & Non-Negotiables Preserved
- [ ] Tier 1: Pure domain logic remains 100% free of framework or ORM imports.
- [ ] Tier 1: Real container integration tests (no engine-substitution emulators like SQLite for Postgres).
- [ ] Tier 1: All stored and wire timestamps use UTC ISO-8601 (`Z`).
- [ ] Tier 1: Directory nesting depth does not exceed 6 levels from project root.
- [ ] Tier 1: Database migrations follow Expand/Contract pattern for zero-downtime rollout.
- [ ] Tier 2: Files respect size ceilings (\le 800 lines hard, \le 400 lines soft); no micro-file sprawl.
- [ ] Tier 2: Domain test coverage maintains \ge 95% line & branch coverage; adapters \ge 80%.
- [ ] Tier 2: Transactional outbox pattern used for domain events published to brokers.
- [ ] Tier 2: Backward compatibility of existing API contracts preserved.

## 6. Risk Matrix & Rollback Strategy
| Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|
| Potential regression in callers | Low | Low | Comprehensive automated regression test suite |

### Rollback Strategy
Revert commits via standard git rollback or branch reset.
