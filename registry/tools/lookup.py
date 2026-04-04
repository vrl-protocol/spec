#!/usr/bin/env python3
"""
VRL Circuit Registry Lookup Tool

A command-line utility to query and display circuits from the VRL Circuit Registry.

Usage:
    python lookup.py <circuit_id>              # Look up a specific circuit
    python lookup.py --list                    # List all circuits
    python lookup.py --list --domain trade     # Filter by domain
    python lookup.py --list --tier CERTIFIED   # Filter by certification tier
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any


class CircuitRegistry:
    """Load and query the VRL Circuit Registry."""

    def __init__(self, registry_path: Path):
        """Initialize registry from registry.json file."""
        self.registry_path = registry_path
        self.circuits = []
        self.load()

    def load(self) -> None:
        """Load circuits from registry.json."""
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                self.circuits = data.get('circuits', [])
        except FileNotFoundError:
            print(f"Error: Registry file not found at {self.registry_path}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in registry file: {e}", file=sys.stderr)
            sys.exit(1)

    def get_circuit(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific circuit by ID."""
        for circuit in self.circuits:
            if circuit['circuit_id'] == circuit_id:
                return circuit
        return None

    def list_circuits(
        self,
        domain: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List circuits with optional filtering."""
        results = self.circuits

        if domain:
            results = [c for c in results if c['domain'] == domain]

        if tier:
            results = [c for c in results if c['certification_tier'] == tier]

        return sorted(results, key=lambda c: c['circuit_id'])

    def get_domains(self) -> List[str]:
        """Get list of all domains."""
        return sorted(set(c['domain'] for c in self.circuits))

    def get_tiers(self) -> List[str]:
        """Get list of all certification tiers."""
        return sorted(set(c['certification_tier'] for c in self.circuits))


def print_circuit_detail(circuit: Dict[str, Any]) -> None:
    """Print detailed information about a circuit."""
    print(f"\n{'=' * 70}")
    print(f"Circuit: {circuit['circuit_id']}")
    print(f"{'=' * 70}\n")

    print(f"Certification Tier: {circuit['certification_tier']}")
    print(f"Domain:             {circuit['domain']}")
    print(f"Circuit Hash:       {circuit['circuit_hash']}")
    print()

    print(f"Description:\n  {circuit['description']}\n")

    if 'long_description' in circuit:
        print(f"Details:\n  {circuit['long_description']}\n")

    print(f"Author:             {circuit['author']}")
    if 'author_email' in circuit:
        print(f"Email:              {circuit['author_email']}")
    print(f"License:            {circuit['license']}")
    print(f"Published:          {circuit['published_at']}")
    print()

    print("Input Schema:")
    if 'private' in circuit['input_schema']:
        print("  Private:")
        for inp in circuit['input_schema']['private']:
            if isinstance(inp, dict):
                print(f"    - {inp['name']} ({inp['type']}): {inp['description']}")
            else:
                print(f"    - {inp}")
    if 'public' in circuit['input_schema']:
        print("  Public:")
        for inp in circuit['input_schema']['public']:
            if isinstance(inp, dict):
                print(f"    - {inp['name']} ({inp['type']}): {inp['description']}")
            else:
                print(f"    - {inp}")
    print()

    print("Output Schema:")
    for out in circuit['output_schema']['public']:
        if isinstance(out, dict):
            print(f"  - {out['name']} ({out['type']}): {out['description']}")
        else:
            print(f"  - {out}")
    print()

    print(f"Proof Systems:      {', '.join(circuit['proof_systems'])}")
    print(f"Constraints:        {circuit['constraint_count']}")
    print()

    if circuit.get('dataset_dependencies'):
        print("Dataset Dependencies:")
        for dep in circuit['dataset_dependencies']:
            print(f"  - {dep['dataset_id']} (>= {dep['min_version']})")
            if 'description' in dep:
                print(f"    {dep['description']}")
        print()

    if 'compliance_frameworks' in circuit and circuit['compliance_frameworks']:
        print(f"Compliance:         {', '.join(circuit['compliance_frameworks'])}")
        print()

    if 'tags' in circuit:
        print(f"Tags:               {', '.join(circuit['tags'])}")
        print()

    if 'security_notes' in circuit:
        print(f"Security Notes:\n  {circuit['security_notes']}\n")

    if 'performance_notes' in circuit:
        print(f"Performance:\n  {circuit['performance_notes']}\n")

    print(f"{'=' * 70}\n")


def print_circuits_table(circuits: List[Dict[str, Any]]) -> None:
    """Print circuits in a nice table format."""
    if not circuits:
        print("No circuits found.")
        return

    # Calculate column widths
    col_id = max(len(c['circuit_id']) for c in circuits)
    col_domain = max(len(c['domain']) for c in circuits)
    col_tier = max(len(c['certification_tier']) for c in circuits)

    col_id = max(col_id, 15)
    col_domain = max(col_domain, 8)
    col_tier = max(col_tier, 14)

    # Print header
    header = f"{'Circuit ID':<{col_id}} {'Domain':<{col_domain}} {'Tier':<{col_tier}} Description"
    print(f"\n{header}")
    print("-" * 100)

    # Print rows
    for circuit in circuits:
        desc = circuit['description'][:50] + "..." if len(circuit['description']) > 50 else circuit['description']
        row = f"{circuit['circuit_id']:<{col_id}} {circuit['domain']:<{col_domain}} {circuit['certification_tier']:<{col_tier}} {desc}"
        print(row)

    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='VRL Circuit Registry Lookup Tool',
        epilog='Examples:\n'
               '  python lookup.py trade/import-landed-cost@2.0.0\n'
               '  python lookup.py --list\n'
               '  python lookup.py --list --domain trade\n'
               '  python lookup.py --list --tier CERTIFIED',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('circuit_id', nargs='?', help='Circuit ID to look up')
    parser.add_argument('--list', action='store_true', help='List all circuits')
    parser.add_argument('--domain', help='Filter by domain (trade, healthcare, finance, general)')
    parser.add_argument('--tier', help='Filter by certification tier (EXPERIMENTAL, REVIEWED, CERTIFIED)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    # Determine registry path
    registry_dir = Path(__file__).parent.parent
    registry_path = registry_dir / 'registry.json'

    # Load registry
    registry = CircuitRegistry(registry_path)

    # Handle --list
    if args.list:
        circuits = registry.list_circuits(domain=args.domain, tier=args.tier)

        if args.json:
            print(json.dumps(circuits, indent=2))
        else:
            print_circuits_table(circuits)

        if not circuits:
            sys.exit(1)
        sys.exit(0)

    # Handle specific circuit lookup
    if args.circuit_id:
        circuit = registry.get_circuit(args.circuit_id)

        if not circuit:
            print(f"Error: Circuit '{args.circuit_id}' not found in registry", file=sys.stderr)
            print(f"\nAvailable circuits:", file=sys.stderr)
            print_circuits_table(registry.list_circuits())
            sys.exit(1)

        if args.json:
            print(json.dumps(circuit, indent=2))
        else:
            print_circuit_detail(circuit)

        sys.exit(0)

    # If no arguments, show help
    if not args.circuit_id and not args.list:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()
