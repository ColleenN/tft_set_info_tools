# Publishing `tft_set_info_tools` to GCP Artifact Registry

## 1. Deploy the Python registry (Terraform)

Infra is defined in `D:\CODE_REPOS\tft_data_infra\terraform`. A `google_artifact_registry_repository`
resource (`python_registry`, format `PYTHON`) has been added alongside the existing Docker registry.

```bash
cd D:/CODE_REPOS/tft_data_infra/terraform
terraform plan   # with your usual -var-file or CI var source
terraform apply
```

This creates a repository named `tft-data-python-registry` (var `python_artifact_registry_name`)
in project `tft-data-463022`, region `var.region`.

## 2. Install publishing tools

From `D:\tft_set_info_tools`:

```bash
pip install keyring keyrings.google-artifactregistry-auth twine
```

The `keyrings.google-artifactregistry-auth` plugin authenticates using your existing
`gcloud auth` credentials — no manual token needed.

## 3. Build the package

```bash
python -m build
```

## 4. Upload to the registry

```bash
twine upload --repository-url https://<region>-python.pkg.dev/tft-data-463022/tft-data-python-registry/ dist/*
```

Replace `<region>` with the deployed `var.region` value.

### Shortcuts

**Makefile** — builds and uploads in one step:
```bash
make publish GCP_REGION=<region>
```
(`GCP_PROJECT_ID` and `GCP_ARTIFACT_REPO` default to the values above; override if needed.)

**`.pypirc`** — avoid typing `--repository-url` every time. Copy `.pypirc.example` to
`~/.pypirc` (or `%USERPROFILE%\.pypirc` on Windows), fill in `<region>`, then:
```bash
twine upload --repository gcp-artifact dist/*
```

## 5. Installing the package elsewhere

Add an extra index URL pointing at the registry's `simple` endpoint, and install the same
keyring auth plugin so pip can authenticate:

```
https://<region>-python.pkg.dev/tft-data-463022/tft-data-python-registry/simple/
```

```bash
pip install keyring keyrings.google-artifactregistry-auth
pip install tft-set-info-tools --extra-index-url https://<region>-python.pkg.dev/tft-data-463022/tft-data-python-registry/simple/
```
