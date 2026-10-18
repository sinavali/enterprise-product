# Incident Postmortem: [INCIDENT_TITLE]

**Incident Reference**: `INC-{{YYYYMMDD}}-{{ID}}`  
**Date**: `{{YYYY-MM-DD}}`  
**Severity**: `SEV-1` / `SEV-2` / `SEV-3`  
**Incident Commander**: `{{NAME}}`  
**Authors**: `{{TEAM_NAMES}}`  
**Status**: `Draft` / `Reviewed` / `Action Items In Progress` / `Closed`

---

## 1. Executive Summary
*Provide a 2-3 paragraph high-level overview describing what happened, the customer/business impact, and what resolved the issue.*

- **Start Time**: `YYYY-MM-DDTHH:MM:SSZ`
- **End Time**: `YYYY-MM-DDTHH:MM:SSZ`
- **Time to Detect (TTD)**: `X minutes`
- **Time to Mitigate (TTM)**: `Y minutes`
- **Customer Impact**: `e.g. 1,420 users experienced 504 errors on checkout; $12,000 delayed transactions.`

---

## 2. Impact Breakdown
- **User Experience**: [What did the end user observe?]
- **Error Budget Consumption**: [e.g. Consumed 42% of 30-day availability error budget]
- **Data Integrity Impact**: [Any data corruption, loss, or duplicate processing? If none, state "Zero data loss / zero corruption."]
- **Security & Compliance Impact**: [Any breach of confidential data or PII exposure? If none, state "No unauthorized data disclosure."]

---

## 3. Incident Timeline (UTC)
*All times must be recorded in ISO-8601 UTC with Z suffix.*

- `YYYY-MM-DDTHH:MM:SSZ` - **Change Deployment**: Release `vX.Y.Z` deployed to production via CI/CD pipeline.
- `YYYY-MM-DDTHH:MM:SSZ` - **First Alert Fired**: Alertmanager triggered `ServiceHigh5xxRate` on channel `#alerts-prod`.
- `YYYY-MM-DDTHH:MM:SSZ` - **Incident Declared**: On-call engineer acknowledged alert, declared `SEV-1`, and created bridge.
- `YYYY-MM-DDTHH:MM:SSZ` - **Root Cause Hypothesized**: Log analysis indicated connection pool exhaustion following migration.
- `YYYY-MM-DDTHH:MM:SSZ` - **Mitigation Executed**: Rollback initiated to `vX.Y.Z-1`.
- `YYYY-MM-DDTHH:MM:SSZ` - **Traffic Stabilized**: p95 latency returned to normal ($\le 85\text{ms}$), 5xx errors dropped to 0.
- `YYYY-MM-DDTHH:MM:SSZ` - **Incident Closed**: System verified stable across 30 minutes of peak traffic.

---

## 4. Root Cause Analysis (5 Whys)

1. **Why did users experience 504 Gateway Timeouts?**  
   The application instances failed to respond to ingress requests within the 10-second timeout.
2. **Why did the application fail to respond?**  
   All worker threads were blocked waiting to acquire a connection from the database connection pool.
3. **Why was the connection pool exhausted?**  
   A new database query introduced in the release lacked an index on `tenant_id`, triggering full table scans that held connections for 4,500ms instead of 4ms.
4. **Why was the unindexed query deployed to production?**  
   The performance test suite in CI ran against a synthetic database with only 100 rows, masking the table scan cost.
5. **Why did CI test against non-representative data volume?**  
   The ephemeral container test fixture lacked a database seed benchmark representing production cardinality.

---

## 5. What Went Well / What Went Poorly / Where We Got Lucky

### What Went Well
- Automated alert fired within 90 seconds of deployment.
- Rollback executed cleanly without requiring database schema down-migrations.
- Graceful degradation prevented total cluster crash.

### What Went Poorly
- Missing query index was not flagged by static linters or CI queries.
- Dashboard metric cardinality was too coarse to isolate which tenant query was saturating the pool.

### Where We Got Lucky
- Occurred during off-peak traffic window, limiting total impacted requests.

---

## 6. Corrective Action Items (No Blame, High Accountability)

| Action Item | Type | Owner | Target Date | Tracking Ticket |
|---|---|---|---|---|
| Add missing index on `tenant_id` to migration | Preventative | `@engineer1` | `YYYY-MM-DD` | `TICKET-101` |
| Add `EXPLAIN ANALYZE` static AST / query plan lint rule to CI | Preventative | `@platform` | `YYYY-MM-DD` | `TICKET-102` |
| Scale ephemeral container test fixtures with realistic cardinality ($10^5$ rows) | Testing | `@qa-team` | `YYYY-MM-DD` | `TICKET-103` |
| Implement connection pool acquisition timeout metric and alert | Observability| `@observability`| `YYYY-MM-DD`| `TICKET-104` |
| Update operational runbook with connection pool saturation diagnosis | Process | `@oncall` | `YYYY-MM-DD` | `TICKET-105` |
