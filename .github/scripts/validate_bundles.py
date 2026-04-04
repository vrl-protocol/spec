#!/usr/bin/env python3
"""
Validate VRL test bundles against the JSON Schema in SPEC.md §17.

This script:
1. Reads SPEC.md and extracts the JSON Schema from §17
2. Validates each .json file in verifier/test_bundles/ against it
3. Prints PASS/FAIL for each bundle
4. Exits with code 1 if any validation fails
"""

import json
import re
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Install with: pip install jsonschema")
    sys.exit(1)


def extract_schema_from_spec(spec_path):
    """Extract JSON Schema from SPEC.md §17."""
    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: {spec_path} not found")
        sys.exit(1)

    # Find §17 section
    # Look for "## 17. JSON Schema" or similar
    section_17_match = re.search(
        r"^## 17\. JSON Schema.*?^(?=## [0-9]+\.|$)",
        content,
        re.MULTILINE | re.DOTALL
    )

    if not section_17_match:
        print("ERROR: Section 17 (JSON Schema) not found in SPEC.md")
        sys.exit(1)

    section_17 = section_17_match.group(0)

    # Extract JSON from code block
    # Look for ```json ... ``` blocks
    json_matches = re.findall(
        r"```(?:json)?\s*\n(.*?)\n```",
        section_17,
        re.DOTALL
    )

    if not json_matches:
        print("ERROR: No JSON schema found in §17")
        sys.exit(1)

    # Try each JSON block until we find valid schema
    schema = None
    for json_block in json_matches:
        try:
            candidate = json.loads(json_block)
            # Valid schema should have type or $schema property
            if "type" in candidate or "$schema" in candidate:
                schema = candidate
                break
        except json.JSONDecodeError:
            continue

    if schema is None:
        print("ERROR: Could not parse valid JSON schema from §17")
        sys.exit(1)

    return schema


def validate_bundles(spec_path, bundles_dir):
    """Validate all bundles in bundles_dir against the schema."""
    # Extract schema from SPEC.md
    schema = extract_schema_from_spec(spec_path)
    print(f"✓ Extracted JSON Schema from {spec_path} §17")
    print()

    bundles_path = Path(bundles_dir)
    if not bundles_path.exists():
        print(f"WARNING: {bundles_dir} directory not found")
        return True

    # Find all .json files in test_bundles/
    json_files = sorted(bundles_path.glob("*.json"))

    if not json_files:
        print(f"WARNING: No .json files found in {bundles_dir}")
        return True

    print(f"Validating {len(json_files)} bundle(s):")
    all_valid = True

    for bundle_file in json_files:
        try:
            with open(bundle_file, "r", encoding="utf-8") as f:
                bundle = json.load(f)
        except json.JSONDecodeError as e:
            print(f"✗ FAIL: {bundle_file.name} - Invalid JSON: {e}")
            all_valid = False
            continue

        try:
            jsonschema.validate(instance=bundle, schema=schema)
            print(f"✓ PASS: {bundle_file.name}")
        except jsonschema.ValidationError as e:
            print(f"✗ FAIL: {bundle_file.name} - Schema validation error:")
            print(f"  {e.message}")
            if e.path:
                print(f"  Path: {'.'.join(str(p) for p in e.path)}")
            all_valid = False
        except Exception as e:
            print(f"✗ FAIL: {bundle_file.name} - Unexpected error: {e}")
            all_valid = False

    print()
    return all_valid


def main():
    """Main entry point."""
    spec_path = Path("SPEC.md")
    bundles_dir = Path("verifier/test_bundles")

    if not spec_path.exists():
        print(f"ERROR: {spec_path} not found")
        sys.exit(1)

    success = validate_bundles(spec_path, bundles_dir)

    if success:
        print("All bundle validations passed!")
        sys.exit(0)
    else:
        print("Some bundle validations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
