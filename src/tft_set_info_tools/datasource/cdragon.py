"""Community Dragon TFT metadata json data source."""

from __future__ import annotations

import os
from types import TracebackType

from tft_set_info_tools.datasource.base import TFTDataSource
from tft_set_info_tools.schema import CDragonSchema


class CDragonDataSource(TFTDataSource):
    """Read-only source that fetches TFT metadata json from Community Dragon.

    ``patch`` falls back to the ``TFT_CDRAGON_PATCH`` environment variable when
    not passed explicitly, so this class can be zero-arg constructed.

    Bundles in the separate Team Planner champion-code json (mutator ->
    champion list, each carrying the numeric ``team_planner_code`` id used
    by v2 Team Planner codes -- see ``TFTSetData.decode_team_planner_code``)
    under the ``TEAM_PLANNER_CODES_KEY`` top-level key, alongside the main
    payload's own ``items``/``setData``/``sets`` keys.
    """

    URL_TEMPLATE = "https://raw.communitydragon.org/{patch}/cdragon/tft/en_us.json"
    TEAM_PLANNER_URL_TEMPLATE = (
        "https://raw.communitydragon.org/{patch}/plugins/rcp-be-lol-game-data/"
        "global/default/v1/tftchampions-teamplanner.json"
    )
    DEFAULT_PATCH = "latest"
    PATCH_ENV_VAR = "TFT_CDRAGON_PATCH"
    TEAM_PLANNER_CODES_KEY = "teamPlannerCodes"

    schema = CDragonSchema

    def __init__(self, patch: str | None = None):
        super().__init__()
        self._patch = patch or os.environ.get(self.PATCH_ENV_VAR) or self.DEFAULT_PATCH
        self._client = None

    @property
    def url(self) -> str:
        return self.URL_TEMPLATE.format(patch=self._patch)

    @property
    def team_planner_url(self) -> str:
        return self.TEAM_PLANNER_URL_TEMPLATE.format(patch=self._patch)

    def _get_json(self, url: str) -> dict:
        import httpx

        response = self._client.get(url) if self._client else httpx.get(url)
        response.raise_for_status()
        return response.json()

    def _read(self) -> dict:
        data = self._get_json(self.url)
        team_planner_codes = self._get_json(self.team_planner_url)
        return {**data, self.TEAM_PLANNER_CODES_KEY: team_planner_codes}

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
