import json
from dataclasses import FrozenInstanceError, asdict

import pytest

from tests.conftest import DictDataSource
from tft_set_info_tools.datasource import CDragonDataSource
from tft_set_info_tools.set_data import TFTSetData, build_set_bundle

SWORD = {"apiName": "TFT_Item_BFSword", "name": "B.F. Sword", "icon": "sword.tex", "tags": ["component"]}
EDGE = {
    "apiName": "TFT_Item_InfinityEdge",
    "name": "Infinity Edge",
    "desc": "Abilities can crit.",
    "icon": "edge.tex",
    "composition": ["TFT_Item_BFSword", "TFT_Item_SparringGloves"],
    "effects": {"CritChance": 35},
    "tags": ["{7ea41d13}"],
    "unique": False,
}
EMBLEM = {
    "apiName": "TFT12_Item_ChronoEmblem",
    "name": "Chrono Emblem",
    "icon": "emblem.tex",
    "composition": ["TFT_Item_Spatula", "TFT_Item_BFSword"],
    "incompatibleTraits": ["TFT12_Chrono"],
    "tags": ["{ebcd1bac}"],
    "unique": True,
}
WISP = {"apiName": "TFT12_Wisp", "name": "Wisp", "tags": ["{5b609ae2}"]}
AUGMENT = {
    "apiName": "TFT12_Augment_ChronoCrest",
    "name": "Chrono Crest",
    "desc": "Gain a Chrono Emblem.",
    "icon": "crest.tex",
    "associatedTraits": ["TFT12_Chrono"],
    "effects": {},
    "tags": ["{ce1fd21c}"],
}
ZILEAN = {
    "name": "Zilean",
    "apiName": "TFT12_Zilean",
    "cost": 2,
    "role": "APCaster",
    "traits": ["Chrono"],
    "icon": "zilean_splash.tex",
    "squareIcon": "zilean_square.tex",
    "tileIcon": "zilean_tile.tex",
    "stats": {"hp": 550.0},
    "ability": {
        "name": "Time Bomb",
        "desc": "Deal @Damage@ damage.",
        "icon": "zilean_q.tex",
        "variables": [{"name": "Damage", "value": [0, 200, 300, 450]}],
    },
}
AHRI = {"name": "Ahri", "apiName": "TFT12_Ahri", "cost": 1, "traits": ["Chrono"], "stats": {}}
DUMMY = {"name": "TrainingDummy", "apiName": "TFT_TrainingDummy", "cost": 0, "traits": []}
CHRONO = {
    "name": "Chrono",
    "apiName": "TFT12_Chrono",
    "desc": "(@MinUnits@) Gain attack speed.",
    "icon": "chrono.tex",
    "effects": [
        {"minUnits": 2, "maxUnits": 3, "style": 1, "variables": {"AS": 0.1}},
        {"minUnits": 4, "maxUnits": 25000, "style": 5, "variables": {"AS": 0.3}},
    ],
}


def make_raw(team_planner_codes=None):
    raw = {
        "items": [SWORD, EDGE, EMBLEM, WISP, AUGMENT],
        "setData": [
            {
                "number": 12,
                "mutator": "TFTSet12",
                "items": [
                    "TFT_Item_BFSword",
                    "TFT_Item_InfinityEdge",
                    "TFT12_Item_ChronoEmblem",
                    "TFT12_Wisp",
                ],
                "augments": ["TFT12_Augment_ChronoCrest"],
                "champions": [ZILEAN, AHRI, DUMMY],
                "traits": [CHRONO],
            }
        ],
    }
    if team_planner_codes is not None:
        raw[CDragonDataSource.TEAM_PLANNER_CODES_KEY] = team_planner_codes
    return raw


def bundle(raw):
    """The bundle as plain dicts, the way it's serialized."""
    return asdict(build_set_bundle(TFTSetData(DictDataSource(raw), set_num=12)))


def test_champions_are_shop_units_with_icons_ability_and_trait_api_names():
    zilean, ahri = bundle(make_raw())["champions"]

    assert zilean == {
        "api_name": "TFT12_Zilean",
        "name": "Zilean",
        "cost": 2,
        "role": "APCaster",
        "traits": ["TFT12_Chrono"],
        "icon": "zilean_splash.tex",
        "square_icon": "zilean_square.tex",
        "tile_icon": "zilean_tile.tex",
        "ability": {
            "name": "Time Bomb",
            "desc": "Deal @Damage@ damage.",
            "icon": "zilean_q.tex",
            "variables": {"Damage": [0, 200, 300, 450]},
        },
        "stats": {"hp": 550.0},
        "team_planner_id": 2,
    }
    assert ahri["ability"] == {"name": None, "desc": None, "icon": None, "variables": {}}
    assert ahri["role"] is None


def test_team_planner_ids_default_to_version_1_order():
    result = bundle(make_raw())

    assert result["team_planner_version"] == 1
    assert {c["api_name"]: c["team_planner_id"] for c in result["champions"]} == {
        "TFT12_Ahri": 1,
        "TFT12_Zilean": 2,
    }


def test_team_planner_ids_use_bundled_version_2_codes():
    codes = {
        "TFTSet12": [
            {"character_id": "TFT12_Ahri", "team_planner_code": 1041},
            {"character_id": "TFT12_Zilean", "team_planner_code": 1055},
        ]
    }
    result = bundle(make_raw(codes))

    assert result["team_planner_version"] == 2
    assert {c["api_name"]: c["team_planner_id"] for c in result["champions"]} == {
        "TFT12_Ahri": 1041,
        "TFT12_Zilean": 1055,
    }


def test_traits_keep_icon_desc_and_every_tier():
    [chrono] = bundle(make_raw())["traits"]

    assert chrono == {
        "api_name": "TFT12_Chrono",
        "name": "Chrono",
        "desc": "(@MinUnits@) Gain attack speed.",
        "icon": "chrono.tex",
        "tiers": [
            {"min_units": 2, "max_units": 3, "style": 1, "variables": {"AS": 0.1}},
            {"min_units": 4, "max_units": 25000, "style": 5, "variables": {"AS": 0.3}},
        ],
    }


def test_items_are_equippable_with_recipes_and_types():
    items = {i["api_name"]: i for i in bundle(make_raw())["items"]}

    assert set(items) == {"TFT_Item_BFSword", "TFT_Item_InfinityEdge", "TFT12_Item_ChronoEmblem"}
    assert items["TFT_Item_BFSword"]["types"] == ["component"]
    assert items["TFT_Item_BFSword"]["composition"] == []
    assert items["TFT_Item_InfinityEdge"] == {
        "api_name": "TFT_Item_InfinityEdge",
        "name": "Infinity Edge",
        "desc": "Abilities can crit.",
        "icon": "edge.tex",
        "types": [],
        "composition": ["TFT_Item_BFSword", "TFT_Item_SparringGloves"],
        "unique": False,
        "trait_granted": None,
        "effects": {"CritChance": 35},
    }
    assert items["TFT12_Item_ChronoEmblem"]["types"] == ["emblem"]
    assert items["TFT12_Item_ChronoEmblem"]["trait_granted"] == "TFT12_Chrono"
    assert items["TFT12_Item_ChronoEmblem"]["unique"] is True


def test_augments_carry_tier_and_associated_traits():
    assert bundle(make_raw())["augments"] == [
        {
            "api_name": "TFT12_Augment_ChronoCrest",
            "name": "Chrono Crest",
            "desc": "Gain a Chrono Emblem.",
            "icon": "crest.tex",
            "tier": "gold",
            "associated_traits": ["TFT12_Chrono"],
            "effects": {},
        }
    ]


def test_bundle_is_json_serializable():
    result = bundle(make_raw())

    assert json.loads(json.dumps(result)) == result
    assert result["mutator"] == "TFTSet12"


def test_bundle_records_are_frozen():
    result = build_set_bundle(TFTSetData(DictDataSource(make_raw()), set_num=12))

    with pytest.raises(FrozenInstanceError):
        result.champions[0].cost = 5
