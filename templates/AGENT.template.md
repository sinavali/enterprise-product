---
project_name: "[project-folder-name]"
profile: "A"                          # A (Backend/Core) | B (Web) | C (Mobile) | D (Shared Contracts)
stack: "[runtime-and-language, e.g. node-ts-20 | go-1.22 | dotnet-8 | flutter-3.24]"
scope: "backend"                      # backend | frontend | mobile | shared
owner: "[team-or-domain-owner]"
tier_overrides: []
dr:
  rto: "1h"
  rpo: "15m"
slo:
  tier: "tier-1"
  availability_target: "0.999"
resources:
  cpu_limit: "1000m"
  memory_limit: "1Gi"
# Example tier_override entry:
#  - rule: "domain-test-coverage"
#    adr_reference: "docs/adr/0014-example.md"
#    justification: "Calculations covered by mathematical property tests at 90% branch"
---

# Project Agent Manifest: [project-name]

## 1. Scope & Business Intent
[Define the domain responsibility, bounded context, and primary purpose of this project within the monorepo ecosystem.]

## 2. Architectural Profile & Boundaries
- **Profile**: [A | B | C | D]
- **Primary Inputs**: [e.g., Inbound REST API, gRPC endpoints, Event bus listeners, UI User Input]
- **Allowed Outbound Dependencies**:
  - `libs/core-contracts`
  - [Ephemeral datastore / cache]
- **Forbidden Dependencies**:
  - Direct imports from sibling services or private internal layers of other packages.
  - Framework imports into `src/domain/` (Tier 1 Inviolable).

## 3. Local Nx Target Delegations
- `nx lint [project-name]` -> `[native lint command]`
- `nx test [project-name]` -> `[native test command with coverage]`
- `nx build [project-name]` -> `[native build / compile command]`
- `nx audit [project-name]` -> `[native security / dependency audit command]`

## 4. Test & Verification Rules
- Pure domain unit tests located in `tests/unit/` (Fast, in-process, zero I/O).
- Integration tests located in `tests/integration/` utilizing **real ephemeral containers** (Testcontainers/Podman).
- In-memory SQL emulators (e.g. SQLite for PostgreSQL) are strictly forbidden (Tier 1 Inviolable).
- Timestamp handling must strictly store and exchange UTC ISO-8601 (Tier 1 Inviolable).
- Anti-MVP & Zero-Stub Mandate: No prototypes, stubs, or deferred hardening; all code must be production-ready (Tier 1 Inviolable).
- Single-Turn Ingestion: Before editing, run `ep pack --surface` to ingest targeted files in one turn. Sequential one-by-one file reading across turns is forbidden.

## 5. Approved Tier 2 Deviations
| Rule | Justification | ADR Reference |
|---|---|---|
| *(None by default)* | - | - |

## 6. Project Invariants
- [Invariant 1: e.g., Aggregate roots enforce transactional boundary]
- [Invariant 2: e.g., All external HTTP calls configure explicit 5s timeout]
- [Invariant 3: Zero-stub guarantee: all error paths, retries, and edge cases fully implemented]
