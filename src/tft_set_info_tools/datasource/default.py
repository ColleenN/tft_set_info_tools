"""A read-only TFTDataSource that reads from the first working source in a priority order."""

from __future__ import annotations

import os
from types import TracebackType

from tft_set_info_tools.datasource.base import TFTDataSource
from tft_set_info_tools.datasource.cdragon import CDragonDataSource
from tft_set_info_tools.datasource.gcp import GCPDataSource
from tft_set_info_tools.datasource.local import LocalDataSource
from tft_set_info_tools.datasource.metatft import MetaTFTDataSource
from tft_set_info_tools.schema import SetDataSchema

REGISTRY: dict[str, type[TFTDataSource]] = {
    "local": LocalDataSource,
    "gcp": GCPDataSource,
    "cdragon": CDragonDataSource,
    "metatft": MetaTFTDataSource,
}


class DefaultDataSource(TFTDataSource):
    """Reads via the first working source named in a priority order.

    Order is a comma-separated list of registry names (e.g. "local,gcp,cdragon"),
    taken from the TFT_DATASOURCE_ORDER env var (defaults to "gcp,cdragon,local").

    read() tries each name in turn, skipping one that's unconfigured (its
    constructor raises ValueError) or fails to read (network error, missing
    file, malformed response, etc.), and caches whichever source works. (This
    only ever happens once per instance — TFTDataSource.read() caches the
    returned data across calls, so _read() below won't run again unless
    force=True is passed, which re-runs the whole fallback search.)

    write() is not supported, since there's no single unambiguous backend to
    write to across an ordered list of sources.
    """

    ORDER_ENV_VAR = "TFT_DATASOURCE_ORDER"
    DEFAULT_ORDER = "gcp,cdragon,local"

    def __init__(self):
        super().__init__()
        order = os.environ.get(self.ORDER_ENV_VAR, self.DEFAULT_ORDER)
        self._names = [n.strip() for n in order.split(",") if n.strip()]
        if not self._names:
            raise ValueError(f"No data source order specified; set {self.ORDER_ENV_VAR}")
        self._resolved: TFTDataSource | None = None

    def get_schema(self) -> type[SetDataSchema] | None:
        """Proxies to whichever concrete source resolved during the last read().

        None until a successful read() has resolved a source (or if that
        source is itself a generic passthrough with no fixed schema).
        """
        return self._resolved.get_schema() if self._resolved is not None else None

    def _read(self) -> dict:
        if self._resolved is not None:
            self._resolved.__exit__(None, None, None)
            self._resolved = None

        errors = []
        for name in self._names:
            cls = REGISTRY.get(name)
            if cls is None:
                errors.append(f"{name!r} is not a recognized data source")
                continue
            try:
                source = cls()
                source.__enter__()
            except ValueError as exc:
                errors.append(f"{name!r}: not configured ({exc})")
                continue
            try:
                data = source.read()
            except Exception as exc:
                source.__exit__(type(exc), exc, exc.__traceback__)
                errors.append(f"{name!r}: failed to read ({exc})")
                continue
            self._resolved = source
            return data

        raise RuntimeError(
            f"None of the data sources in {self._names} could be read: " + "; ".join(errors)
        )

    def _write(self, data: dict) -> None:
        raise NotImplementedError()

    def __enter__(self) -> DefaultDataSource:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._resolved is not None:
            self._resolved.__exit__(exc_type, exc_value, traceback)
            self._resolved = None
