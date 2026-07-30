"""Community Dragon TFT metadata json data source."""

from __future__ import annotations

import os
from types import TracebackType

from tft_set_info_tools.datasource.base import TFTDataSource


class CDragonDataSource(TFTDataSource):
    """Read-only source that fetches TFT metadata json from Community Dragon.

    ``patch`` falls back to the ``TFT_CDRAGON_PATCH`` environment variable when
    not passed explicitly, so this class can be zero-arg constructed.
    """

    URL_TEMPLATE = "https://raw.communitydragon.org/{patch}/cdragon/tft/en_us.json"
    DEFAULT_PATCH = "latest"
    PATCH_ENV_VAR = "TFT_CDRAGON_PATCH"

    def __init__(self, patch: str | None = None):
        super().__init__()
        self._patch = patch or os.environ.get(self.PATCH_ENV_VAR) or self.DEFAULT_PATCH
        self._client = None

    @property
    def url(self) -> str:
        return self.URL_TEMPLATE.format(patch=self._patch)

    def _read(self) -> dict:
        import httpx

        response = self._client.get(self.url) if self._client else httpx.get(self.url)
        response.raise_for_status()
        return response.json()

    def _write(self, data: dict) -> None:
        raise NotImplementedError("CDragonDataSource is read-only.")

    def __enter__(self) -> CDragonDataSource:
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
