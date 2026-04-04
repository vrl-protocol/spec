# Publishing vrl-sdk to PyPI

Follow these steps to publish the Python SDK to PyPI.

## Prerequisites

- PyPI account at https://pypi.org
- GitHub repository access with admin permissions

## Step 1: Create PyPI Account

If you don't have a PyPI account:

1. Visit https://pypi.org/account/register/
2. Complete the registration and email verification
3. Save your credentials securely

## Step 2: Generate PyPI API Token

1. Log in to https://pypi.org
2. Click your account name → Account Settings
3. Go to API tokens section
4. Click "Add API token"
5. Set the scope to "Entire account" (or limit to the `vrl-sdk` project if available)
6. Copy the generated token (it won't be displayed again)

## Step 3: Add Token as GitHub Secret

1. Navigate to your GitHub repository
2. Go to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `PYPI_API_TOKEN`
5. Value: Paste the PyPI API token from Step 2
6. Click "Add secret"

## Step 4: Trigger PyPI Publication

1. Create a new release in GitHub:
   - Go to Releases → Draft a new release
   - Tag version: `v0.1.0` (matches version in `pyproject.toml`)
   - Release title: `v0.1.0 - Initial Release`
   - Add release notes describing the SDK
   - Click "Publish release"

2. This automatically triggers the publish workflow in `.github/workflows/publish.yml`

3. The workflow will:
   - Build the distribution package
   - Upload to PyPI using the `PYPI_API_TOKEN` secret
   - Mark the release as complete

## Step 5: Verify Publication

1. Visit https://pypi.org/project/vrl-sdk/
2. Within ~5 minutes of release creation, the package should appear
3. Test installation:

   ```bash
   pip install vrl-sdk==0.1.0
   ```

4. Verify the package loads:

   ```bash
   python -c "import vrl; print(vrl.__version__)"
   ```

## Troubleshooting

- **"Workflow failed"**: Check `.github/workflows/publish.yml` for syntax errors
- **"No module named vrl"**: Ensure `vrl/` directory exists and contains `__init__.py`
- **"Version conflict"**: If `0.1.0` already exists, update the version in `pyproject.toml` and create a new release tag
- **Token expired**: Generate a new token and update the `PYPI_API_TOKEN` secret

## Future Releases

For subsequent releases:

1. Update version in `pyproject.toml` (e.g., `0.2.0`)
2. Update `CHANGELOG.md` or release notes
3. Create and push a new git tag: `git tag v0.2.0`
4. Create a GitHub release for that tag
5. The publish workflow runs automatically

## Security Notes

- Never commit the PyPI token in code
- Rotate tokens periodically
- Use a project-scoped token when possible
- Restrict package upload permissions to CI/CD only
