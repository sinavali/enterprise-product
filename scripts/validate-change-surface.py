#!/usr/bin/env python3
"""
validate-change-surface.py
Validates the structure, frontmatter, and completeness of an enterprise CHANGE_SURFACE artifact.
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple


REQUIRED_FRONTMATTER_FIELDS = [
    "title",
    "author",
    "created_date",
    "target_branch",
    "risk_level",
    "affected_projects",
]

ALLOWED_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

REQUIRED_SECTIONS = [
    r"1\.\s*Intent\s*(&|and)?\s*Business\s*Rationale",
    r"2\.\s*Affected\s*Monorepo\s*Projects",
    r"3\.\s*Code\s*Surface",
    r"4\.\s*Test\s*Surface",
    r"5\.\s*Invariants",
    r"6\.\s*Risk\s*Matrix",
]

PLACEHOLDER_PATTERNS = [
    r"\[(?:Author|Agent|TODO|project-path|Short|Feature|Insert|Pending).*?\]",
    r"YYYY-MM-DD",
]


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    stripped_content = content.lstrip("\ufeff \t\r\n")
    if not stripped_content.startswith("---"):
        return {}, content
    
    parts = stripped_content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    
    yaml_text = parts[1].strip()
    body = parts[2].strip()
    
    # Simple YAML key-value parser for standard scalar and list structures
    data: Dict[str, Any] = {}
    current_list_key = None
    
    for line in yaml_text.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        
        # List item (handles indented or unindented list bullets)
        list_match = re.match(r"^\s*-\s*(.*?)$", line)
        if list_match and current_list_key:
            raw_item = list_match.group(1).strip()
            if "#" in raw_item:
                m = re.match(r"^([\"'].*?[\"'])\s*(?:#.*)?$", raw_item)
                raw_item = m.group(1) if m else raw_item.split("#", 1)[0].strip()
            item_val = raw_item.strip("\"'")
            if item_val and isinstance(data.get(current_list_key), list):
                data[current_list_key].append(item_val)
            continue
        
        # Key-value
        kv_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if kv_match:
            k = kv_match.group(1).strip()
            raw_v = kv_match.group(2).strip()
            if "#" in raw_v:
                m = re.match(r"^([\"'].*?[\"'])\s*(?:#.*)?$", raw_v)
                if m:
                    raw_v = m.group(1)
                else:
                    raw_v = raw_v.split("#", 1)[0].strip()
            v = raw_v.strip("\"'")
            if v == "" or v == "[]":
                data[k] = []
                current_list_key = k
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                data[k] = [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
                current_list_key = None
            else:
                data[k] = v
                current_list_key = None
                
    return data, body


def validate_change_surface(file_path: str, strict: bool = False) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    
    if not os.path.isfile(file_path):
        return False, [f"File not found: {file_path}"]
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, [f"Failed to read file: {e}"]
    
    if not content.strip():
        return False, ["File is empty."]
    
    frontmatter, body = parse_frontmatter(content)
    
    # 1. Frontmatter validation
    if not frontmatter:
        errors.append("Missing YAML frontmatter block (enclosed in ---).")
    else:
        for field in REQUIRED_FRONTMATTER_FIELDS:
            if field not in frontmatter:
                errors.append(f"Missing required frontmatter field: '{field}'")
            elif not frontmatter[field]:
                errors.append(f"Frontmatter field '{field}' cannot be empty.")
        
        risk = frontmatter.get("risk_level", "").upper()
        if risk and risk not in ALLOWED_RISK_LEVELS:
            errors.append(f"Invalid risk_level '{risk}'. Must be one of: {', '.join(sorted(ALLOWED_RISK_LEVELS))}")

        created_str = str(frontmatter.get("created_date", "")).strip()
        if created_str and not re.match(r"^\d{4}[-/](?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01])$", created_str):
            errors.append(f"Invalid created_date '{created_str}'. Expected valid ISO date (YYYY-MM-DD).")
            
        affected = frontmatter.get("affected_projects")
        if not isinstance(affected, list) or len(affected) == 0:
            errors.append("Frontmatter 'affected_projects' list must contain at least one project.")

    # 2. Section validation
    for sec_pattern in REQUIRED_SECTIONS:
        if not re.search(r"^##\s*" + sec_pattern, body, re.IGNORECASE | re.MULTILINE):
            errors.append(f"Missing required section matching pattern: '## {sec_pattern}'")
            
    # 3. Check for wildcards in Code Surface
    code_surface_match = re.search(r"^##\s*3\.\s*Code\s*Surface[^\n]*\n(.*?)(?=\n##\s+[0-9]|\Z)", body, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    if code_surface_match:
        code_surface_text = code_surface_match.group(1)
        if re.search(r"(?:^|\n)\s*[-*]?\s*[`]?\*[`]?\s*(?:\n|$)", code_surface_text):
            errors.append("Code Surface contains unconstrained bare wildcard '*' which is forbidden.")
        has_symbol_marker = bool(
            re.search(r"(?:[-*]|\d+\.)\s*`|###\s*(Added|Modified)", code_surface_text)
        )
        if not has_symbol_marker:
            errors.append("Code Surface does not list explicit files or symbol targets.")

    # 4. Check for test targets in Test Surface
    test_surface_match = re.search(
        r"^##\s*4\.\s*Test\s*Surface[^\n]*\n(.*?)(?=\n##\s+[0-9]|\Z)",
        body,
        re.DOTALL | re.IGNORECASE | re.MULTILINE,
    )
    if test_surface_match:
        test_surface_text = test_surface_match.group(1).strip()
        has_test_marker = bool(
            re.search(
                r"(?:[-*]|\d+\.)\s*`|###\s*(Unit|Domain|Integration|Failure|Concurrency|Compatibility|E2E)|\bN/A\b",
                test_surface_text,
                re.IGNORECASE,
            )
        )
        if not has_test_marker:
            errors.append("Test Surface does not list explicit test files, test suites, or justifiable N/A status.")

    # 5. Strict placeholder check
    if strict:
        for pat in PLACEHOLDER_PATTERNS:
            matches = re.findall(pat, content)
            if matches:
                errors.append(f"Found unpopulated template placeholder(s): {matches[:3]}")

    is_valid = len(errors) == 0
    return is_valid, errors


def main():
    parser = argparse.ArgumentParser(description="Validate enterprise CHANGE_SURFACE artifact.")
    parser.add_argument("file", nargs="?", default="CHANGE_SURFACE.md", help="Path to CHANGE_SURFACE markdown file")
    parser.add_argument("--strict", action="store_true", help="Disallow template placeholders")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()
    target_file = args.file
    if target_file == "CHANGE_SURFACE.md" and not os.path.exists("CHANGE_SURFACE.md"):
        if os.path.isdir("docs/changes"):
            change_files = sorted(
                [os.path.join("docs/changes", f) for f in os.listdir("docs/changes") if f.endswith(".md")],
                reverse=True,
            )
            if change_files:
                target_file = change_files[0]

    is_valid, errors = validate_change_surface(target_file, strict=args.strict)
    
    if args.json:
        res = {
            "file": target_file,
            "valid": is_valid,
            "errors": errors,
        }
        print(json.dumps(res, indent=2))
    else:
        if is_valid:
            print(f"[SUCCESS] Change Surface '{target_file}' is structurally valid and complete.")
        else:
            print(f"[ERROR] Change Surface '{target_file}' failed validation with {len(errors)} error(s):")
            for err in errors:
                print(f"  - {err}")
                
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
