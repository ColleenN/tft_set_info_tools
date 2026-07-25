"""A TFTDataSource that delegates to the first working source in a priority order."""

from __future__ import annotations

import os
from types import TracebackType

from tft_set_info_tools.datasource.base import TFTDataSource
from tft_set_info_tools.datasource.cdragon import CDragonDataSource
from tft_set_info_tools.datasource.gcp import GCPDataSource
from tft_set_info_tools.datasource.local import LocalDataSource

REGISTRY: dict[str, type[TFTDataSource]] = {
    "local": LocalDataSource,
    "gcp": GCPDataSource,
    "cdragon": CDragonDataSource,
}


class DefaultDataSource(TFTDataSource):
    """Reads/writes via the first working source named in a priority order.

    Order is a comma-separated list of registry names (e.g. "local,gcp,cdragon"),
    taken from the ``order`` argument or the TFT_DATASOURCE_ORDER env var.

    read() tries each name in turn, skipping one that's unconfigured (its
    constructor raises ValueError) or fails to read (network error, missing
    file, malformed response, etc.), and caches whichever source works so
    later read()/write() calls on this instance reuse it directly.

    write() picks the first *configured* name (without probing whether it's
    currently readable) and delegates to it — a failed write is not retried
    against a different source, since retrying a mutation across backends
    risks partial or duplicate writes.
    """

    ORDER_ENV_VAR = "TFT_DATASOURCE_ORDER"

    def __init__(self):
        order = os.environ.get(self.ORDER_ENV_VAR, "gcp,cdragon,local")
        self._names = [n.strip() for n in order.split(",") if n.strip()]
        if not self._names:
            raise ValueError(
                f"No data source order specified; pass order= or set {self.ORDER_ENV_VAR}"
            )
        self._resolved: TFTDataSource | None = None

    def read(self) -> dict:

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
