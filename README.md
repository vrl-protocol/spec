# VRL Integration Workspace

This repository is the local integration workspace for VRL.

It is not the long-term public source of truth. The target public layout is:

1. `vrl-protocol/spec`
2. `vrl-protocol/sdk`
3. `vrl-protocol/registry`
4. `vrl-protocol/server`

Use this workspace to:

- iterate across protocol, SDK, registry, and server changes together
- run cross-cutting tests before splitting or publishing
- generate clean per-repo exports from one local working tree

## Split Plan

The split plan lives at:

- [docs/REPO_SPLIT_PLAN.md](./docs/REPO_SPLIT_PLAN.md)

The export manifest lives at:

- [proposals/repo_split_manifest.json](./proposals/repo_split_manifest.json)

## Export The Split Repos

Generate the four target repos under `C:\Users\13173\OneDrive\Documents\vrl-split`:

```powershell
cd "C:\Users\13173\OneDrive\Documents\verifiable-reality-layer"
python scripts/export_repo_split.py
```

Or with the PowerShell wrapper:

```powershell
cd "C:\Users\13173\OneDrive\Documents\verifiable-reality-layer"
.\scripts\export_repo_split.ps1
```

## Generated Output

The exporter creates:

- `C:\Users\13173\OneDrive\Documents\vrl-split\spec`
- `C:\Users\13173\OneDrive\Documents\vrl-split\sdk`
- `C:\Users\13173\OneDrive\Documents\vrl-split\registry`
- `C:\Users\13173\OneDrive\Documents\vrl-split\server`

Each generated repo includes:

- a repo-specific `README.md`
- a repo-specific `.gitignore`
- a `.vrl-export.json` summary file

## Current Role Of This Repo

Think of this repository as:

- a local staging area
- a cross-repo integration harness
- a safe place to evolve boundaries before publishing

Do not treat this repo as the canonical public `spec` repository.
