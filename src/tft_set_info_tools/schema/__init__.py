"""Classification vocabulary and per-source extraction logic for TFT set metadata.

Different TFTDataSource origins (Community Dragon, MetaTFT, ...) publish the same
content under different json shapes. A SetDataSchema knows how to locate a given
set's units/traits/items/augments within one such shape, and how to classify an
item/augment against ItemType/AugmentTier.

This package has no dependency on `datasource` or `set_data` -- both of those
depend on it instead, so it can be imported freely from either without risking
a circular import.
"""

from tft_set_info_tools.schema.base import SetDataSchema
from tft_set_info_tools.schema.cdragon import CDragonSchema
from tft_set_info_tools.schema.metatft import MetaTFTSchema
from tft_set_info_tools.schema.models import (
    Augment,
    ExtractedSet,
    Item,
    TraitTier,
    Unit,
    UnitTrait,
)
from tft_set_info_tools.schema.registry import SCHEMAS, detect_schema
from tft_set_info_tools.schema.vocab import (
    AUGMENT_HASH_MARKER,
    AugmentTier,
    Component,
    ItemType,
    TraitStyle,
)

__all__ = [
    "AUGMENT_HASH_MARKER",
    "ItemType",
    "AugmentTier",
    "Component",
    "TraitStyle",
    "TraitTier",
    "Augment",
    "Item",
    "Unit",
    "UnitTrait",
    "ExtractedSet",
    "SetDataSchema",
    "CDragonSchema",
    "MetaTFTSchema",
    "SCHEMAS",
    "detect_schema",
]
