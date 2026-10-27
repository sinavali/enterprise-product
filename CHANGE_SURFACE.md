---
title: "Change Surface: [Short Descriptive Title]"
author: "[Author or Agent ID]"
created_date: "2026-10-27"
target_branch: "main"
risk_level: "LOW"                    # LOW | MEDIUM | HIGH | CRITICAL
affected_projects:
  - "services/core"
---

# Change Surface: [Feature or Task Title]

## 1. Intent & Business Rationale
[Provide a clear, unambiguous statement of why this change is needed, what problem it solves, and the expected business outcome.]

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `services/core` | Profile A (DDD/Hexagonal) | Target project |

## 3. Code Surface (Targeted Symbols & Files)
Declare the exact files and symbols that will be modified or created. Modifying files outside this surface requires updating this document.

### Added Files
- `services/core/src/index.ts`

### Modified Files
- `services/core/src/service.ts`

## 4. Test Surface
Every code change must have a corresponding test surface. Happy-path-only tests are prohibited.

### Unit & Domain Tests
- `services/core/tests/unit/service.spec.ts`

### Integration Tests (Real Ephemeral Containers)
- `services/core/tests/integration/service.test.ts`

### Failure & Resilience Tests
- `services/core/tests/integration/resilience.test.ts`

### Concurrency Tests
- `services/core/tests/integration/concurrency.test.ts`

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
