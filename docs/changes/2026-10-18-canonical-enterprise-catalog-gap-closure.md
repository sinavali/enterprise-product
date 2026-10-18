---
title: "Change Surface: Canonical Enterprise Engineering Catalog Gap-Closure"
author: "Antigravity"
created_date: "2026-10-18"
target_branch: "main"
risk_level: "MEDIUM"
affected_projects:
  - "root"
---

# Change Surface: Canonical Enterprise Engineering Catalog Gap-Closure

## 1. Intent & Business Rationale
Execute a comprehensive gap-closure pass across the 86 canonical enterprise-grade software engineering terms in EP-OS.
Extend mechanical enforcement across audit dimensions, AST structural linters, CLI operational tools, enterprise templates, and reference specifications while preserving backward compatibility, zero-dependency core execution, and passing all tests.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `root` | Root Governance | Manifests, references, CLI tools, templates, AST scanners, and self-tests |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `docs/changes/2026-10-18-canonical-enterprise-catalog-gap-closure.md`: Change Surface specification.
- `references/exclusions.md`: Documented deliberate exclusions (Vendor Viability, Continuous Profiling, eBPF).
- `references/optional-tooling.md`: Optional tooling registry (k6, OTel Collector, Infracost, OPA, Chaos Mesh).
- `references/deep-observability.md`: Standards for Golden Signals, RED/USE methods, W3C Trace Context, and Exemplars.
- `references/compliance-matrix.md`: Compliance mappings for SOC 2, ISO 27001, GDPR, and data classification.
- `templates/RUNBOOK.template.md`: Operational incident response and readiness runbook.
- `templates/POSTMORTEM.template.md`: Blameless postmortem template with root cause and action items.
- `templates/CHAOS_EXPERIMENT.template.md`: Chaos engineering and game day experiment template.
- `templates/THREAT_MODEL.template.md`: STRIDE-based application threat modeling template.
- `templates/monitoring/`: Directory containing enterprise monitoring templates.
- `templates/monitoring/slo.template.yaml`: Service Level Objective definition template.
- `templates/monitoring/alerts.template.yaml`: Prometheus/Alertmanager alert definitions.
- `templates/monitoring/otel-collector-config.template.yaml`: OTel collector pipeline configuration.
- `templates/audit-log-migration.sql`: Immutable audit logging database schema.
- `templates/perf-test.k6.js`: Standard k6 load and stress test script template.
- `scripts/ep_ops.py`: Operational CLI extensions (`slo`, `codeowners`, `dora`, `perf`).
- `tests/test_enterprise_catalog_enforcement.py`: Comprehensive test suite for new gates.
- `tests/test_verify_agent_manifests.py`: Verification tests for manifest schema extensions.

### Modified Files
- `references/audit-taxonomy.md`: Extend Dimensions 1, 2, 3, 4, 5, 6, 8, 9 with new checks.
- `scripts/audit-runner.py`: Add heuristic scanners for statelessness, backpressure, rate limiting, and config validation.
- `scripts/ep_ast.py`: Add AST rules for mutable global state and unhandled error boundaries.
- `scripts/ep_security.py`: Add `cmd_iac` static scanning for infrastructure manifests.
- `scripts/ep.py`: Register and dispatch new CLI subcommands (`iac`, `slo`, `codeowners`, `dora`, `perf`).
- `scripts/verify-agent-manifests.py`: Add validation support for optional `dr`, `slo`, and `resources` fields.
- `scripts/ep_scaffold.py`: Include `dr`, `slo`, and `resources` stubs in generated `AGENT.md`.
- `templates/AGENT.template.md`: Update subproject manifest template with resilience and SLO metadata.
- `AGENT.md`: Document new operational commands and standards.
- `SKILL.md`: Update CLI reference index and operational capabilities.
- `.cursorrules`: Manifest projection from AGENT.md.
- `.windsurfrules`: Manifest projection from AGENT.md.
- `CLAUDE.md`: Manifest projection from AGENT.md.

## 4. Test Surface

### Unit & Domain Suites
- `tests/test_enterprise_catalog_enforcement.py`: Test new audit checks, AST patterns, and CLI subcommands.
- `tests/test_audit_runner.py`: Verify new 10-dimension audit heuristics.
- `tests/test_ep_ast.py`: Verify new AST pattern rules.
- `tests/test_ep_cli.py`: Verify new CLI subcommand routing and graceful fallbacks.
- `tests/test_verify_agent_manifests.py`: Verify manifest schema validations.
- Full suite verification: `python3 -m unittest discover tests`.

## 5. Invariants Preserved
- All 10 Tier 1 enterprise inviolables remain strictly preserved.
- 100% backward compatibility with existing subprojects and CLI commands.
- Zero external package dependencies required for core Python execution.
- Real ephemeral container testing standards preserved.

## 6. Risk Matrix
- **Risk Level**: MEDIUM. Expands audit taxonomy and CLI surface; zero breaking changes to existing contracts.
- **Rollback Strategy**: Revert git commit via standard VCS rollback.
