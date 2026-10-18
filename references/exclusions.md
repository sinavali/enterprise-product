# Deliberate Architectural Exclusions

This specification formally records engineering concepts from the canonical enterprise catalog that are **deliberately excluded from mandatory repository-level gate enforcement** within the EP-OS engineering operating system, along with the principled architectural rationale for each exclusion.

---

## 1. Vendor Viability & Commercial Support (Term 62)

- **Definition**: Evaluating commercial third-party vendor financials, corporate viability, software license agreements (SLAs), escrow provisions, and long-term business roadmap.
- **Classification**: `EXCLUDED (deliberate)`
- **Architectural Rationale**:
  - Corporate vendor viability evaluations, procurement negotiations, and business credit risk assessments are business operations conducted by legal, procurement, and vendor management departments.
  - They cannot be deterministically verified or evaluated by git-based CLI tools, AST pattern matchers, unit test runners, or CI pipelines.
  - **EP-OS Technical Scope**: EP-OS enforces *technical* vendor decoupling via Hexagonal Architecture (Profile A Secondary Ports) and Sovereign Infrastructure preferences (`references/core-directives.md` Section 3.1), guaranteeing that any vendor can be swapped without rewriting business domain logic. Commercial viability itself remains outside repository governance.

---

## 2. Continuous Kernel Profiling (Term 74)

- **Definition**: Always-on, fleet-wide CPU, memory allocation, and goroutine/thread profiling using continuous profiling agents (e.g. Pyroscope, Parca, continuous pprof) generating continuous flame graphs.
- **Classification**: `EXCLUDED (deliberate)` from mandatory gates; supported as an optional runtime integration.
- **Architectural Rationale**:
  - Continuous profiling requires persistent host-level background daemon processes (`pyroscope-agent`, `parca-agent`), specialized kernel privileges, and external centralized time-series storage backends.
  - EP-OS is a git monorepo engineering operating system governing development, testing, and CI/CD quality gates. Imposing mandatory continuous profiling gates on local development or CI unit test runs would introduce heavy runtime overhead, external infrastructure dependencies, and flaky network calls.
  - **EP-OS Alternative**: Supported as an **opt-in runtime profile** in `references/optional-tooling.md`. Projects requiring continuous profiling may configure exporters in their runtime deployments without blocking repository CI gates.

---

## 3. eBPF Observability (Term 81)

- **Definition**: Kernel-level dynamic tracing and networking telemetry using extended Berkeley Packet Filter programs (e.g. Cilium, Pixie, Tetragon) attached to kernel probes (`kprobes`) and tracepoints without code changes.
- **Classification**: `EXCLUDED (deliberate)` from mandatory gates; supported as an optional platform capability.
- **Architectural Rationale**:
  - eBPF programs require root privileges (`CAP_SYS_ADMIN` or `CAP_BPF`), a modern Linux kernel ($\ge 5.4$) compiled with `CONFIG_DEBUG_INFO_BTF=y`, and direct access to kernel subsystem memory.
  - eBPF cannot execute inside unprivileged containerized CI environments (GitHub Actions standard runners, Docker-in-Docker), on macOS developer workstations, or within Windows environments. Mandating eBPF gates would violate universal multi-platform agnosticism.
  - **EP-OS Alternative**: Application-level telemetry is standardized through vendor-neutral **OpenTelemetry (OTel)** APIs (`references/deep-observability.md`), which run portably across all platforms, languages, and container runtimes without kernel dependencies. Teams with sovereign eBPF Kubernetes clusters can run eBPF agents alongside standard OTel collectors as documented in `references/optional-tooling.md`.
