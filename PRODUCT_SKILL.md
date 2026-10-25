# Product Operating Skill Manifest: Monorepo Governance

This is the **tailored operating skill** for this product monorepo. Agents working on this codebase must strictly observe the localized rules and profile mappings below.

---

## 1. Monorepo Project & Profile Matrix

| Project Name | Project Path | Architectural Profile | Scope |
|---|---|---|---|
| `enterprise-product` | `.` | **Profile D** | `shared` |

---

## 2. Active Architectural Profiles & Invariants

### Profile D (Shared Contracts & Core Libraries)
- Pure stateless schemas, serializers, or utility functions.
- Zero dependencies on concrete services or application code.
- Semantic versioning and backward-compatible schema evolutions.

---

## 3. High-Velocity Single-Turn Ingestion Mandate (P0)

AI agents are **strictly forbidden from reading files one by one with sequential tool calls**.
Before modifying code:
1. Ingest all target files in a single turn:
   ```bash
   python3 scripts/ep.py pack --surface
   ```
2. For diff-based modifications:
   ```bash
   python3 scripts/ep.py pack --diff
   ```

---

## 4. Local Execution & Mechanical Verification

- **Run target**: `python3 scripts/ep.py run <project>:<target>`
- **Verify blast radius**: `python3 scripts/ep.py surface check-diff --strict`
- **Verify compliance**: `python3 scripts/ep.py verify`
- **10-Dimension Audit**: `python3 scripts/ep.py audit`
- **Run test suite**: `python3 -m unittest discover tests` (or native project test runner)
