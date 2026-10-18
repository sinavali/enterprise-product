---
title: "Change Surface: Smart OCI Container Engine Resolution"
author: "Antigravity"
created_date: "2026-10-18"
target_branch: "main"
risk_level: "LOW"
affected_projects:
  - "root"
---

# Change Surface: Smart OCI Container Engine Resolution

## 1. Intent & Business Rationale
Implement an OS-agnostic, intelligent OCI container engine resolver for EP-OS.
Resolves user environments dynamically:
1. Detects both Podman and Docker across Linux, macOS, and Windows.
2. If both exist, probes socket/daemon liveness and selects the optimal engine:
   - Podman preferred by default (rootless, daemonless, zero commercial licensing restrictions).
   - Graceful fallback to Docker if Docker is actively running while Podman is stopped.
3. If only one exists, uses the available engine.
4. If neither exists, halts cleanly with platform-specific installation commands (and agent-executable instructions).
5. Provides a standardized CLI command: `ep container [status|detect|info] [--json]`.

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `root` | Root Governance | Container engine resolution, CLI command registration, reference docs, tests |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `docs/changes/2026-10-18-smart-container-engine-resolution.md`: Change Surface specification.
- `tests/test_container_engine_resolver.py`: Automated test suite for container detection, liveness, and prioritization.
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
- `tests/test_audit_gap_closure.py`: Automated verification suite for closed audit gaps.
- `tests/test_enterprise_catalog_enforcement.py`: Test suite for enterprise catalog enforcement.

### Modified Files
- `scripts/ep_ops.py`: Implement `resolve_container_engine` and `cmd_container`.
- `scripts/ep.py`: Register and dispatch `container` CLI subcommand.
- `scripts/audit-runner.py`: Heuristic scanners and runbook check.
- `scripts/ep_adopt.py`: Brownfield adoption schema and audit target injection.
- `scripts/ep_ast.py`: AST pattern rules for enterprise boundaries.
- `scripts/ep_hooks.py`: Add `ep verify` execution to native pre-push hook.
- `scripts/ep_scaffold.py`: Wire Profile A templates into scaffolding router.
- `scripts/ep_security.py`: Secret scanning and IaC static analysis commands.
- `scripts/ep_stack.py`: Standard audit target definitions for 13 supported languages.
- `scripts/verify-agent-manifests.py`: Add `human-only-prod` to `TIER_1_BANNED_OVERRIDES`.
- `references/optional-tooling.md`: Document container engine resolution hierarchy and OS installation instructions.
- `references/core-directives.md`: Document smart container engine resolver in Rule 3.
- `references/audit-taxonomy.md`: Audit checks extension.
- `references/compliance-matrix.md`: Compliance framework mapping.
- `references/deep-observability.md`: Deep observability reference guide.
- `references/exclusions.md`: Enterprise catalog exclusion decisions.
- `templates/AGENT.template.md`: Manifest template with operational fields.
- `AGENT.md`: Document `ep container` CLI command and smart resolution.
- `SKILL.md`: Update CLI command reference.
- `.cursorrules`: Manifest projection.
- `.windsurfrules`: Manifest projection.
- `CLAUDE.md`: Manifest projection.
- `tests/test_verify_agent_manifests.py`: Manifest verification tests.

## 4. Test Surface

### Unit & Domain Suites
- `tests/test_container_engine_resolver.py`: Test both engines present, one present, none present, socket liveness fallback, and CLI output formats.
- Full test suite: `python3 -m unittest discover tests`.

## 5. Invariants Preserved
- Tier 1 Real-Container Invariant preserved (zero mock databases).
- Zero external pip package dependencies (pure Python standard library).
- 100% backward compatibility with all profiles and commands.

## 6. Risk Matrix
- **Risk Level**: LOW. Centralizes and enhances existing container detection; non-breaking.
- **Rollback Strategy**: Git commit revert.
