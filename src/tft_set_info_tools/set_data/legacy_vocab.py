"""Legacy seed CSV column-naming vocabulary, ported byte-for-byte from the
tft_tools seed_gen package.

Unlike the CDragon-hash-tag/api-name vocabulary in schema/cdragon.py and
schema/metatft.py, these aren't about interpreting raw per-source data --
they're about what column name a given ItemType/Component gets in the
legacy seed CSV schema, which is a TFTSetData/seed-generation concern, not
a schema one. Internal to set_data; not re-exported from the package.
"""

from __future__ import annotations

from tft_set_info_tools.schema import Component, ItemType

SUMMON_UNITS = {
    "TFT_TrainingDummy",
    "TFT_BlueGolem",
    "TFT14_SummonLevel2",
    "TFT14_SummonLevel4",
}

ITEM_TYPE_COLUMN_NAMES = {
    ItemType.ARTIFACT: "artifacts",
    ItemType.RADIANT: "radiants",
    ItemType.SUPPORT: "supports",
    ItemType.EMBLEM: "emblems",
    ItemType.COMPONENT: "components",
    ItemType.TG_ITEM: "tg_items",
    ItemType.TAC_ITEM: "tac_items",
}

COMPONENT_COLUMN_NAMES = {
    Component.SWORD: "num_swords",
    Component.VEST: "num_vests",
    Component.PAN: "num_pans",
    Component.BELT: "num_belts",
    Component.ROD: "num_rods",
    Component.CLOAK: "num_cloaks",
    Component.BOW: "num_bows",
    Component.GLOVES: "num_gloves",
    Component.SPATULA: "num_spats",
    Component.TEAR: "num_tears",
}
