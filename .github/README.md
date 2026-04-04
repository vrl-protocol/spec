# VRL GitHub Actions CI/CD Pipeline

Complete automated build, test, and deployment pipeline for the Verifiable Reality Layer project.

## Workflows

### 1. `ci.yml` — Continuous Integration (Main Pipeline)

**Trigger:** `push` to `main` and all `pull_request` events

**Jobs (run in parallel where possible):**

#### test-python
Tests the Python SDK (sdk/python)
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4
  - actions/setup-python@v5 (Python 3.11)
  - pip install -e sdk/python
  - pytest sdk/python/tests/ -v --cov=vrl
  - Upload coverage to Codecov

#### test-typescript
Tests the TypeScript SDK (sdk/typescript)
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4
  - actions/setup-node@v4 (Node 20)
  - cd sdk/typescript && npm install && npm test

#### test-go
Tests the Go SDK (sdk/go)
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4
  - actions/setup-go@v5 (Go 1.21)
  - cd sdk/go && go test ./... -v

#### validate-spec
Validates test bundles against the JSON Schema in SPEC.md §17
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4
  - actions/setup-python@v5 (Python 3.11)
  - pip install jsonschema
  - python .github/scripts/validate_bundles.py
  - Validates: verifier/test_bundles/*.json

#### validate-registry
Validates circuit definitions against the registry schema
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4
  - actions/setup-python@v5 (Python 3.11)
  - pip install jsonschema
  - python .github/scripts/validate_registry.py
  - Validates: registry/circuits/*.json

#### lint-spec
Verifies specification document integrity
- **Runner:** ubuntu-latest
- **Checks:**
  - SPEC.md exists
  - All required sections present (§2 through §17)
  - README.md exists and is readable
  - Links in README.md to SPEC sections validated

### 2. `publish.yml` — Package Publishing

**Trigger:** `push` of version tags matching `v*` (e.g., v0.1.0)

**Jobs:**

#### publish-python
Publishes Python SDK to PyPI
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4
  - actions/setup-python@v5
  - Builds: cd sdk/python && python -m build
  - Uses: pypa/gh-action-pypi-publish@release/v1
  - **Secret:** TWINE_TOKEN or PYPI_API_TOKEN

#### publish-npm
Publishes TypeScript SDK to npm
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4
  - actions/setup-node@v4 (Node 20)
  - Builds: cd sdk/typescript && npm install && npm run build
  - Publishes: npm publish --access public
  - **Secret:** NPM_TOKEN

#### publish-go
Publishes Go SDK
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4 (with full history for tags)
  - actions/setup-go@v5 (Go 1.21)
  - Validates: go mod tidy, go mod verify, go test
  - **Note:** Go modules are published directly via Git tags to github.com/vrl-protocol/spec/sdk/go

### 3. `pages.yml` — GitHub Pages Deployment

**Trigger:** `push` to `main` branch

**Jobs:**

#### build
Prepares documentation for deployment
- **Runner:** ubuntu-latest
- **Actions:**
  - actions/checkout@v4
  - Copies docs/ folder to _site/ (or uses ui/index.html if no docs/)
  - Includes README.md and SPEC.md in _site/
  - Uses: actions/upload-pages-artifact@v2

#### deploy
Deploys to GitHub Pages
- **Runner:** ubuntu-latest
- **Actions:**
  - Uses: actions/deploy-pages@v2
  - Environment: github-pages

**Site URL:** `https://<org>.github.io/spec/` (depends on repository settings)

## Issue Templates

### `.github/ISSUE_TEMPLATE/bug_report.yml`

Structured bug report template for:
- Spec issues
- SDK bugs (Python, TypeScript, Go)
- Verifier errors
- Registry problems

**Fields:**
- Component (dropdown)
- Description
- Steps to reproduce
- Environment
- Logs and error messages
- Verification checklist

### `.github/ISSUE_TEMPLATE/circuit_submission.yml`

Circuit registry submission template for VRL Circuit Registry contributions.

**Fields:**
- Circuit ID (domain/name@version)
- Domain (dropdown)
- Description
- Proof systems supported
- Certification tier requested
- Schema JSON (must validate against circuit.schema.json)
- Test cases (at least 3)
- Specification compliance checklist

## Pull Request Template

### `.github/PULL_REQUEST_TEMPLATE.md`

Comprehensive PR checklist covering:
- Specification compliance (SPEC.md §2-§17)
- SDK parity (if feature addition, all 3 SDKs updated)
- Registry updates (if applicable)
- Documentation updates
- Test coverage
- No breaking changes (or major version bump justified)

## Validation Scripts

### `.github/scripts/validate_bundles.py`

**Purpose:** Validate all test bundles against the JSON Schema in SPEC.md §17

**Usage:**
```bash
python .github/scripts/validate_bundles.py
```

**Process:**
1. Reads SPEC.md and extracts JSON Schema from §17
2. Iterates through verifier/test_bundles/*.json
3. Validates each bundle against the schema
4. Prints PASS/FAIL for each bundle
5. Exits with code 0 on success, 1 if any validations fail

**Output Example:**
```
✓ Extracted JSON Schema from SPEC.md §17

Validating 3 bundle(s):
✓ PASS: valid_trade.json
✓ PASS: valid_tee.json
✗ FAIL: tampered.json - Schema validation error
```

### `.github/scripts/validate_registry.py`

**Purpose:** Validate all circuit definitions against registry/schema/circuit.schema.json

**Usage:**
```bash
python .github/scripts/validate_registry.py
```

**Process:**
1. Loads registry/schema/circuit.schema.json
2. Iterates through registry/circuits/*.json
3. Validates each circuit against the schema
4. Checks registry.json index consistency
5. Prints PASS/FAIL for each circuit
6. Exits with code 0 on success, 1 if any validations fail

**Output Example:**
```
✓ Loaded schema from registry/schema/circuit.schema.json

Validating 8 circuit(s):
✓ PASS: trade/import-landed-cost@1.0.0
✓ PASS: trade/import-landed-cost@2.0.0
✓ PASS: healthcare/clinical-decision-support@1.0.0
...
```

## Secrets Required

Set these secrets in GitHub repository settings:

| Secret | Used By | Purpose |
|--------|---------|---------|
| `TWINE_TOKEN` or `PYPI_API_TOKEN` | publish-python | PyPI authentication |
| `NPM_TOKEN` | publish-npm | npm registry authentication |
| (none) | publish-go | Git tag-based publishing |

## Configuration

### Python SDK
- **Location:** sdk/python/
- **Setup:** setup.py with setuptools
- **Tests:** pytest (sdk/python/tests/)
- **Coverage:** pytest-cov

### TypeScript SDK
- **Location:** sdk/typescript/
- **Build:** npm run build (tsc)
- **Tests:** npm test (node --test)
- **Config:** tsconfig.json, package.json

### Go SDK
- **Location:** sdk/go/
- **Module:** github.com/vrl-protocol/spec/sdk/go
- **Tests:** go test ./...
- **Minimum:** Go 1.21

### Specification
- **File:** SPEC.md (at root)
- **Sections:** 17 major sections (§1-§17)
- **Schema:** JSON Schema in §17
- **Test bundles:** verifier/test_bundles/

### Registry
- **Index:** registry/registry.json
- **Circuits:** registry/circuits/*.json
- **Schema:** registry/schema/circuit.schema.json
- **Submission:** registry/SUBMISSION.md

## Local Testing

### Run CI checks locally

```bash
# Test Python SDK
cd sdk/python
pip install -e .
pytest tests/ -v

# Test TypeScript SDK
cd sdk/typescript
npm install
npm test

# Test Go SDK
cd sdk/go
go test ./...

# Validate bundles
pip install jsonschema
python .github/scripts/validate_bundles.py

# Validate registry
python .github/scripts/validate_registry.py
```

### Simulate CI environment

Use `act` to run GitHub Actions workflows locally:

```bash
# Install act: https://github.com/nektos/act
act

# Run specific workflow
act -j test-python

# With specific event
act push -b main
```

## Troubleshooting

### CI Failures

**test-python fails:**
- Verify sdk/python/setup.py exists and is valid
- Check that tests/ directory exists
- Ensure Python 3.11 compatibility

**test-typescript fails:**
- Verify sdk/typescript/package.json has test script
- Check tsconfig.json is valid
- Node 20 required

**test-go fails:**
- Verify sdk/go/go.mod exists
- Check go.sum is committed if present
- Go 1.21 required

**validate-spec fails:**
- Ensure SPEC.md exists in repository root
- Check §17 contains valid JSON schema block
- Verify verifier/test_bundles/*.json files are valid JSON

**validate-registry fails:**
- Ensure registry/schema/circuit.schema.json exists
- Check all circuits/*.json files have circuit_id
- Verify each circuit matches schema structure

**publish fails:**
- Check secrets are set correctly (PYPI_API_TOKEN, NPM_TOKEN)
- Ensure tag follows semver (v0.1.0, v1.0.0, etc.)
- Verify package versions match tag version

### Pages deployment fails:**
- Ensure docs/ folder exists OR ui/index.html exists
- Check for permission issues in GitHub Pages settings
- Verify branch is set to "GitHub Actions" in Pages settings

## Maintenance

### Regular Tasks

1. **Weekly:** Monitor test coverage trends
2. **Monthly:** Update action versions (check for security updates)
3. **Per release:** Ensure all three SDKs are updated in parallel
4. **Per sprint:** Review and triage CI failures

### Action Versions

All actions are pinned to specific versions for stability:
- actions/checkout@v4
- actions/setup-python@v5
- actions/setup-node@v4
- actions/setup-go@v5
- actions/upload-pages-artifact@v2
- actions/deploy-pages@v2
- codecov/codecov-action@v3
- pypa/gh-action-pypi-publish@release/v1

Update according to your security policy.

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [VRL Specification](../SPEC.md)
- [VRL README](../README.md)
- [Python SDK](../sdk/python/)
- [TypeScript SDK](../sdk/typescript/)
- [Go SDK](../sdk/go/)
- [Circuit Registry](../registry/)
