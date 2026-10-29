# Enterprise Documentation System

This specification incorporates and elevates the core documentation capabilities into the `enterprise-product` engineering system. Documentation is an active, machine-verifiable contract that leads code implementation.

---

## 1. The Core Doctrine: Docs Lead, Code Follows

In an enterprise monorepo, code is never written into a void:
```text
1. Change Request / Task
     │
     ▼
2. Impact Graph Analysis (Trace affected projects, contracts, dependencies)
     │
     ▼
3. CHANGE SURFACE Declaration (`CHANGE_SURFACE.md`)
     │
     ▼
4. Mechanical Validation (`python3 scripts/validate-change-surface.py`)
     │
     ▼
5. Implementation & Value-Driven Tests (Red -> Green -> Refactor)
     │
     ▼
6. 2-Pass PR Self-Audit vs CHANGE SURFACE
```

No non-trivial modification to code, configuration, or contracts is permitted without an approved, validated **Change Surface**.

---

## 2. The Change Surface Specification

A Change Surface bounds the scope of work, prevents scope creep, and informs reviewers of the exact blast radius.

### 2.1 Change Surface Schema & Storage Paths
To prevent branch collision across concurrent features, a Change Surface may be stored in one of two supported formats:
1. **Versioned Archive Path (Recommended)**: `docs/changes/YYYYMMDD-<branch-slug>.md`
2. **Local Root Staging**: `CHANGE_SURFACE.md` (at repo root, or symlinked)
3. **PR Embedded Contract**: Formatted directly within the Pull Request description matching `templates/PR_CONTRACT.template.md`.

Every Change Surface must declare:
1. **Metadata**: Title, author/agent, created date, target branch, risk level.
2. **Intent & Problem Statement**: Precise business rationale and problem description.
3. **Affected Projects**: Monorepo packages affected (`apps/*`, `services/*`, `libs/*`) and their Architectural Profiles.
4. **Code Surface**: Explicit list of files and code symbols (classes, functions, interfaces) targeted for addition or modification.
5. **Test Surface**: Exact test files and suites verifying the change (Unit, Ephemeral Container Integration, Failure paths).
6. **Invariants Preserved**: Core business rules and architectural constraints that must remain unbroken (including Tier 1 Inviolables and structural limits).
7. **Risk Matrix & Rollback Strategy**: Identified risks, blast radius, and recovery plan.

### 2.2 Mechanical Validation
The script `scripts/validate-change-surface.py` verifies:
- Presence of all required sections.
- Non-empty Code Surface and Test Surface.
- Existence of affected project references within the monorepo.
- Prevention of unconstrained wildcards (`*`) without path scoping.
- Resolves files at root (`CHANGE_SURFACE.md`) or within `docs/changes/`.

### 2.3 Mechanical Archival & Template Reset Lifecycle
To prevent `CHANGE_SURFACE.md` from accumulating stale modifications across branches and PRs:
1. **Mechanical Archival (`ep surface archive`)**:
   - Parses the active Change Surface, extracts its ISO date and title slug.
   - Saves a persistent versioned snapshot at `docs/changes/YYYY-MM-DD-<slug>.md`.
   - Atomically resets the root `CHANGE_SURFACE.md` to a clean baseline template (`CLEAN_SURFACE_TEMPLATE`).
2. **Auto-Archiving on New Initialization (`ep surface init`)**:
   - When initializing a new Change Surface via `ep surface init`, any existing populated surface is automatically detected and archived into `docs/changes/` before the new surface is scaffolded.
3. **Pre-Prod Promotion Gate (`ep pr create-prod`)**:
   - Before opening a production promotion PR, `ep pr create-prod` automatically triggers `ep surface archive` to ensure zero stale active change surfaces reach production.

---

## 3. Architecture Decision Records (ADRs)

An ADR captures an important architectural decision, along with its context, alternatives considered, and consequences.

### 3.1 When is an ADR Mandatory?
An ADR must be created in `docs/adr/NNNN-<slug>.md` whenever a change:
1. Deviates from a **Tier 2 Strong Default** (e.g., altering coverage thresholds, waiving a port-adapter interface).
2. Introduces a new database, message broker, cloud service, or external protocol.
3. Alters the architectural profile of a project (e.g., transitioning from Profile B to Profile A).
4. Deprecates or introduces a major breaking change to shared API contracts (Profile D).
5. Modifies core cross-cutting patterns (authentication, distributed tracing, encryption).

### 3.2 ADR Structure
Every ADR conforms to `templates/ADR.template.md` and contains:
- Number, Title, Date, Status (`Proposed`, `Accepted`, `Superseded`, `Rejected`).
- Context & Problem Statement.
- Decision Drivers & Constraints.
- Considered Options & Trade-Offs.
- Decision Outcome & Justification.
- Positive, Negative, and Neutral Consequences.
- Compliance & Verification Plan.

---

## 4. File-Level Documentation & Inline Standards

- **Two Audiences, Two Files**:
  - `README.md`: Written for human developers; covers onboarding, architecture overview, and developer commands.
  - `AGENT.md`: Written for AI agents; specifies strict machine-readable rules, invariants, and local toolchain targets.
- **Complex Domain Logic**: For complex state machines, cryptographic algorithms, or financial calculation modules, code comments must explain *why* an invariant exists, not just *what* the syntax does.
- **Companion Documentation (`<filename>.md`)**: If a domain aggregate root requires extensive documentation exceeding reasonable file headers, place a companion markdown document alongside it (`order_aggregate.md`) referencing domain specifications.

---

## 5. Documentation Drift Detection

Documentation drift is treated as a software defect during audits:
- If a pull request modifies domain interfaces, data schemas, or configuration without updating the corresponding documentation, Dimension 9 of the Enterprise Audit will flag a `blocking` finding.
- The CI pipeline runs doc validation checks to ensure all links and ADR numbers are strictly monotonic and unbroken.

---

## 6. Enterprise Template & Asset Catalog

The `templates/` directory provides standardized, machine-validated scaffolding assets for all EP-OS workflows:

| Category | Template Path | Purpose & Profile Standard |
|---|---|---|
| **Governance** | `templates/CHANGE_SURFACE.template.md` | Pre-implementation blast radius and invariant bounding contract |
| **Governance** | `templates/NEED_CLARIFICATION.template.md` | Formal ambiguity tracking and 14-day aging escalation |
| **Governance** | `templates/AUDIT_REPORT.template.md` | 10-Dimension Enterprise Audit scorecard and findings log |
| **Governance** | `templates/PR_CONTRACT.template.md` | 2-Pass PR Self-Audit checklist and merge gate agreement |
| **Governance** | `templates/ADR.template.md` | Architecture Decision Record schema for Tier 2 deviations |
| **Governance** | `templates/AGENT.template.md` | Subproject-level `AGENT.md` governance manifest |
| **Operations** | `templates/RUNBOOK.template.md` | Operational service runbook (health probes, alerts, rollback) |
| **Operations** | `templates/POSTMORTEM.template.md` | Blameless incident postmortem and root-cause analysis |
| **Operations** | `templates/THREAT_MODEL.template.md` | STRIDE security threat modeling and data flow analysis |
| **Operations** | `templates/CHAOS_EXPERIMENT.template.md` | Chaos Mesh and resilience verification hypothesis protocol |
| **Operations** | `templates/perf-test.k6.js` | k6 load, stress, and latency distribution test script |
| **Telemetry** | `templates/monitoring/slo.template.yaml` | Service Level Objective (SLO/SLI) target definition |
| **Telemetry** | `templates/monitoring/alerts.template.yaml` | Multi-window multi-burn-rate Prometheus alerting rules |
| **Telemetry** | `templates/monitoring/otel-collector-config.template.yaml` | OpenTelemetry Collector pipeline and processor config |
| **Profiles** | `templates/profiles/node-service-project.json` | Profile A (Backend) Node.js/TypeScript Nx contract |
| **Profiles** | `templates/profiles/go-service-project.json` | Profile A (Backend) Go/Hexagonal Nx contract |
| **Profiles** | `templates/profiles/rust-service-project.json` | Profile A (Backend) Rust/Cargo Nx contract |
| **Profiles** | `templates/profiles/python-service-project.json` | Profile A (Backend) Python/Pytest Nx contract |
| **Profiles** | `templates/profiles/next-web-project.json` | Profile B (Web) Next.js/React/A11y Nx contract |
| **Profiles** | `templates/profiles/flutter-mobile-project.json` | Profile C (Mobile) Flutter/Dart/BLoC Nx contract |
| **Profiles** | `templates/profiles/contracts-project.json` | Profile D (Contracts) OpenAPI/Protobuf codegen contract |
| **Database** | `templates/audit-log-migration.sql` | Append-only, tamper-evident audit logging schema (Check 4.8) |
| **Database** | `templates/outbox-migration.sql` | Transactional outbox event publishing table (Check 4.5) |
| **CI/CD** | `templates/ci-workflow.template.yml` | GitHub Actions multi-tier promotion workflow |
| **Hooks** | `templates/pre-commit-config.template.yaml` | Native pre-commit mechanical gate configuration |
