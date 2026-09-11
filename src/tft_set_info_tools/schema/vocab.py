"""Classification vocabulary shared by every SetDataSchema."""

from __future__ import annotations

from enum import Enum

AUGMENT_HASH_MARKER = "{b72bd3bf}"


class ItemType(Enum):
    """TFT item categories, keyed by the hash tag CDragon uses to mark them."""

    COMPONENT = ("component", "component")
    SUPPORT = ("support", "{27557a09}")
    ARTIFACT = ("artifact", "{44ace175}")
    RADIANT = ("radiant", "{6ef5c598}")
    EMBLEM = ("emblem", "{ebcd1bac}")
    TAC_ITEM = ("tac_item", "{d304f83b}")
    TG_ITEM = ("tg_item", "{218b53a5}")

    def __init__(self, type_name: str, type_hash: str):
        self.type_name = type_name
        self.type_hash = type_hash


class Component(Enum):
    """The 10 basic TFT component items, common to every set.

    Unlike ItemType, no member carries a source-specific vocabulary value --
    each concrete SetDataSchema owns its own raw-api-name-to-Component
    mapping (see get_component()), since sources aren't consistent about
    what api name a given component uses.
    """

    SWORD = "sword"
    VEST = "vest"
    PAN = "pan"
    BELT = "belt"
    ROD = "rod"
    CLOAK = "cloak"
    BOW = "bow"
    GLOVES = "gloves"
    SPATULA = "spatula"
    TEAR = "tear"


class AugmentTier(Enum):
    """TFT augment tiers, keyed by the hash tag CDragon uses to mark them."""

    SILVER = "{d11fd6d5}"
    GOLD = "{ce1fd21c}"
    PRISMATIC = "{cf1fd3af}"


class TraitStyle(Enum):
    """TFT trait activation styles, keyed by the numeric code raw trait effects use."""

    BRONZE = 1
    SILVER = 3
    LEGENDARY = 4
    GOLD = 5
    PRISMATIC = 6
