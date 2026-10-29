---
title: "Change Surface: Expand Polyglot Cross-Stack Static Analysis and Dimension 7 Heuristics"
author: "Antigravity EP-OS Agent & DeepCoder"
created_date: "2026-10-28"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "enterprise-product"
---

# Change Surface: Expand Polyglot Cross-Stack Static Analysis and Dimension 7 Heuristics

## 1. Intent & Business Rationale
Implement polyglot static analysis heuristics and AST pattern expansion across all 10 enterprise dimensions:
1. Dimension 1: Detect mutable package-level state in Go handlers (`var cache = make(map[string]...)`, `[]string{}`) and Rust (`static mut`).
2. Dimension 3: Bounded queue prefetch verification across Rust (`rdkafka`, `lapin`), PHP AMQP (`basic_qos`), and Java consumers.
3. Dimension 5: Raw unparameterized SQL concatenation detection in Rust (`sqlx::query(&format!(...))`) and Java (`createNativeQuery`).
4. Dimension 6: W3C tracecontext correlation propagation heuristics for outbound HTTP calls across Go, Rust, PHP, C#, and Java.
5. Dimension 7: Direct cross-service relative import detection (`RULE-7.1-DIRECT-CROSS-PROJECT-IMPORT`) to enforce Hexagonal boundary integrity, and contract mutation checks (`RULE-7.2-UNVERSIONED-CONTRACT-MUTATION`).
6. Dimension 8: Empty error suppression detection for Java, Kotlin, and C# parameterless catch blocks.
7. Dimension 10: Tautological test assertion detection for Go testify suites (`assert.True(t, true)`, `require.Equal(t, 1, 1)`).
8. AST Structural Scanning: Refine `RULE-4.4-AST-NON-UTC-CLOCK` in `scripts/ep_ast.py` with Go `time.Now()` repository pattern matching.
9. Comprehensive Unit Test Suite: 9 new unit tests in `tests/test_audit_polyglot_expansion.py` verifying positive and negative cases.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `enterprise-product` | Profile D (Contracts & Libs) | Polyglot heuristic expansion, taxonomy alignment, AST rule refinement, and test suite |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `tests/test_audit_polyglot_expansion.py`: Unit test suite verifying all 10-dimension polyglot heuristics.

### Modified Files
- `references/audit-taxonomy.md`: Catalog Checks 7.1 and 7.2 under Dimension 7.
- `scripts/audit-runner.py`: Add Dimension 7 rules and expand heuristics for Go, Rust, PHP, C#, Java.
- `scripts/ep_ast.py`: Add Go `time.Now()` pattern to `RULE-4.4-AST-NON-UTC-CLOCK`.

## 4. Test Surface

### Unit & Domain Tests
- `tests/test_audit_polyglot_expansion.py`: 9 test cases covering Go/Rust mutable state, AMQP prefetch, SQL injection patterns, trace propagation, cross-service imports, empty catches, and tautologies.
- Full regression suite across 189 unit tests (`pytest`).

### Integration Tests (Real Ephemeral Containers)
- N/A for pure static heuristic and AST pattern logic.

### Failure & Resilience Tests
- Negative and edge-case pattern validation for multi-argument AMQP prefetch and parameterless catches.

### Concurrency Tests
- Zero shared mutable state across audit scanner regex engines.

## 5. Invariants & Non-Negotiables Preserved
- [x] Tier 1: Zero-compromise verification gates and static typing (`mypy scripts` 0 errors).
- [x] Tier 1: Hard file ceiling $\le 800$ lines strictly preserved (`scripts/audit-runner.py` at 630 lines, `scripts/ep.py` at 723 lines).
- [x] Tier 2: 100% test pass rate preserved (189/189 tests passing).
- [x] Tier 2: 100% cryptographic SHA-256 parity with canonical skill store.

## 6. Risk Matrix & Rollback Strategy
| Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|
| False positives on legitimate multi-argument AMQP calls | Low | Low | Refined regex parsing second and third parameters |
| False positives on internal shared library imports | Low | Low | Path constraint restricted to cross-service `../../services/` traversals |

### Rollback Strategy
Revert commits via standard git rollback or branch reset.
