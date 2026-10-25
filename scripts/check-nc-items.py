#!/usr/bin/env python3
"""
check-nc-items.py
Scans, tracks, and audits NEED_CLARIFICATION (NC) items in an enterprise repository.
Enforces the 14-day merge blocking escalation gate for open NC items.
"""

import argparse
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


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
    "references",
    "__pycache__",
}

VALID_STATUSES = {"OPEN", "RESOLVED", "ABANDONED"}


def parse_date(date_str: str) -> Optional[datetime.date]:
    if not date_str:
        return None
    cleaned = str(date_str).strip().strip("\"'")
    if "T" in cleaned or " " in cleaned:
        cleaned = cleaned.split("T")[0].split(" ")[0]
    cleaned = cleaned.replace("/", "-")
    try:
        return datetime.date.fromisoformat(cleaned)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    return None


def parse_nc_file(file_path: str) -> Optional[Dict]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"file_path": file_path, "parse_error": f"Failed to read file: {e}"}

    stripped_content = content.lstrip("\ufeff \t\r\n")
    norm_path = file_path.replace("\\", "/")
    basename = os.path.basename(norm_path)
    if basename.lower() in ("nc-protocol.md", "need_clarification.template.md", "nc.md"):
        return None
    is_nc_designated = basename.upper().startswith("NC-") or "/docs/nc/" in norm_path or norm_path.startswith("docs/nc/")

    if not stripped_content.startswith("---"):
        if is_nc_designated:
            return {"file_path": file_path, "parse_error": "Missing YAML frontmatter block (enclosed in ---)."}
        return None

    parts = stripped_content.split("---", 2)
    if len(parts) < 3:
        if is_nc_designated:
            return {"file_path": file_path, "parse_error": "Unclosed YAML frontmatter block."}
        return None

    yaml_text = parts[1].strip()
    data: Dict[str, Any] = {"file_path": file_path, "affected_projects": []}
    current_list_key = None

    for line in yaml_text.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

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

        kv_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if kv_match:
            k = kv_match.group(1).strip()
            raw_v = kv_match.group(2).strip()
            if "#" in raw_v:
                m = re.match(r"^([\"'].*?[\"'])\s*(?:#.*)?$", raw_v)
                raw_v = m.group(1) if m else raw_v.split("#", 1)[0].strip()
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

    nc_id = str(data.get("id", "")).strip()
    if any(p in nc_id.upper() for p in ["YYYY", "XXXX", "TEMPLATE", "["]):
        return None

    if not nc_id.upper().startswith("NC-"):
        if is_nc_designated:
            return {"file_path": file_path, "parse_error": f"Missing or invalid NC ID ('{nc_id}'). Expected format: 'NC-YYYYMMDD-XXX'."}
        return None

    return data


def scan_nc_items(scan_dir: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not os.path.exists(scan_dir):
        return items

    if os.path.isfile(scan_dir):
        parsed = parse_nc_file(scan_dir)
        if parsed:
            items.append(parsed)
        return items

    for root, dirs, files in os.walk(scan_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for f in files:
            if f.endswith(".md") and not f.endswith(".template.md"):
                full_path = os.path.join(root, f)
                parsed = parse_nc_file(full_path)
                if parsed:
                    items.append(parsed)

    return items


def audit_nc_items(
    items: List[Dict], max_age_days: int = 14, as_of_date: Optional[datetime.date] = None
) -> Tuple[List[Dict], List[Dict], List[str]]:
    if as_of_date is None:
        as_of_date = datetime.date.today()

    open_items = []
    blocking_items = []
    errors = []

    for item in items:
        if "parse_error" in item:
            errors.append(f"{item['file_path']}: {item['parse_error']}")
            continue

        nc_id = item.get("id", "UNKNOWN")
        status = str(item.get("status", "OPEN")).upper()
        created_str = item.get("created_date")

        if status not in VALID_STATUSES:
            errors.append(f"{nc_id} ({item['file_path']}): Invalid status '{status}'. Expected one of: {', '.join(sorted(VALID_STATUSES))}")
            continue

        if not created_str:
            errors.append(f"{nc_id} ({item['file_path']}): Missing created_date.")
            continue

        created_date = parse_date(created_str)
        if not created_date:
            errors.append(f"{nc_id} ({item['file_path']}): Invalid created_date '{created_str}'. Expected valid ISO date.")
            continue

        age_days = (as_of_date - created_date).days
        item["age_days"] = max(0, age_days)

        if status == "RESOLVED":
            resolved_str = item.get("resolved_date")
            if not resolved_str:
                errors.append(f"{nc_id} ({item['file_path']}): Status is RESOLVED but missing required 'resolved_date'.")
            elif not parse_date(resolved_str):
                errors.append(f"{nc_id} ({item['file_path']}): Status is RESOLVED but has invalid 'resolved_date' '{resolved_str}'.")

        if status == "OPEN":
            open_items.append(item)
            if age_days >= max_age_days:
                blocking_items.append(item)

    return open_items, blocking_items, errors


def main():
    parser = argparse.ArgumentParser(description="Audit and track NEED_CLARIFICATION (NC) items.")
    parser.add_argument(
        "--dir",
        default="docs/nc",
        help="Directory or file path to scan for NC items (defaults to 'docs/nc')",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=14,
        help="Maximum allowed age in days for open NC items before blocking merge (default: 14)",
    )
    parser.add_argument(
        "--as-of-date",
        help="Reference date for calculating age in YYYY-MM-DD format (defaults to current date)",
    )
    parser.add_argument(
        "--block-on-open-aged",
        action="store_true",
        default=True,
        help="Exit with code 1 if any open NC item is >= max-age (default: True)",
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    ref_date = None
    if args.as_of_date:
        ref_date = parse_date(args.as_of_date)
        if not ref_date:
            print(f"[ERROR] Invalid --as-of-date '{args.as_of_date}'. Expected valid date (YYYY-MM-DD or YYYY/MM/DD).", file=sys.stderr)
            sys.exit(2)

    # If default dir doesn't exist, try scanning root docs or current dir
    target_dir = args.dir
    if not os.path.exists(target_dir):
        if args.dir != "docs/nc":
            print(f"[ERROR] Specified directory '{args.dir}' does not exist.", file=sys.stderr)
            sys.exit(1)
        if os.path.exists("docs"):
            target_dir = "docs"
        else:
            target_dir = "."

    items = scan_nc_items(target_dir)
    open_items, blocking_items, parse_errors = audit_nc_items(
        items, max_age_days=args.max_age, as_of_date=ref_date
    )

    is_blocked = len(blocking_items) > 0 or len(parse_errors) > 0

    if args.json:
        output = {
            "total_items": len(items),
            "open_items": open_items,
            "blocking_items": blocking_items,
            "parse_errors": parse_errors,
            "max_age_days": args.max_age,
            "is_blocked": is_blocked,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"=== NC Protocol Audit (Found {len(items)} NC items, {len(open_items)} open) ===")
        if parse_errors:
            print(f"[PARSE ERRORS] {len(parse_errors)} error(s):")
            for err in parse_errors:
                print(f"  - {err}")

        if blocking_items:
            print(f"\n[MERGE BLOCK DETECTED] {len(blocking_items)} open NC item(s) >= {args.max_age} days old:")
            for item in blocking_items:
                print(f"  - {item.get('id')}: Age {item.get('age_days')} days (Created {item.get('created_date')})")
                print(f"    File: {item.get('file_path')}")
                if item.get("affected_projects"):
                    print(f"    Affected Projects: {', '.join(item['affected_projects'])}")
            print("\nAction Required: These items must be resolved with stakeholder decisions before PR merge.")
        else:
            print(f"[OK] No blocking NC items. (All open items are < {args.max_age} days old).")

    if args.block_on_open_aged and is_blocked:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
