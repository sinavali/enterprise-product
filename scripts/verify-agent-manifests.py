#!/usr/bin/env python3
"""
verify-agent-manifests.py
Validates the syntax, schema, architectural profile compliance, and tier override validity
of all AGENT.md files across an enterprise monorepo.
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


ALLOWED_PROFILES = {"A", "B", "C", "D"}
ALLOWED_SCOPES = {"backend", "frontend", "mobile", "shared"}

# Tier 1 Inviolables that CANNOT be overridden under any circumstances
TIER_1_BANNED_OVERRIDES = {
    "pure-domain",
    "domain-isolation",
    "no-sqlite-in-integration",
    "testcontainers-only",
    "utc-storage",
    "utc-convention",
    "single-monorepo",
    "nx-orchestration",
    "14-day-nc",
    "nc-block",
    "2-pass-audit",
    "pr-audit",
    "change-surface",
    "mandatory-change-surface",
    "max-dir-depth",
    "directory-depth",
    "expand-contract",
    "expand-contract-migration",
    "anti-mvp",
    "zero-stub",
    "human-only-prod",
    "human-only-prod-merge",
    "prod-merge",
    "prod-merge-restriction",
    "no-agent-prod-merge",
}

TIER_1_BANNED_STEMS = [
    (r"sqlite", "No SQLite in integration tests"),
    (r"container", "Real containers required for integration tests"),
    (r"(prod.*merge|merge.*prod|auto.*merge)", "Human-only production merge"),
    (r"utc", "UTC timestamp storage convention"),
    (r"(mvp|stub)", "Zero-stub / Anti-MVP production rigor"),
    (r"(expand.*contract|contract.*expand|skip.*migration)", "Expand/Contract database migrations"),
    (r"(14-?day|nc-?block|non-?conformance)", "14-day non-conformance block"),
    (r"change-?surface", "Mandatory Change Surface"),
    (r"(pure-?domain|domain-?isolation)", "Pure Domain / DDD isolation"),
]

REQUIRED_SECTIONS = [
    r"1\.\s*Scope\s*(&|and)?\s*Business\s*Intent",
    r"2\.\s*Architectural\s*Profile",
    r"3\.\s*Local\s*Nx\s*Target",
    r"4\.\s*Test\s*(&|and)?\s*Verification",
]

EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    ".nx",
    "dist",
    "build",
    "coverage",
    ".cache",
    ".venv",
    "vendor",
    "templates",
    "__pycache__",
}


def parse_agent_yaml(content: str) -> Tuple[Dict, str]:
    stripped_content = content.lstrip("\ufeff \t\r\n")
    if not stripped_content.startswith("---"):
        return {}, content

    parts = stripped_content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    yaml_text = parts[1].strip()
    body = parts[2].strip()

    data = {"tier_overrides": []}
    current_list = None
    current_dict_item = None
    current_parent_key = None

    for line in yaml_text.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        # Check for list start or items (indented or unindented)
        list_dict_match = re.match(r"^\s*-\s*([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if list_dict_match and current_list == "tier_overrides":
            k = list_dict_match.group(1).strip()
            raw_v = list_dict_match.group(2).strip()
            if "#" in raw_v:
                m = re.match(r"^([\"'].*?[\"'])\s*(?:#.*)?$", raw_v)
                raw_v = m.group(1) if m else raw_v.split("#", 1)[0].strip()
            v = raw_v.strip("\"'")
            current_dict_item = {k: v}
            data["tier_overrides"].append(current_dict_item)
            continue

        sub_kv_match = re.match(r"^\s+([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if sub_kv_match:
            k = sub_kv_match.group(1).strip()
            raw_v = sub_kv_match.group(2).strip()
            if "#" in raw_v:
                m = re.match(r"^([\"'].*?[\"'])\s*(?:#.*)?$", raw_v)
                raw_v = m.group(1) if m else raw_v.split("#", 1)[0].strip()
            v = raw_v.strip("\"'")
            if current_dict_item is not None:
                current_dict_item[k] = v
            elif current_parent_key is not None:
                if not isinstance(data.get(current_parent_key), dict):
                    data[current_parent_key] = {}
                data[current_parent_key][k] = v
            continue

        # Top-level key
        kv_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if kv_match:
            current_dict_item = None
            k = kv_match.group(1).strip()
            raw_v = kv_match.group(2).strip()
            if "#" in raw_v:
                m = re.match(r"^([\"'].*?[\"'])\s*(?:#.*)?$", raw_v)
                raw_v = m.group(1) if m else raw_v.split("#", 1)[0].strip()
            v = raw_v.strip("\"'")
            if v == "" or v == "[]":
                if k == "tier_overrides":
                    data[k] = []
                    current_list = k
                    current_parent_key = None
                else:
                    data[k] = {}
                    current_list = None
                    current_parent_key = k
            else:
                data[k] = v
                current_list = None
                current_parent_key = None

    return data, body


def find_agent_files(root_dir: str) -> List[str]:
    matches = []
    for current_root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        if "AGENT.md" in files:
            matches.append(os.path.join(current_root, "AGENT.md"))
    return sorted(matches)


def verify_agent_manifest(
    file_path: str, root_dir: str, check_adrs: bool = True
) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, [f"Could not read file: {e}"]

    frontmatter, body = parse_agent_yaml(content)
    # A manifest is a root manifest if it resides at root_dir, is outside subproject trees (apps, services, libs, packages),
    # and does not declare subproject-specific project_name.
    norm_path = file_path.replace("\\", "/")
    has_project_name = bool(frontmatter.get("project_name")) if frontmatter else False
    in_subproject_dir = any(d in norm_path.split("/") for d in ["apps", "services", "libs", "packages"])
    is_root_file = (os.path.abspath(file_path) == os.path.abspath(os.path.join(root_dir, "AGENT.md")))
    is_root = is_root_file and not in_subproject_dir and not has_project_name

    # For subproject AGENT.md, frontmatter is strictly required with project properties
    if not is_root:
        if not frontmatter:
            errors.append("Missing required YAML frontmatter.")
        else:
            if "profile" not in frontmatter and "architectural_profile" in frontmatter:
                frontmatter["profile"] = frontmatter["architectural_profile"]
            for req in ["project_name", "profile", "stack", "scope"]:
                if req not in frontmatter or not frontmatter[req]:
                    errors.append(f"Missing required frontmatter property: '{req}'")

            prof = str(frontmatter.get("profile", "")).upper()
            if prof and prof not in ALLOWED_PROFILES:
                errors.append(f"Invalid profile '{prof}'. Must be one of: {', '.join(sorted(ALLOWED_PROFILES))}")

            sc = str(frontmatter.get("scope", "")).lower()
            if sc and sc not in ALLOWED_SCOPES:
                errors.append(f"Invalid scope '{sc}'. Must be one of: {', '.join(sorted(ALLOWED_SCOPES))}")

            # Validate optional operational & resilience metadata if present
            if "slo" in frontmatter and isinstance(frontmatter["slo"], dict):
                slo_tier = frontmatter["slo"].get("tier")
                if slo_tier and slo_tier not in ("tier-1", "tier-2", "tier-3"):
                    errors.append(f"Invalid frontmatter slo.tier '{slo_tier}'. Must be tier-1, tier-2, or tier-3.")

    # Check tier overrides (for both root and subproject manifests if present)
    overrides = frontmatter.get("tier_overrides", []) if frontmatter else []
    if isinstance(overrides, list):
        for ov in overrides:
            if not isinstance(ov, dict):
                continue
            rule = ov.get("rule", "")
            norm_rule = rule.lower().strip().replace("_", "-").replace(" ", "-")
            is_banned = norm_rule in TIER_1_BANNED_OVERRIDES or any(re.search(pat, norm_rule) for pat, _ in TIER_1_BANNED_STEMS)
            if is_banned:
                errors.append(f"Illegal Tier 1 override attempted for rule '{rule}'. Tier 1 rules are inviolable.")

            adr = ov.get("adr_reference")
            if not adr:
                errors.append(f"Tier override '{rule}' is missing required 'adr_reference'.")
            elif check_adrs:
                # Strip leading slashes so os.path.join does not discard root_dir
                clean_adr = adr.lstrip("/\\")
                path_from_root = os.path.join(root_dir, clean_adr)
                path_from_manifest = os.path.join(os.path.dirname(file_path), clean_adr)
                if not (os.path.exists(path_from_root) or os.path.exists(path_from_manifest)):
                    errors.append(f"Referenced ADR file does not exist: '{adr}'")

    # Section validation for non-root AGENT.md files
    if not is_root:
        for sec_pattern in REQUIRED_SECTIONS:
            if not re.search(r"^##\s*" + sec_pattern, body, re.IGNORECASE | re.MULTILINE):
                errors.append(f"Missing required section matching pattern: '## {sec_pattern}'")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Verify AGENT.md manifests across the monorepo.")
    parser.add_argument("--root", default=".", help="Root directory to scan (default: current directory)")
    parser.add_argument("--no-check-adrs", dest="check_adrs", action="store_false", help="Skip checking ADR file existence")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    if not os.path.exists(args.root):
        print(f"[ERROR] Specified root directory '{args.root}' does not exist.", file=sys.stderr)
        sys.exit(1)

    agent_files = find_agent_files(args.root)
    results = {}
    total_errors = 0

    for af in agent_files:
        valid, errors = verify_agent_manifest(af, root_dir=args.root, check_adrs=args.check_adrs)
        rel_path = os.path.relpath(af, args.root)
        results[rel_path] = {"valid": valid, "errors": errors}
        total_errors += len(errors)

    all_valid = total_errors == 0

    if args.json:
        out = {
            "root": args.root,
            "total_manifests": len(agent_files),
            "compliant": all_valid,
            "total_errors": total_errors,
            "manifests": results,
        }
        print(json.dumps(out, indent=2))
    else:
        print("=== AGENT.md Manifest Verification ===")
        print(f"Scanned {len(agent_files)} AGENT.md file(s) under '{args.root}'.\n")

        if len(agent_files) == 0:
            print("[INFO] No AGENT.md files found.")
            sys.exit(0)

        for path, info in results.items():
            if info["valid"]:
                print(f"[PASS] {path}")
            else:
                print(f"[FAIL] {path}:")
                for err in info["errors"]:
                    print(f"       - {err}")

        print(f"\nResult: {'ALL PASSED' if all_valid else f'FAILED with {total_errors} error(s)'}")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
