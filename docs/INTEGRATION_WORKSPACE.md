# Integration Workspace

This repository exists to support local VRL development across multiple public repos before those boundaries are fully stable.

## Why It Exists

During early development, protocol work, SDK work, registry work, and runtime work often change together. Splitting too early creates friction. This workspace keeps those concerns together locally while preserving a clean path to the target repository model.

## Public Target Repositories

- `vrl-protocol/spec`
- `vrl-protocol/sdk`
- `vrl-protocol/registry`
- `vrl-protocol/server`

## Local Workflow

1. Make changes here.
2. Run tests and checks here.
3. Export split repos with `scripts/export_repo_split.py`.
4. Push each exported repo to its public destination.

## Rules

- avoid committing generated artifacts
- keep split boundaries documented
- prefer updating the manifest instead of manually copying files
- use this repo to validate integration, not as the public canonical home
