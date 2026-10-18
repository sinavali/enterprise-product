# Enterprise Compliance & Governance Matrix

This specification establishes the formal mapping between EP-OS engineering standards and major regulatory frameworks (SOC 2 Type II, ISO/IEC 27001:2022, and GDPR / Data Privacy), as well as data classification, encryption, and retention policies.

---

## 1. Regulatory Framework Control Mapping

| Standard | Control Domain | EP-OS Mechanical Implementation | Verifying Gate |
|---|---|---|---|
| **SOC 2** | CC6.1 (Logical Access & Auth) | Granular permission scopes, authentication enforcement on all endpoints (Check 5.2). | `ep audit` (Dim 5) |
| **SOC 2** | CC6.6 (Vulnerability Management) | Automated SCA secret scanning, dependency CVE scanning, copyleft license audit. | `ep security scan`, `ep license check` |
| **SOC 2** | CC6.8 (Software Integrity) | 2-Pass PR Self-Audit, Human-only production merge gate, Conventional Commits. | `ep vcs sync-check`, `ep pr create-prod` |
| **SOC 2** | CC7.1 (Change Management) | Pre-implementation Change Surface (`CHANGE_SURFACE.md`), ADR requirement for Tier 2 deviations. | `ep surface validate`, `ep surface check-diff` |
| **SOC 2** | CC7.2 (Security Testing) | Value-driven test matrix ($\ge 95\%$ Domain, $\ge 80\%$ Adapter in real containers), failure path testing. | `ep run-many -t test`, `ep audit` (Dim 10) |
| **ISO 27001** | A.8.24 (Use of Cryptography) | Hardware-backed mobile encryption (Keychain/KeyStore), TLS in transit, KMS envelope encryption. | `ep audit` (Dim 5.5, 5.10) |
| **ISO 27001** | A.8.28 (Secure Coding) | Parameterized SQL queries, strict typing, null safety, zero swallowed catch blocks. | `ep ast scan`, `ep audit` (Dim 5.1, 8.1–8.3) |
| **ISO 27001** | A.8.31 (Separation of Environments)| 4-tier branch hierarchy (`main` $\to$ `test` $\to$ `stage` $\to$ `prod`), zero drift verification. | `ep vcs sync-check` |
| **GDPR** | Art. 25 (Privacy by Design) | PII redaction in structured logs, no sensitive data in metrics or URL parameters. | `ep audit` (Dim 6.5, 6.8), `scripts/audit-runner.py` |
| **GDPR** | Art. 32 (Security of Processing)| Immutable audit logging for state mutations, encrypted backups, ephemeral test containers. | `templates/audit-log-migration.sql` |

---

## 2. Data Classification Schema

Every domain entity and datastore schema must classify its fields under one of four data tiers:

```text
┌─────────────────────────────────────────────────────────────┐
│ Tier 1: PUBLIC                                              │
│ Marketing content, public product catalog, open API schemas │
├─────────────────────────────────────────────────────────────┤
│ Tier 2: INTERNAL BUSINESS                                   │
│ Internal service logs, operational metrics, task graphs     │
├─────────────────────────────────────────────────────────────┤
│ Tier 3: CONFIDENTIAL                                        │
│ Customer billing records, business transactions, tenant data│
├─────────────────────────────────────────────────────────────┤
│ Tier 4: RESTRICTED / PII / SENSITIVE                        │
│ Passwords, payment tokens, auth secrets, national IDs       │
└─────────────────────────────────────────────────────────────┘
```

### Invariants for Tier 4 (Restricted / PII):
1. **Zero Logging**: Must never be written to stdout, logs, metrics, or URL query parameters (`RULE-6.5-PII-LOGGING`).
2. **Encryption at Rest**: Must be stored using hardware-backed encryption or KMS-derived data encryption keys.
3. **Right to Erasure (GDPR Art. 17)**: Systems must support cryptographic erasure (destroying the entity's data key) or soft-delete scrubbing within 30 days of request.

---

## 3. Retention & Audit Trail Directives

1. **Transactional Audit Logging**: Mutating business operations (billing, permissions, status changes) must emit an immutable record into an `audit_events` table (see `templates/audit-log-migration.sql`) recording `actor_id`, `tenant_id`, `event_type`, `before_state`, `after_state`, and `timestamp_utc`.
2. **Log Retention Limits**: Application debug logs must be pruned after 30 days. Security and compliance audit logs must be retained immutably in tamper-evident storage for $\ge 365$ days.
3. **Database Restore Verification**: Stateful databases must execute periodic automated restore drills verifying that backups can be restored to clean ephemeral instances within declared RTO/RPO targets.
