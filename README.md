# tft_set_info_tools

Shared tools for working with TFT set info, packaged for reuse across other Python projects.

## Install (editable, for local development)

```bash
pip install -e ".[dev]"
```

Then from another local project's venv:

```bash
pip install -e D:/tft_set_info_tools
```

## Test

```bash
pytest
```

## Build a distributable wheel/sdist

```bash
python -m build
```

Output lands in `dist/`.
