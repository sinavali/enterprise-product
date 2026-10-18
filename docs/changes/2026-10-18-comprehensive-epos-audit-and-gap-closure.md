---
title: "Change Surface: Comprehensive EP-OS Audit and Gap Closure"
author: "Antigravity"
created_date: "2026-10-18"
target_branch: "main"
risk_level: "MEDIUM"
affected_projects:
  - "root"
---

# Change Surface: Comprehensive EP-OS Audit and Gap Closure

## 1. Intent & Business Rationale
Deep audit and remediation pass across EP-OS content and context.
Closes identified gaps across:
1. Missing Profile A scaffolding templates for Node/TypeScript and Python.
2. Incomplete 4-target contracts in polyglot stack detection (`scripts/ep_stack.py`).
3. Schema alignment bug in brownfield adoption wizard (`scripts/ep_adopt.py`).
4. Missing `human-only-prod` rule in Tier 1 banned overrides (`scripts/verify-agent-manifests.py`).
5. Missing operational runbook heuristic in 10-dimension audit runner (`scripts/audit-runner.py`).
6. Pre-push hook verification gate enhancement (`scripts/ep_hooks.py`).
7. Tier 1 numbered list alignment in core directives (`references/core-directives.md`).
8. Mode count documentation consistency in `SKILL.md`.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `root` | Root Governance | Manifests, references, CLI tools, profile templates, and test suites |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `docs/changes/2026-10-18-comprehensive-epos-audit-and-gap-closure.md`: Change Surface specification.
- `templates/profiles/node-service-project.json`: Standard Node/TypeScript Profile A project contract.
- `templates/profiles/python-service-project.json`: Standard Python Profile A project contract.
- `templates/RUNBOOK.template.md`: Operational incident response and readiness runbook.
- `templates/POSTMORTEM.template.md`: Blameless postmortem template with root cause and action items.
- `templates/CHAOS_EXPERIMENT.template.md`: Chaos engineering and game day experiment template.
- `templates/THREAT_MODEL.template.md`: STRIDE-based application threat modeling template.
- `templates/monitoring/slo.template.yaml`: Service Level Objective definition template.
- `templates/monitoring/alerts.template.yaml`: Prometheus/Alertmanager alert definitions.
- `templates/monitoring/otel-collector-config.template.yaml`: OTel collector pipeline configuration.
- `templates/audit-log-migration.sql`: Immutable audit logging database schema.
- `templates/perf-test.k6.js`: Standard k6 load and stress test script template.
- `scripts/ep_ops.py`: Operational CLI extensions (`slo`, `codeowners`, `dora`, `perf`).
- `tests/test_audit_gap_closure.py`: Automated verification suite for closed audit gaps.
- `tests/test_enterprise_catalog_enforcement.py`: Test suite for enterprise catalog enforcement.

### Modified Files
- `scripts/ep.py`: Register and dispatch CLI commands.
- `scripts/ep_ast.py`: AST pattern rules for enterprise boundaries.
- `scripts/ep_ops.py`: Operational commands implementation.
- `scripts/ep_security.py`: Security and IaC static analysis commands.
- `scripts/ep_stack.py`: Add standard audit target definitions for all 13 supported language stacks.
- `scripts/ep_scaffold.py`: Wire Node/TS and Python Profile A templates into scaffolding router.
- `scripts/ep_adopt.py`: Fix frontmatter keys to emit compliant `profile` and `stack` properties.
- `scripts/verify-agent-manifests.py`: Add `human-only-prod` to `TIER_1_BANNED_OVERRIDES` and alias `architectural_profile`.
- `scripts/ep_hooks.py`: Add `ep verify` execution to native pre-push hook.
- `scripts/audit-runner.py`: Add heuristic check for service runbooks under Check 9.5.
- `references/core-directives.md`: Align numbered Tier 1 inviolables list with root AGENT.md.
- `references/audit-taxonomy.md`: Extend audit taxonomy checks.
- `references/compliance-matrix.md`: Compliance framework mapping.
- `references/deep-observability.md`: Deep observability reference guide.
- `references/exclusions.md`: Enterprise catalog exclusion decisions and rationales.
- `references/optional-tooling.md`: Optional tooling integrations reference.
- `templates/AGENT.template.md`: Subproject manifest template with operational fields.
- `SKILL.md`: Update operational mode count and description.
- `AGENT.md`: Document enhanced pre-push gate and profile templates.
- `.cursorrules`: Manifest projection from AGENT.md.
- `.windsurfrules`: Manifest projection from AGENT.md.
- `CLAUDE.md`: Manifest projection from AGENT.md.
- `tests/test_verify_agent_manifests.py`: Manifest verification tests.

## 4. Test Surface

### Unit & Domain Suites
- `tests/test_audit_gap_closure.py`: Tests for Node/Python scaffolding, stack detection 4-target contracts, brownfield adoption schema, and human-only prod override blocking.
- Full test suite: `python3 -m unittest discover tests`.

## 5. Invariants Preserved
- All 10 Tier 1 enterprise inviolables remain strictly preserved.
- Zero external package dependencies for core Python execution.
- 100% backward compatibility with all existing CLI commands and profiles.

## 6. Risk Matrix
- **Risk Level**: MEDIUM. Enhances scaffolding templates, stack detection, and audit heuristics; zero breaking changes.
- **Rollback Strategy**: Revert git commit via standard VCS rollback.
