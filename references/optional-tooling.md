# Optional Enterprise Tooling Registry

This document establishes the official registry of optional, specialized external engineering tools supported by EP-OS. EP-OS enforces a **zero-dependency core** in Python 3.12, but provides first-class dispatchers, templates, and graceful degradation for external tools when present in the host environment.

---

## 1. Tooling Policy & Degradation Contract

Every external tool supported by EP-OS conforms to these invariants:
1. **Zero-Dependency Fallback**: If the tool binary is not installed, EP-OS CLI subcommands **must never crash with unhandled tracebacks**. They must emit a clean diagnostic with installation instructions and exit cleanly (code 0 in informational/optional modes, code 1 only if explicitly invoked in strict verification).
2. **Deterministic Invocation**: Tools are invoked through explicit `ep <subcommand>` wrappers that normalize flags, output paths, and exit codes across polyglot projects.
3. **Hermetic Configuration**: Tool configuration files live in standard monorepo paths (`templates/`, `infra/`, or subproject roots).

---

## 2. Supported Tooling Registry

### 2.0 OCI Container Engines (`Podman` & `Docker`)
- **Binaries**: `podman` or `docker`
- **Purpose**: Powers Tier 1 Real-Container Integration Testing (ephemeral databases, brokers, caches) and containerized test runners (e.g. k6).
- **CLI Resolver**: `ep container [status|detect|info] [--json]`
- **Resolution & Prioritization Policy**:
  1. **Both Podman and Docker Installed**: Probes socket/daemon liveness. Prefers **Podman** as enterprise default (rootless, daemonless, zero commercial licensing fees). Automatically falls back to **Docker** if Docker daemon is actively running while Podman machine/socket is inactive.
  2. **Single Engine Installed**: Verifies liveness and selects the available engine.
  3. **Neither Installed**: Halts gracefully with platform-specific package installation commands (Ubuntu/Debian, RHEL/Fedora, Arch, macOS Homebrew, Windows WinGet / WSL2).
- **OS-Agnostic Setup Guide**:
  - **Linux**: Native and rootless (`sudo apt install podman` or `sudo dnf install podman`).
  - **macOS**: `brew install podman && podman machine init && podman machine start`.
  - **Windows (Recommended)**: Inside WSL2 (`sudo apt install podman`) or host `winget install RedHat.Podman-Desktop`.

### 2.1 Load & Stress Testing (`k6`)
- **Binary**: `k6`
- **Purpose**: High-throughput load, stress, spike, and soak testing of HTTP, gRPC, and WebSocket APIs.
- **CLI Wrapper**: `ep perf [--script <path>] [--vus <count>] [--duration <time>]`
- **Scaffolding Template**: `templates/perf-test.k6.js`
- **Fallback Behavior**:
  ```bash
  [INFO] 'k6' binary not found in PATH.
         Install k6: https://grafana.com/docs/k6/latest/set-up/install-k6/
         Example: brew install k6 / sudo apt install k6
  ```

### 2.2 Telemetry Pipeline & Routing (`OpenTelemetry Collector`)
- **Binary**: `otelcol` / `otelcol-contrib` (or container image `otel/opentelemetry-collector-contrib`)
- **Purpose**: Local and staging aggregation, batching, PII scrubbing, and forwarding of traces, metrics, and logs.
- **Configuration Template**: `templates/monitoring/otel-collector-config.template.yaml`
- **Validation**: `ep telemetry verify [--config <path>]`
- **Fallback Behavior**: Verifies YAML syntax using standard Python `json`/parser without requiring a running collector daemon.

### 2.3 FinOps & Cloud Cost Estimation (`Infracost`)
- **Binary**: `infracost`
- **Purpose**: Shift-left cloud infrastructure cost estimation on Terraform / OpenTofu pull request diffs.
- **CLI Dispatcher**: `ep finops check [--path <infra-dir>]`
- **Fallback Behavior**: Skips gracefully if unconfigured; provides actionable link to https://www.infracost.io.

### 2.4 Policy as Code (`Conftest` / `OPA`)
- **Binary**: `conftest` or `opa`
- **Purpose**: Structural policy verification across Kubernetes manifests, Terraform plans, and Dockerfiles using Rego policies.
- **CLI Dispatcher**: `ep policy test [--scope <dir>]`
- **Policy Directory**: `policy/*.rego`
- **Fallback Behavior**: Validates internal static policies via `ep iac verify` if Conftest is not installed.

### 2.5 Chaos Engineering (`Chaos Mesh` / `LitmusChaos`)
- **Specification**: Pure declarative Kubernetes Custom Resource Definitions (CRDs) or ephemeral failure scripts.
- **Template**: `templates/CHAOS_EXPERIMENT.template.md`
- **Execution**: Verified via structural YAML/schema validation during CI; executed during scheduled Game Days.

---

## 3. Tool Installation Reference Cheatsheet

| Tool | Linux (Apt / Shell) | macOS (Homebrew) | Container Alternative |
|---|---|---|---|
| **k6** | `sudo gpg -k && sudo apt-get install k6` | `brew install k6` | `podman run -i grafana/k6 run - <script.js` |
| **Infracost** | `curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh \| sh` | `brew install infracost` | `infracost/infracost:ci-latest` |
| **Conftest** | `wget -O - https://github.com/open-policy-agent/conftest/releases/download/v0.56.0/conftest_0.56.0_Linux_x86_64.tar.gz \| tar -xz` | `brew install conftest` | `openpolicyagent/conftest:latest` |
| **OTel Collector**| Native download from `open-telemetry/opentelemetry-collector-releases` | `brew install opentelemetry-collector` | `podman run -p 4317:4317 -p 4318:4318 otel/opentelemetry-collector-contrib` |
