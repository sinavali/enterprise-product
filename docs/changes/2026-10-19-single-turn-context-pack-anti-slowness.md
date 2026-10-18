---
title: "Change Surface: Single-Turn Context Ingestion Engine and Anti-Slowness Mandate"
author: "Antigravity"
created_date: "2026-10-19"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "root"
---

# Change Surface: Single-Turn Context Ingestion Engine and Anti-Slowness Mandate

## 1. Intent & Business Rationale
Prevent severe agent execution latency caused by multi-turn, sequential one-by-one file inspection (`view_file` roundtrips). Introduce `ep pack` (and `ep context`) to bundle declared Change Surface, git diff, or directory scope files into an LLM-optimized single-turn context stream, and enforce the Anti-Serialization Mandate across product governance.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `root` | Root Governance | Context pack engine, CLI subcommand, and manifest rules |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `scripts/ep_context.py`: Single-turn context bundle engine (`pack_files`, `collect_files_from_surface`, `collect_files_from_diff`, `collect_files_from_scope`, `cmd_pack`).
- `tests/test_ep_context.py`: Comprehensive test suite for context bundling, truncation, and CLI flags.
- `docs/changes/2026-10-19-single-turn-context-pack-anti-slowness.md`: Change surface specification.
- `docs/changes/2026-10-18-comprehensive-27-defect-remediation.md`: Comprehensive 27 defect remediation specification.
- `tests/test_defect_remediations.py`: Comprehensive test suite for all 27 defect closures.
- `templates/profiles/node-service-project.json`: Standard Node/TypeScript Profile A project contract.
- `templates/profiles/python-service-project.json`: Standard Python Profile A project contract.
- `templates/RUNBOOK.template.md`: Operational incident response and readiness runbook.
- `templates/POSTMORTEM.template.md`: Blameless postmortem template.
- `templates/CHAOS_EXPERIMENT.template.md`: Chaos engineering template.
- `templates/THREAT_MODEL.template.md`: STRIDE-based threat modeling template.
- `templates/monitoring/slo.template.yaml`: SLO definition template.
- `templates/monitoring/alerts.template.yaml`: Alert definitions template.
- `templates/monitoring/otel-collector-config.template.yaml`: OTel collector pipeline configuration.
- `templates/audit-log-migration.sql`: Immutable audit logging database schema.
- `templates/perf-test.k6.js`: Standard k6 load test script.
- `tests/test_audit_gap_closure.py`: Verification suite for audit gap closure.
- `tests/test_enterprise_catalog_enforcement.py`: Test suite for enterprise catalog enforcement.
- `tests/test_container_engine_resolver.py`: Test suite for container engine resolver.

### Modified Files
- `scripts/ep.py`: Register `pack` subcommand and route to `cmd_pack`.
- `scripts/ep_runner.py`: Topological depth waves and scoped dependency resolution.
- `scripts/ep_hooks.py`: Direct hook execution fallback.
- `scripts/ep_security.py`: Secret scanner path boundaries and entropy SBOM.
- `scripts/ep_vcs.py`: Base branch checking and mechanical auto-merge disable.
- `scripts/ep_scaffold.py`: Language tooling commands and preflight.
- `scripts/ep_adopt.py`: Dynamic schema path and scope inference normalization.
- `scripts/ep_ops.py`: SLO parsing and codeowners audit.
- `scripts/ep_session.py`: Porcelain rename parsing.
- `scripts/ep_sync.py`: Dynamic workspace root resolution.
- `scripts/ep_stack.py`: Polyglot stack definitions.
- `scripts/ep_ast.py`: AST structural rules.
- `scripts/verify-agent-manifests.py`: Semantic stem matching.
- `scripts/audit-runner.py`: Mechanical checks for UTC storage and outbox.
- `AGENT.md`: Add Zero-Serialization File Ingestion Mandate to Section 3 and update `implement` mode.
- `SKILL.md`: Add `ep pack` CLI documentation and single-turn ingestion step in Mode `implement`.
- `references/core-directives.md`: Add Prime Directive P11 (Single-Turn Context Ingestion Mandate).
- `templates/AGENT.template.md`: Add single-turn ingestion rule to subproject agent template.
- `references/optional-tooling.md`: Tooling integration contracts.
- `references/audit-taxonomy.md`: Audit taxonomy.
- `references/compliance-matrix.md`: Compliance mapping.
- `references/deep-observability.md`: Deep observability reference.
- `references/exclusions.md`: Architectural exclusions.
- `.cursorrules`: Manifest projection.
- `.windsurfrules`: Manifest projection.
- `CLAUDE.md`: Manifest projection.
- `tests/test_verify_agent_manifests.py`: Manifest verification tests.

## 4. Test Surface

### Unit & Domain Suites
- `tests/test_ep_context.py`: Context packing unit and CLI integration tests.
- Full regression suite: `python3 -m unittest discover tests`.

## 5. Invariants Preserved
- Zero external pip package dependencies (pure Python standard library).
- Maximum line count $\le 800$ lines per file (`RULE-2.6-FILE-SIZE-CEILING`).
- Blast-radius compliance via `ep surface check-diff --strict`.
