"""MetaTFT TFT metadata json data source."""

from __future__ import annotations

import os
from types import TracebackType

from tft_set_info_tools.datasource.base import TFTDataSource
from tft_set_info_tools.schema import MetaTFTSchema


class MetaTFTDataSource(TFTDataSource):
    """Read-only source that fetches TFT metadata json from MetaTFT's lookup files.

    MetaTFT publishes one file per set (e.g. "TFTSet18_pbe_en_us.json"), unlike
    CDragon's single file covering every set, so there's no generic patch/set
    template to build a URL from here -- ``url`` defaults to the exact url given
    when this source was added, and falls back to the ``TFT_METATFT_URL``
    environment variable when not passed explicitly.
    """

    DEFAULT_URL = "https://data.metatft.com/lookups/TFTSet18_pbe_en_us.json"
    URL_ENV_VAR = "TFT_METATFT_URL"

    schema = MetaTFTSchema

    def __init__(self, url: str | None = None):
        super().__init__()
        self._url = url or os.environ.get(self.URL_ENV_VAR) or self.DEFAULT_URL
        self._client = None

    @property
    def url(self) -> str:
        return self._url

    def _read(self) -> dict:
        import httpx

        response = self._client.get(self._url) if self._client else httpx.get(self._url)
        response.raise_for_status()
        return response.json()

    def _write(self, data: dict) -> None:
        raise NotImplementedError("MetaTFTDataSource is read-only.")

    def __enter__(self) -> MetaTFTDataSource:
        import httpx

        self._client = httpx.Client()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
