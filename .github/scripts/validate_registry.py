#!/usr/bin/env python3
"""
Validate VRL Circuit Registry circuits against the circuit schema.

This script:
1. Reads registry/schema/circuit.schema.json
2. Validates each .json file in registry/circuits/ against it
3. Prints PASS/FAIL for each circuit
4. Exits with code 1 if any validation fails
"""

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Install with: pip install jsonschema")
    sys.exit(1)


def load_schema(schema_path):
    """Load the circuit JSON schema."""
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        return schema
    except FileNotFoundError:
        print(f"ERROR: Schema file not found: {schema_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse schema: {e}")
        sys.exit(1)


def validate_circuits(schema_path, circuits_dir):
    """Validate all circuits against the schema."""
    schema = load_schema(schema_path)
    print(f"✓ Loaded schema from {schema_path}")
    print()

    circuits_path = Path(circuits_dir)
    if not circuits_path.exists():
        print(f"WARNING: {circuits_dir} directory not found")
        return True

    # Find all .json files in circuits/
    json_files = sorted(circuits_path.glob("*.json"))

    if not json_files:
        print(f"WARNING: No .json files found in {circuits_dir}")
        return True

    print(f"Validating {len(json_files)} circuit(s):")
    all_valid = True

    for circuit_file in json_files:
        try:
            with open(circuit_file, "r", encoding="utf-8") as f:
                circuit = json.load(f)
        except json.JSONDecodeError as e:
            print(f"✗ FAIL: {circuit_file.name} - Invalid JSON: {e}")
            all_valid = False
            continue

        # Get circuit_id for better error messages
        circuit_id = circuit.get("circuit_id", circuit_file.name)

        try:
            jsonschema.validate(instance=circuit, schema=schema)
            print(f"✓ PASS: {circuit_id}")
        except jsonschema.ValidationError as e:
            print(f"✗ FAIL: {circuit_id} - Schema validation error:")
            print(f"  {e.message}")
            if e.path:
                print(f"  Path: {'.'.join(str(p) for p in e.path)}")
            all_valid = False
        except Exception as e:
            print(f"✗ FAIL: {circuit_id} - Unexpected error: {e}")
            all_valid = False

    print()
    return all_valid


def validate_registry_index(registry_path, circuits_dir):
    """Validate that registry.json references all circuits."""
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Registry index is optional for this basic validation
        return True

    circuits_path = Path(circuits_dir)
    json_files = {f.stem for f in circuits_path.glob("*.json")}
    indexed_circuits = {c.get("circuit_id", "").split("@")[0] for c in registry.get("circuits", [])}

    print("Checking registry index consistency...")
    # Basic check: warn if circuits exist but aren't indexed
    for filename in json_files:
        if not any(filename in str(c) for c in indexed_circuits):
            print(f"  WARNING: {filename}.json not found in registry.json index")

    return True


def main():
    """Main entry point."""
    schema_path = Path("registry/schema/circuit.schema.json")
    circuits_dir = Path("registry/circuits")
    registry_path = Path("registry/registry.json")

    if not schema_path.exists():
        print(f"ERROR: {schema_path} not found")
        sys.exit(1)

    success = validate_circuits(schema_path, circuits_dir)
    validate_registry_index(registry_path, circuits_dir)

    if success:
        print("All circuit validations passed!")
        sys.exit(0)
    else:
        print("Some circuit validations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
