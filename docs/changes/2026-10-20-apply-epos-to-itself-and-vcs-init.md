---
title: "Change Surface: Apply EP-OS Governance to Self Monorepo and VCS Initialization"
author: "Antigravity"
created_date: "2026-10-20"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "root"
---

# Change Surface: Apply EP-OS Governance to Self Monorepo and VCS Initialization

## 1. Intent & Business Rationale
Apply complete EP-OS monorepo governance directly to its own repository (dogfooding):
- Monorepo root `project.json` defining standard Nx targets (`lint`, `test`, `build`, `audit`).
- `.github/workflows/ep-ci.yml` automated GitHub Actions workflow enforcing all mechanical gates.
- `.github/CODEOWNERS` deterministic code ownership mapping.
- Native git hooks (`pre-commit`, `pre-push`, `commit-msg`) installed locally.
- `ep vcs init-branches` subcommand to initialize multi-tier branches (`test`, `stage`, `prod`).

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `root` | Root Governance (Profile D) | Root project contract, CI workflows, VCS initialization |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `.github/`: GitHub metadata and codeowners directory.
- `project.json`: Root Nx project contract with lint, test, build, audit targets.
- `.github/CODEOWNERS`: Global codeownership declaration.
- `scripts/ep_context.py`: Single-turn context pack engine.
- `tests/test_ep_context.py`: Tests for context pack engine.
- `docs/changes/2026-10-20-apply-epos-to-itself-and-vcs-init.md`: Active change surface.
- `docs/changes/2026-10-19-single-turn-context-pack-anti-slowness.md`: Prior change surface.
- `docs/changes/2026-10-18-comprehensive-27-defect-remediation.md`: Comprehensive defect remediation surface.
- `tests/test_defect_remediations.py`: Comprehensive test suite.
- `templates/profiles/node-service-project.json`: Node profile template.
- `templates/profiles/python-service-project.json`: Python profile template.
- `templates/RUNBOOK.template.md`: Runbook template.
- `templates/POSTMORTEM.template.md`: Postmortem template.
- `templates/CHAOS_EXPERIMENT.template.md`: Chaos template.
- `templates/THREAT_MODEL.template.md`: Threat model template.
- `templates/monitoring/slo.template.yaml`: SLO template.
- `templates/monitoring/alerts.template.yaml`: Alerts template.
- `templates/monitoring/otel-collector-config.template.yaml`: OTel template.
- `templates/audit-log-migration.sql`: Audit log SQL template.
- `templates/perf-test.k6.js`: k6 script template.
- `tests/test_audit_gap_closure.py`: Audit gap closure tests.
- `tests/test_enterprise_catalog_enforcement.py`: Catalog enforcement tests.
- `tests/test_container_engine_resolver.py`: Container resolver tests.

### Modified Files
- `scripts/ep.py`: Register `vcs init-branches` action.
- `scripts/ep_vcs.py`: Implement `init-branches` action for multi-tier branch setup.
- `scripts/verify-agent-manifests.py`: Distinguish root manifest from subproject manifests when root project.json exists.
- `scripts/ep_runner.py`: Topological level waves.
- `scripts/ep_hooks.py`: Direct hook fallback.
- `scripts/ep_security.py`: Secret scanner boundaries.
- `scripts/ep_scaffold.py`: Language tooling scaffolding.
- `scripts/ep_adopt.py`: Dynamic schema path.
- `scripts/ep_ops.py`: SLO parsing.
- `scripts/ep_session.py`: Porcelain renames.
- `scripts/ep_sync.py`: Dynamic root resolution.
- `scripts/ep_stack.py`: Polyglot stack definitions.
- `scripts/ep_ast.py`: AST structural rules.
- `scripts/audit-runner.py`: Mechanical checks.
- `AGENT.md`: Root agent manifest.
- `SKILL.md`: Skill definition.
- `references/core-directives.md`: Core directives.
- `templates/AGENT.template.md`: Manifest template.
- `references/optional-tooling.md`: Tooling contracts.
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
- `python3 -m unittest discover tests`
- `python3 scripts/ep.py verify`
- `python3 scripts/ep.py audit`

## 5. Invariants Preserved
- Zero external pip package dependencies.
- File size ceiling $\le 800$ lines.
- Complete dogfooding: EP-OS is 100% compliant with its own rules.
