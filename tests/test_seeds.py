import pytest

from tests.conftest import DictDataSource
from tft_set_info_tools.scripts.seeds import SEED_GENERATORS
from tft_set_info_tools.set_data import TFTSetData


def make_full_base():
    return {
        "items": [
            {
                "apiName": "TFT_Item_RecurveBow",
                "name": "Recurve Bow",
                "tags": ["component"],
                "effects": {},
                "incompatibleTraits": [],
                "unique": False,
                "composition": [],
            },
            {
                "apiName": "TFT_Item_GuinsoosRageblade",
                "name": "Guinsoo's Rageblade",
                "tags": ["{27557a09}"],
                "effects": {"a": 1},
                "incompatibleTraits": [],
                "unique": False,
                "composition": ["TFT_Item_RecurveBow", "TFT_Item_RecurveBow"],
            },
            {
                "apiName": "TFT_Augment_TestAugment",
                "name": "Test Augment",
                "tags": ["{b72bd3bf}", "{d11fd6d5}"],
                "effects": {"x": 1},
                "incompatibleTraits": [],
                "unique": False,
                "composition": [],
            },
        ],
        "setData": [
            {
                "number": 12,
                "mutator": "TFTSet12",
                "name": "Set12",
                "items": ["TFT_Item_RecurveBow", "TFT_Item_GuinsoosRageblade"],
                "augments": ["TFT_Augment_TestAugment"],
                "champions": [
                    {
                        "name": "Zilean",
                        "apiName": "TFT12_Zilean",
                        "cost": 2,
                        "role": "support",
                        "traits": ["Chrono", "Preserver"],
                        "stats": {"hp": 550.0, "mana": 70.0},
                    },
                    {
                        "name": "TrainingDummy",
                        "apiName": "TFT_TrainingDummy",
                        "cost": 0,
                        "role": None,
                        "traits": [],
                        "stats": {"hp": 1000.0, "mana": 0.0},
                    },
                ],
                "traits": [
                    {
                        "name": "Chrono",
                        "apiName": "TFT12_Chrono",
                        "desc": "Chrono desc",
                        "effects": [
                            {"minUnits": 2, "maxUnits": 4, "style": 3},
                            {"minUnits": 4, "maxUnits": 6, "style": 4},
                        ],
                    },
                    {
                        "name": "Preserver",
                        "apiName": "TFT12_Preserver",
                        "desc": "Preserver desc",
                        "effects": [
                            {"minUnits": 1, "maxUnits": 25, "style": 1},
                        ],
                    },
                ],
            }
        ],
    }


@pytest.fixture
def set_data():
    return TFTSetData(DictDataSource(make_full_base()), set_num=12)


def test_generate_items(set_data):
    rows = {r["item_api_name"]: r for r in SEED_GENERATORS["items"](set_data)}

    assert set(rows) == {"TFT_ITEM_RECURVEBOW", "TFT_ITEM_GUINSOOSRAGEBLADE"}
    assert rows["TFT_ITEM_RECURVEBOW"]["num_craftables"] == 0
    assert rows["TFT_ITEM_RECURVEBOW"]["num_bows"] == 1
    assert rows["TFT_ITEM_GUINSOOSRAGEBLADE"]["num_craftables"] == 1
    assert rows["TFT_ITEM_GUINSOOSRAGEBLADE"]["num_bows"] == 2
    assert rows["TFT_ITEM_GUINSOOSRAGEBLADE"]["num_supports"] == 1


def test_generate_augments(set_data):
    rows = SEED_GENERATORS["augments"](set_data)

    assert len(rows) == 1
    assert rows[0]["item_api_name"] == "TFT_AUGMENT_TESTAUGMENT"
    assert rows[0]["tier"] == "SILVER"


def test_generate_trait_tiers(set_data):
    rows = SEED_GENERATORS["trait_tiers"](set_data)

    types = {(r["api_name"], r["type"]) for r in rows}
    assert types == {
        ("TFT12_CHRONO", "SILVER"),
        ("TFT12_CHRONO", "LEGENDARY"),
        ("TFT12_PRESERVER", "BRONZE"),
    }
    chrono_silver = next(
        r for r in rows if r["api_name"] == "TFT12_CHRONO" and r["type"] == "SILVER"
    )
    assert chrono_silver["tier_min_units"] == 2
    assert chrono_silver["tier_max_units"] == 4


def test_generate_units(set_data):
    rows = {r["api_name"]: r for r in SEED_GENERATORS["units"](set_data)}

    assert set(rows) == {"TFT12_ZILEAN", "TFT_TRAININGDUMMY"}
    assert rows["TFT12_ZILEAN"]["shop_unit"] is True
    assert rows["TFT_TRAININGDUMMY"]["shop_unit"] is False
    assert rows["TFT12_ZILEAN"]["stats_hp"] == 550.0


def test_generate_unit_innate_traits(set_data):
    rows = SEED_GENERATORS["unit_innate_traits"](set_data)

    pairs = {(r["api_name"], r["trait_api_name"]) for r in rows}
    assert pairs == {
        ("TFT12_ZILEAN", "TFT12_CHRONO"),
        ("TFT12_ZILEAN", "TFT12_PRESERVER"),
    }
