"""Shared helper for building a TFTDataSource from a CLI-provided name."""

from __future__ import annotations

from tft_set_info_tools.datasource import DefaultDataSource, TFTDataSource
from tft_set_info_tools.datasource.cdragon import CDragonDataSource
from tft_set_info_tools.datasource.default import REGISTRY as _CONCRETE_REGISTRY

REGISTRY: dict[str, type[TFTDataSource]] = {
    **_CONCRETE_REGISTRY,
    "default": DefaultDataSource,
}


def build_source(name: str | None, *, patch: str | None = None) -> TFTDataSource:
    """Build a TFTDataSource from a registry name (local/gcp/cdragon/default).

    None (unspecified) is treated the same as "default": a DefaultDataSource,
    which resolves its own source from TFT_DATASOURCE_ORDER.

    ``patch`` selects the Community Dragon patch/version to fetch and is only
    valid when ``name`` is "cdragon".
    """
    name = name or "default"
    try:
        cls = REGISTRY[name]
    except KeyError:
        valid = ", ".join(sorted(REGISTRY))
        raise ValueError(f"Unknown data source {name!r}; expected one of: {valid}") from None
    if patch is not None:
        if cls is not CDragonDataSource:
            raise ValueError(f"--src-patch is only valid for the cdragon data source, not {name!r}")
        return CDragonDataSource(patch=patch)
    return cls()
