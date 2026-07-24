"""Abstract base class for TFT metadata json data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType


class TFTDataSource(ABC):
    """Interface for reading/writing TFT metadata json from/to a source."""

    @abstractmethod
    def read(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def write(self, data: dict | TFTDataSource) -> None:
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

    @staticmethod
    def _resolve(data: dict | TFTDataSource) -> dict:
        return data.read() if isinstance(data, TFTDataSource) else data
