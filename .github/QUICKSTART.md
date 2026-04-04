# CI/CD Pipeline Quick Start

## Files Created

```
.github/
├── workflows/
│   ├── ci.yml              # Main CI: test SDKs, validate spec/registry
│   ├── publish.yml         # Publish to PyPI, npm, git tags
│   └── pages.yml           # GitHub Pages deployment
├── ISSUE_TEMPLATE/
│   ├── bug_report.yml      # Bug report form
│   └── circuit_submission.yml  # Circuit submission form
├── scripts/
│   ├── validate_bundles.py # Validate test bundles vs SPEC.md §17
│   └── validate_registry.py # Validate circuits vs schema
├── PULL_REQUEST_TEMPLATE.md # PR checklist
├── README.md               # Full documentation (this directory)
└── QUICKSTART.md           # This file
```

## Setup in 3 Steps

### 1. Add Repository Secrets

In GitHub: Settings → Secrets and variables → Actions

```
Name: PYPI_API_TOKEN
Value: <your PyPI API token>

Name: NPM_TOKEN
Value: <your npm token>
```

### 2. Enable GitHub Pages

In GitHub: Settings → Pages
- Source: Deploy from a branch
- Branch: gh-pages (will be auto-created)

### 3. Commit and Push

```bash
git add .github/
git commit -m "Add GitHub Actions CI/CD pipeline"
git push origin main
```

## Verify It Works

1. **CI Pipeline**: Push to main or create a PR
   - Workflows tab will show ci.yml running
   - Should see 6 jobs: test-python, test-typescript, test-go, validate-spec, validate-registry, lint-spec

2. **Pages Deployment**: Workflow will create gh-pages branch
   - Check Settings → Pages to see deployment status
   - Site available at: https://\<org\>.github.io/\<repo\>/

3. **Publishing**: Create a version tag
   - `git tag v0.1.0 && git push origin v0.1.0`
   - publish.yml will run and publish to PyPI, npm
   - (You need PYPI_API_TOKEN and NPM_TOKEN for this to work)

## Daily Operations

### Creating a PR

Use the PR template (automatically appears):
- [ ] Tests added/updated
- [ ] Specification compliance
- [ ] SDK parity (if feature, update all 3 SDKs)
- [ ] Registry updated (if adding circuit)

### Reporting a Bug

Use the bug report template:
- Component: Choose from dropdown
- Description: What broke?
- Reproduction: Steps to reproduce
- Environment: OS, versions, SDK version

### Submitting a Circuit

Use the circuit submission template:
- Circuit ID: `domain/circuit-name@version`
- Domain: healthcare, finance, trade, legal, general
- Proof systems: Which ones does it support?
- JSON descriptor: Must validate against circuit.schema.json
- Test cases: At least 3 (happy path, edge case, invalid input)

## Local Testing

### Run CI checks locally

```bash
# Python tests
cd sdk/python
pip install -e .
pytest tests/ -v

# TypeScript tests
cd sdk/typescript
npm install
npm test

# Go tests
cd sdk/go
go test ./...

# Validate bundles
pip install jsonschema
python .github/scripts/validate_bundles.py

# Validate circuits
python .github/scripts/validate_registry.py
```

### Simulate GitHub Actions (optional)

Install [act](https://github.com/nektos/act):

```bash
# Run all workflows
act

# Run specific workflow
act -j test-python

# Run specific workflow file
act -W .github/workflows/ci.yml
```

## Publishing a Release

1. Update versions in SDKs:
   - `sdk/python/setup.py` → version = "X.Y.Z"
   - `sdk/typescript/package.json` → "version": "X.Y.Z"
   - `sdk/go/go.mod` remains unchanged (published via tags)

2. Commit and tag:
   ```bash
   git commit -am "Bump version to X.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```

3. publish.yml workflow runs automatically:
   - Builds Python package → publishes to PyPI
   - Builds TypeScript package → publishes to npm
   - Validates Go module → available via git tag

## Troubleshooting

**Q: CI fails with "SPEC.md not found"**
A: The workflow expects SPEC.md in the repository root

**Q: CI fails with "No tests found"**
A: Ensure sdk/python/tests/, sdk/typescript/tests/ exist with test files

**Q: Publishing fails with "unauthorized"**
A: Check PYPI_API_TOKEN or NPM_TOKEN secrets are set in repository settings

**Q: GitHub Pages not deploying**
A: Ensure docs/ folder exists or ui/index.html is present in root

**Q: Validation scripts fail locally**
A: Install jsonschema: `pip install jsonschema`

## Full Documentation

See `.github/README.md` for comprehensive documentation including:
- Detailed workflow descriptions
- Action version information
- Validation script internals
- Configuration options
- Security considerations

## File Summary

| File | Lines | Purpose |
|------|-------|---------|
| ci.yml | 162 | Main CI pipeline (test + validate) |
| publish.yml | 102 | Publish SDKs to registries |
| pages.yml | 68 | GitHub Pages deployment |
| bug_report.yml | 87 | Bug report issue template |
| circuit_submission.yml | 157 | Circuit submission template |
| PULL_REQUEST_TEMPLATE.md | 84 | PR checklist |
| validate_bundles.py | 146 | Validate test bundles |
| validate_registry.py | 131 | Validate circuits |
| README.md | 381 | Full documentation |
| **TOTAL** | **1,318** | |

---

**Questions?** Check `.github/README.md` for comprehensive documentation.
