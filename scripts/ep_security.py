#!/usr/bin/env python3
"""
ep_security.py — Secret Scanning & License Compliance Gatekeeper for EP-OS
Zero-dependency static security engine scanning git diffs, staged commits,
and repository trees for leaked credentials, high-entropy secrets,
and copyleft license contagion.
"""

import argparse
import collections
import datetime
import json
import math
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


def shannon_entropy(data: str) -> float:
    """Calculates the Shannon entropy (bits per character) of a string."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    counts = collections.Counter(data)
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


# Comprehensive credential & secret detection regexes
SECRET_PATTERNS = [
    (
        "AWS Access Key ID",
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "Critical AWS IAM credential detected.",
    ),
    (
        "GitHub Personal Access Token",
        re.compile(r"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}|github_pat_[A-Za-z0-9_]{82})\b"),
        "Personal GitHub authentication token detected.",
    ),
    (
        "Slack Bot/User Token",
        re.compile(r"\b(xox[baprs]-[0-9A-Za-z_-]{10,})\b"),
        "Slack workspace API token detected.",
    ),
    (
        "Private Key Header",
        re.compile(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----"),
        "Unencrypted cryptographic private key block detected.",
    ),
    (
        "Stripe API Secret / Webhook Key",
        re.compile(r"\b((?:sk|whsec)_(?:test|live)_[0-9a-zA-Z]{24,})\b"),
        "Stripe payment gateway secret detected.",
    ),
    (
        "Database URI with Embedded Credentials",
        re.compile(r"\b(postgres(?:ql)?|mysql|mongodb|redis):\/\/[^:\/\s]+:([^@\/\s]{4,})@[^:\/\s]+"),
        "Database connection string with plain text credentials detected.",
    ),
    (
        "Hardcoded Secret / API Key Assignment",
        re.compile(r"\b(api_key|apikey|secret_key|secretkey|auth_token|client_secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\./+=]{20,})['\"]?", re.IGNORECASE),
        "High-entropy hardcoded secret assignment detected.",
    ),
    (
        "AWS Secret Access Key",
        re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"),
        "High-entropy AWS Secret Access Key or Base64 secret detected.",
    ),
]

EXCLUDED_SCAN_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "dist-next",
    ".next",
    "build",
    ".cache",
    ".venv",
    ".nx",
    "coverage",
    "__pycache__",
    "obj",
    "bin",
    "target",
}

COPYLEFT_LICENSES = {
    "GPL",
    "GPL-2.0",
    "GPL-3.0",
    "AGPL",
    "AGPL-1.0",
    "AGPL-3.0",
    "LGPL-2.1",
    "LGPL-3.0",
    "SSPL",
    "EUPL",
    "CC-BY-NC",
    "BUSL",
}


def mask_secret(secret_str: str) -> str:
    if len(secret_str) <= 8:
        return "****"
    return secret_str[:4] + "*" * (len(secret_str) - 8) + secret_str[-4:]


def is_test_path(filename: str) -> bool:
    norm_fn = filename.replace("\\", "/").lower()
    is_test_dir = bool(re.search(r"(^|/)(tests?|specs?|fixtures?|mocks?|__tests?__)(/|$)", norm_fn))
    is_test_file = bool(re.search(r"\.(spec|test)\.[a-zA-Z0-9]+$", norm_fn))
    is_template = bool(re.search(r"\.template\.[a-zA-Z0-9]+$", norm_fn) or re.search(r"(^|/)templates?/", norm_fn))
    return is_test_dir or is_test_file or is_template


def scan_text_for_secrets(text: str, filename: str = "") -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    # Skip test files and template files from false-positive tripping on placeholders (DEFECT-04)
    if is_test_path(filename):
        return findings

    for line_num, line in enumerate(text.splitlines(), start=1):
        for name, pattern, description in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                matched_val = match.group(0)
                # Filter out obvious templates, environment variable references, and placeholders
                if any(p in matched_val.upper() for p in ["EXAMPLE", "PLACEHOLDER", "YOUR_", "DUMMY", "TEST", "ENV[", "PROCESS.ENV", "DEV-", "CONFIG."]):
                    continue
                # For AWS Secret Access Key or general Base64, require Shannon entropy >= 4.5 (DEFECT-17)
                if name == "AWS Secret Access Key":
                    ent = shannon_entropy(matched_val)
                    if ent < 4.5:
                        continue
                findings.append({
                    "file": filename,
                    "line": line_num,
                    "type": name,
                    "description": description,
                    "matched": mask_secret(matched_val),
                })
    return findings


def scan_staged_diff() -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    cmd = ["git", "diff", "--cached", "--unified=0"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
    except Exception:
        return findings
    if res.returncode != 0 or not res.stdout.strip():
        return findings

    current_file = ""
    for line in res.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:]
            findings.extend(scan_text_for_secrets(added_content, filename=current_file))
    return findings


def scan_diff_range(base_branch: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    diff_target = f"{base_branch}...HEAD" if "..." not in base_branch and base_branch not in ("HEAD", "HEAD~1") else base_branch
    cmd = ["git", "diff", diff_target, "--unified=0"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
    except Exception:
        return findings
    if res.returncode != 0:
        return findings

    current_file = ""
    for line in res.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:]
            findings.extend(scan_text_for_secrets(added_content, filename=current_file))
    return findings


def scan_directory(scan_dir: str = ".") -> List[Dict[str, Any]]:
    findings = []
    for root, dirs, files in os.walk(scan_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_SCAN_DIRS and not d.startswith(".")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in (".ts", ".js", ".go", ".rs", ".py", ".php", ".env", ".json", ".yaml", ".yml", ".toml"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    findings.extend(scan_text_for_secrets(content, filename=path))
                except Exception:
                    pass
    return findings


def cmd_security(args: argparse.Namespace) -> int:
    staged = getattr(args, "staged", False)
    diff = getattr(args, "diff", None)
    scan_dir = getattr(args, "dir", None)

    findings: List[Dict[str, Any]] = []

    if staged:
        findings = scan_staged_diff()
    elif diff:
        findings = scan_diff_range(diff)
    elif scan_dir:
        findings = scan_directory(scan_dir)
    else:
        # Default: scan staged diff first; if clean or empty, scan current directory
        findings = scan_staged_diff()
        if not findings and not os.path.exists(".git"):
            findings = scan_directory(".")

    if findings:
        print("[FAIL] CRITICAL SECURITY GATE: Secrets or credentials detected!", file=sys.stderr)
        for item in findings:
            loc = f"{item['file']}:{item.get('line', 1)}" if item['file'] else "staged"
            print(f"  ❌ [{item['type']}] at {loc}", file=sys.stderr)
            print(f"     Match: {item['matched']}", file=sys.stderr)
            print(f"     Note: {item['description']}", file=sys.stderr)
        print("\nRemediation: Remove hardcoded credentials. Use environment variables or secret managers.", file=sys.stderr)
        return 1

    print("[PASS] Security Secret Scanner: Zero secrets or leaked credentials detected.")
    return 0


def check_licenses(root_dir: str = ".") -> Tuple[int, List[Dict[str, str]]]:
    manifests: List[Dict[str, str]] = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_SCAN_DIRS and not d.startswith(".")]
        for f in files:
            if f == "package.json":
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    lic = data.get("license", "UNKNOWN")
                    manifests.append({"file": p, "project": data.get("name", "unknown"), "license": str(lic)})
                except Exception:
                    pass
            elif f == "Cargo.toml":
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    m = re.search(r'license\s*=\s*["\']([^"\']+)["\']', content)
                    lic = m.group(1) if m else "UNKNOWN"
                    manifests.append({"file": p, "project": os.path.basename(root), "license": lic})
                except Exception:
                    pass

    return 0, manifests


def extract_lockfile_dependencies(root_dir: str = ".") -> List[Dict[str, str]]:
    """Extracts external dependencies from lockfiles (pnpm, npm, cargo, go) for SBOM (DEFECT-17)."""
    deps: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    # Cargo.lock
    cargo_lock = os.path.join(root_dir, "Cargo.lock")
    if os.path.isfile(cargo_lock):
        try:
            with open(cargo_lock, "r", encoding="utf-8") as f:
                content = f.read()
            for block in content.split("[[package]]"):
                name_m = re.search(r'name\s*=\s*"([^"]+)"', block)
                ver_m = re.search(r'version\s*=\s*"([^"]+)"', block)
                if name_m and ver_m:
                    n, v = name_m.group(1), ver_m.group(1)
                    if (n, v) not in seen:
                        seen.add((n, v))
                        deps.append({"name": n, "version": v, "ecosystem": "cargo", "source": "Cargo.lock"})
        except Exception:
            pass

    # package-lock.json
    pkg_lock = os.path.join(root_dir, "package-lock.json")
    if os.path.isfile(pkg_lock):
        try:
            with open(pkg_lock, "r", encoding="utf-8") as f:
                data = json.load(f)
            packages = data.get("packages", {})
            for pkg_path, pkg_info in packages.items():
                if not pkg_path:
                    continue
                name = pkg_info.get("name") or pkg_path.split("node_modules/")[-1]
                version = pkg_info.get("version", "unknown")
                if (name, version) not in seen:
                    seen.add((name, version))
                    deps.append({"name": name, "version": version, "ecosystem": "npm", "source": "package-lock.json"})
        except Exception:
            pass

    # pnpm-lock.yaml
    pnpm_lock = os.path.join(root_dir, "pnpm-lock.yaml")
    if os.path.isfile(pnpm_lock):
        try:
            with open(pnpm_lock, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"^  /?(['\"]?)([@a-zA-Z0-9_\-\./]+)@([0-9a-zA-Z\.\-_]+)\1:", line)
                    if m:
                        name, version = m.group(2), m.group(3)
                        if (name, version) not in seen:
                            seen.add((name, version))
                            deps.append({"name": name, "version": version, "ecosystem": "pnpm", "source": "pnpm-lock.yaml"})
        except Exception:
            pass

    # go.sum
    go_sum = os.path.join(root_dir, "go.sum")
    if os.path.isfile(go_sum):
        try:
            with open(go_sum, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        name = parts[0]
                        version = parts[1].split("/")[0]
                        if (name, version) not in seen:
                            seen.add((name, version))
                            deps.append({"name": name, "version": version, "ecosystem": "go", "source": "go.sum"})
        except Exception:
            pass

    return deps


def cmd_license(args: argparse.Namespace) -> int:
    pkg_json = getattr(args, "package_json", None)
    if pkg_json:
        root = os.path.dirname(pkg_json) if os.path.isfile(pkg_json) else pkg_json
    else:
        root = getattr(args, "root", ".") or "."
    _, manifests = check_licenses(root)

    print(f"=== EP-OS License & Supply Chain Scanner ({len(manifests)} manifests inspected) ===")
    violations = []
    for m in manifests:
        lic = m["license"].upper()
        is_risky = any(cl in lic for cl in COPYLEFT_LICENSES)
        symbol = "❌" if is_risky else "✅"
        print(f"  {symbol} [{m['project']}] -> {m['license']} ({m['file']})")
        if is_risky:
            violations.append(m)

    if getattr(args, "sbom", False):
        os.makedirs(".ep", exist_ok=True)
        sbom_path = ".ep/sbom.json"
        external_deps = extract_lockfile_dependencies(root)
        sbom_data = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "metadata": {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "tools": ["EP-OS Supply Chain Scanner"]
            },
            "components": manifests,
            "dependencies": external_deps,
            "total_internal_components": len(manifests),
            "total_external_dependencies": len(external_deps),
        }
        with open(sbom_path, "w", encoding="utf-8") as fh:
            json.dump(sbom_data, fh, indent=2)
        print(f"[OK] Exported SBOM metadata ({len(manifests)} internal, {len(external_deps)} external dependencies) to '{sbom_path}'.")

    if violations:
        print(f"\n[FAIL] Copyleft license contagion detected in {len(violations)} package(s)!", file=sys.stderr)
        return 1

    print("[PASS] License Compliance: Zero copyleft license violations detected.")
    return 0


def scan_iac_files(target_dir: str = ".") -> List[Dict[str, Any]]:
    findings = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_SCAN_DIRS and not d.startswith(".")]
        for f in files:
            path = os.path.join(root, f)
            norm_path = path.replace("\\", "/")
            lower_name = f.lower()

            # Dockerfile checks
            if "dockerfile" in lower_name or f.endswith(".dockerfile"):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        lines = fh.readlines()
                    has_user = False
                    for idx, line in enumerate(lines, start=1):
                        clean = line.strip()
                        if clean.startswith("#"):
                            continue
                        if re.match(r"^FROM\s+[^\s:]+(:latest)?(\s+AS\s+.*)?$", clean, re.IGNORECASE):
                            findings.append({
                                "file": norm_path,
                                "line": idx,
                                "severity": "warning",
                                "rule": "IAC-DOCKER-LATEST-TAG",
                                "description": "Base image tag is ':latest' or unpinned. Use explicit SHA256 digest or immutable SemVer tag.",
                            })
                        if re.match(r"^USER\s+", clean, re.IGNORECASE):
                            user_val = clean.split()[1].strip().lower()
                            if user_val in ("root", "0"):
                                findings.append({
                                    "file": norm_path,
                                    "line": idx,
                                    "severity": "blocking",
                                    "rule": "IAC-DOCKER-ROOT-USER",
                                    "description": "Container explicitly executes as root user.",
                                })
                            else:
                                has_user = True
                        if re.search(r"^ARG\s+.*(secret|password|token|key|private)", clean, re.IGNORECASE):
                            findings.append({
                                "file": norm_path,
                                "line": idx,
                                "severity": "blocking",
                                "rule": "IAC-DOCKER-SECRET-BUILD-ARG",
                                "description": "Sensitive credential passed via Docker build ARG; will leak in image layers.",
                            })
                    if not has_user and len(lines) > 2:
                        findings.append({
                            "file": norm_path,
                            "line": len(lines),
                            "severity": "blocking",
                            "rule": "IAC-DOCKER-NO-USER-DIRECTIVE",
                            "description": "Dockerfile lacks non-root USER instruction; runs as root by default.",
                        })
                except Exception:
                    pass

            # Kubernetes / Compose YAML checks
            elif lower_name.endswith((".yaml", ".yml")) and any(p in norm_path for p in ["k8s", "deploy", "helm", "manifests", "docker-compose", "compose"]):
                if "template" in lower_name:
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    for idx, line in enumerate(content.splitlines(), start=1):
                        if re.search(r"privileged:\s*true", line, re.IGNORECASE):
                            findings.append({
                                "file": norm_path,
                                "line": idx,
                                "severity": "blocking",
                                "rule": "IAC-K8S-PRIVILEGED-CONTAINER",
                                "description": "Container executes in privileged mode; violates container isolation.",
                            })
                        if re.search(r"hostNetwork:\s*true", line, re.IGNORECASE):
                            findings.append({
                                "file": norm_path,
                                "line": idx,
                                "severity": "blocking",
                                "rule": "IAC-K8S-HOST-NETWORK",
                                "description": "Pod configured with hostNetwork: true; bypasses network namespace isolation.",
                            })
                except Exception:
                    pass
    return findings


def cmd_iac(args: argparse.Namespace) -> int:
    target_dir = getattr(args, "dir", ".") or "."
    findings = scan_iac_files(target_dir)

    print("=== EP-OS Infrastructure as Code (IaC) Security Gate ===")
    print(f"Scanning target directory: '{target_dir}'...\n")

    if not findings:
        print("[PASS] IaC Gate: Zero container or orchestration security misconfigurations found.")
        return 0

    blocking_count = sum(1 for f in findings if f["severity"] == "blocking")
    warning_count = len(findings) - blocking_count

    for f in findings:
        icon = "❌" if f["severity"] == "blocking" else "⚠️"
        print(f"  {icon} [{f['rule']}] at {f['file']}:{f['line']}")
        print(f"     Note: {f['description']}")

    print(f"\nIaC Scan Complete: {blocking_count} blocking defect(s), {warning_count} warning(s).")
    if blocking_count > 0:
        print("[FAIL] Blocking IaC violations detected. Mitigate root user execution and privileged settings before deployment.", file=sys.stderr)
        return 1

    return 0

