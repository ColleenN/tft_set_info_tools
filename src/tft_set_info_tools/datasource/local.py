"""Local-file TFT metadata json data source."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import TracebackType

from tft_set_info_tools.datasource.base import TFTDataSource


class LocalDataSource(TFTDataSource):
    """Reads/writes TFT metadata json from/to a local file.

    ``path`` falls back to the ``TFT_LOCAL_PATH`` environment variable when
    not passed explicitly, so this class can be zero-arg constructed.
    """

    PATH_ENV_VAR = "TFT_LOCAL_PATH"

    def __init__(self, path: str | Path | None = None):
        path = path or os.environ.get(self.PATH_ENV_VAR)
        if not path:
            raise ValueError(
                f"Local file path not specified; pass path= or set {self.PATH_ENV_VAR}"
            )
        self._path = Path(path)

    def read(self) -> dict:
        with self._path.open(encoding="utf-8") as f:
            return json.load(f)

    def write(self, data: dict | TFTDataSource) -> None:
        payload = self._resolve(data)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(payload, f)

    def __enter__(self) -> LocalDataSource:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None
