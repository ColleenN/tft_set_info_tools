"""Abstract base class for TFT metadata json data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from tft_set_info_tools.schema import SetDataSchema


class TFTDataSource(ABC):
    """Interface for reading/writing TFT metadata json from/to a source.

    read() caches its result the first time it succeeds; subsequent calls
    return the cached data without re-fetching, unless force=True is passed.
    write() updates the cache to the data just written, so a following
    read() reflects it without re-fetching from the source. Concrete
    subclasses implement the actual I/O in _read()/_write() rather than
    overriding read()/write() directly.
    """

    schema = None

    def __init__(self):
        self._cache: dict | None = None

    def get_schema(self) -> type[SetDataSchema] | None:
        """The SetDataSchema this source's data is expected to match, if known.

        Origin sources that always fetch from one particular endpoint (e.g.
        CDragonDataSource, MetaTFTDataSource) know their shape up front and
        override this. Generic passthrough sources (LocalDataSource,
        GCPDataSource) can hold data copied from any origin, so they can't
        declare one -- None here means "detect the shape at read time"
        (see schema.detect_schema).
        """
        return self.schema

    def read(self, force: bool = False) -> dict:
        if force or self._cache is None:
            self._cache = self._read()
        return self._cache

    @abstractmethod
    def _read(self) -> dict:
        raise NotImplementedError

    def write(self, data: dict | TFTDataSource) -> None:
        data_dict = data.read() if isinstance(data, TFTDataSource) else data
        self._write(data_dict)
        self._cache = data_dict

    @abstractmethod
    def _write(self, data: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def __enter__(self) -> TFTDataSource:
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError

