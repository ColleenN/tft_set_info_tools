"""Converts TFT metadata json into a structured object for a single set."""

from tft_set_info_tools.schema import AugmentTier, ItemType, TraitStyle, TraitTier
from tft_set_info_tools.set_data.set_data import TFTSetData

__all__ = [
    "TFTSetData",
    "ItemType",
    "AugmentTier",
    "TraitStyle",
    "TraitTier",
]
