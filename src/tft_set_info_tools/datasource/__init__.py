"""Classes for retrieving TFT metadata json from a particular source."""

from tft_set_info_tools.datasource.base import TFTDataSource
from tft_set_info_tools.datasource.cdragon import CDragonDataSource
from tft_set_info_tools.datasource.default import DefaultDataSource
from tft_set_info_tools.datasource.gcp import GCPDataSource
from tft_set_info_tools.datasource.local import LocalDataSource
from tft_set_info_tools.datasource.metatft import MetaTFTDataSource

__all__ = [
    "TFTDataSource",
    "LocalDataSource",
    "GCPDataSource",
    "CDragonDataSource",
    "MetaTFTDataSource",
    "DefaultDataSource",
]
