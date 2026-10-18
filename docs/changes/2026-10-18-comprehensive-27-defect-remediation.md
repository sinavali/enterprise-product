---
title: "Change Surface: Comprehensive 27-Defect Remediation and Enterprise Hardening"
author: "Antigravity"
created_date: "2026-10-18"
target_branch: "main"
risk_level: "MEDIUM"
affected_projects:
  - "root"
---

# Change Surface: Comprehensive 27-Defect Remediation and Enterprise Hardening

## 1. Intent & Business Rationale
Remediate all 27 validated defects discovered during the exhaustive architectural audit:
1. Blast-radius bypass on triple-dot (`...`) git diff ranges (`DEFECT-01`).
2. Parallel task execution order violations (`DEFECT-02`).
3. Monorepo-wide cyclic deadlocks on `^` targets and `KeyError` on cross-project targets (`DEFECT-03`, `DEFECT-09`).
4. Secret scanner blind spot on paths with `"test"` substring (`DEFECT-04`).
5. False-pass in `ep vcs sync-check` on missing base/remote branches (`DEFECT-05`).
6. Mechanical PR auto-merge disable (`DEFECT-06`).
7. Real ADR existence check in Expand/Contract migration gate (`DEFECT-07`).
8. Connect `.ep/baseline.json` debt ratchet to `ep audit` via `--baseline` (`DEFECT-08`).
9. Missing subcommands (`milestone status`, `hooks run`, `telemetry`, `finops`, `policy`) and flag aliases (`DEFECT-10`, `DEFECT-11`).
10. Release note generation and signed tags (`DEFECT-12`).
11. Comprehensive `ep verify` with `--root` propagation (`DEFECT-13`).
12. Scaffolding real target commands for all 13 languages instead of `echo` stubs (`DEFECT-14`).
13. Base64 & unquoted YAML secret detection (`DEFECT-15`).
14. Migration check `--diff` fallback isolation (`DEFECT-16`).
15. Shannon entropy calculation and real lockfile dependency SBOM (`DEFECT-17`).
16. Standard execution timeouts across subprocess calls (`DEFECT-18`).
17. Semantic keyword matching for Tier 1 overrides (`DEFECT-19`).
18. Diagnostic reporting for malformed `project.json` files (`DEFECT-20`).
19. Dynamic workspace root resolution (`DEFECT-21`).
20. Dynamic relative schema path calculation in brownfield adoption (`DEFECT-22`).
21. Graceful error handling in SLO burn rate parsing (`DEFECT-23`).
22. Git porcelain rename handling (`DEFECT-24`).
23. Windows portability in `infer_scope` and `ep preflight` (`DEFECT-25`).
24. Monorepo-wide project discovery in `ep codeowners` (`DEFECT-26`).
25. Automated linters for UTC storage and Transactional Outbox invariants (`DEFECT-27`).

## 2. Affected Monorepo Projects & Profiles
| Project Path | Architectural Profile | Responsibility in this Change |
|---|---|---|
| `root` | Root Governance | Core CLI, runner, security, VCS, scaffolding, templates, tests |

## 3. Code Surface (Targeted Symbols & Files)

### Added Files
- `docs/changes/2026-10-18-comprehensive-27-defect-remediation.md`: Change Surface specification.
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
- `scripts/ep.py`: Fix git diff range parsing, ADR verification in migration check, baseline flag forwarding, missing subcommands, flag aliases, release notes, comprehensive verify, porcelain renames, and timeouts.
- `scripts/ep_runner.py`: Implement level-wave parallel execution, scoped `^` dependency resolution, cross-project target syntax, and diagnostic JSON error handling.
- `scripts/ep_hooks.py`: Direct hook execution fallback for pre-commit and pre-push without installed git hooks.
- `scripts/ep_security.py`: Bound secret scanner path exemptions, Base64/YAML secret matching, Shannon entropy calculation, lockfile SBOM generation.
- `scripts/ep_vcs.py`: Strict base branch check, remote tracking branch inspection, mechanical PR auto-merge disable.
- `scripts/ep_scaffold.py`: Wire `STACK_DEFINITIONS` commands into `cmd_init` for all 13 languages, portable shell preflight.
- `scripts/ep_adopt.py`: Dynamic relative schema path, Windows path normalization in scope inference.
- `scripts/ep_ops.py`: Exception handling in SLO burn rate parsing, unified `discover_projects` in `cmd_codeowners`.
- `scripts/ep_session.py`: Git porcelain rename handling.
- `scripts/ep_sync.py`: Dynamic workspace root resolution.
- `scripts/ep_stack.py`: Polyglot stack definitions and dependency detection.
- `scripts/ep_ast.py`: AST rules for UTC timestamp conventions and Transactional Outbox usage.
- `scripts/verify-agent-manifests.py`: Semantic stem/keyword matching for Tier 1 banned overrides.
- `scripts/audit-runner.py`: Mechanical checks for UTC storage convention and transactional outbox.
- `templates/AGENT.template.md`: Manifest template with operational fields.
- `AGENT.md`: Document enhanced commands and invariants.
- `SKILL.md`: Document CLI commands and subcommands.
- `references/optional-tooling.md`: Document tooling integrations.
- `references/core-directives.md`: Document Inviolable standards.
- `references/audit-taxonomy.md`: Audit taxonomy updates.
- `references/compliance-matrix.md`: Compliance mapping.
- `references/deep-observability.md`: Deep observability reference.
- `references/exclusions.md`: Exclusion rationales.
- `.cursorrules`: Manifest projection.
- `.windsurfrules`: Manifest projection.
- `CLAUDE.md`: Manifest projection.
- `tests/test_verify_agent_manifests.py`: Manifest verification tests.

## 4. Test Surface

### Unit & Domain Suites
- `tests/test_defect_remediations.py`: Tests covering all 27 remediated defects.
- Full test suite: `python3 -m unittest discover tests`.

## 5. Invariants Preserved
- Zero external pip package dependencies (pure Python standard library).
- 100% backward compatibility with all profiles and commands.
- All 10 Tier 1 Enterprise Inviolables strictly preserved.

## 6. Risk Matrix
- **Risk Level**: MEDIUM. Deep mechanical hardening across CLI and governance; non-breaking to existing valid profiles.
- **Rollback Strategy**: Git commit revert.
