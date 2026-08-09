"""Shared test fixtures/helpers."""

from __future__ import annotations

from types import TracebackType

from tft_set_info_tools.datasource import TFTDataSource


class DictDataSource(TFTDataSource):
    """A TFTDataSource wrapping an in-memory dict, for tests that don't need real I/O."""

    def __init__(self, data: dict):
        super().__init__()
        self._data = data

    def _read(self) -> dict:
        return self._data

    def _write(self, data: dict) -> None:
        self._data = data

    def __enter__(self) -> DictDataSource:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None
