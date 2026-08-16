"""Legacy CDragon-hash-tag vocabulary, ported byte-for-byte from the tft_tools
seed_gen package.

Unlike ItemType/AugmentTier (schema.vocab), these aren't (yet) modeled
polymorphically per-source -- TFTSetData.get_equippable_items() only
recognizes CDragon's hash tags/api names. Internal to set_data; not
re-exported from the package.
"""

from __future__ import annotations

from tft_set_info_tools.schema import ItemType

SUMMON_UNITS = {
    "TFT_TrainingDummy",
    "TFT_BlueGolem",
    "TFT14_SummonLevel2",
    "TFT14_SummonLevel4",
}

EQUIPPABLE_ITEM_HASHES = {
    "component",
    "{27557a09}",
    "{44ace175}",
    "{d304f83b}",
    "{7ea41d13}",
    "{6ef5c598}",
    "{ebcd1bac}",
    "{eda79d90}",
    "{218b53a5}",
    "{a3eeef8b}",
    "{b73b012f}",
}

NON_EQUIPPABLE_ITEM_HASHES = {
    "Consumable",
    "TFT_Consumable_ItemRemover",
    "TFT_Consumable_ItemReroller",
    "{b4fe26c6}",
    "{fb608fdb}",
    "{56b1acc8}",
}

COMPONENT_NAME_MAP = {
    "TFT_Item_BFSword": "num_swords",
    "TFT_Item_ChainVest": "num_vests",
    "TFT_Item_FryingPan": "num_pans",
    "TFT_Item_GiantsBelt": "num_belts",
    "TFT_Item_NeedlesslyLargeRod": "num_rods",
    "TFT_Item_NegatronCloak": "num_cloaks",
    "TFT_Item_RecurveBow": "num_bows",
    "TFT_Item_SparringGloves": "num_gloves",
    "TFT_Item_Spatula": "num_spats",
    "TFT_Item_TearOfTheGoddess": "num_tears",
    "DA_Component_BFSword": "num_swords",
    "DA_Component_ChainVest": "num_vests",
    "DA_Component_FryingPan": "num_pans",
    "DA_Component_GiantsBelt": "num_belts",
    "DA_Component_NeedlesslyLargeRod": "num_rods",
    "DA_Component_NegatronCloak": "num_cloaks",
    "DA_Component_RecurveBow": "num_bows",
    "DA_Component_SparringGloves": "num_gloves",
    "DA_Component_Spatula": "num_spats",
    "DA_Component_TearOfTheGoddess": "num_tears",
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
