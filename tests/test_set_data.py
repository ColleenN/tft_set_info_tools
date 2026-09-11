import json

import pytest

from tests.conftest import DictDataSource
from tft_set_info_tools.datasource import LocalDataSource
from tft_set_info_tools.set_data import AugmentTier, ItemType, TFTSetData


def make_base(set_number=12, mutator="TFTSet12"):
    return {
        "items": [
            {
                "apiName": "TFT_Item_Support1",
                "name": "Support Item",
                "tags": ["{27557a09}"],
            },
            {
                "apiName": "TFT_Item_Artifact1",
                "name": "Artifact Item",
                "tags": ["{44ace175}"],
            },
            {
                "apiName": "TFT_Augment_Silver1",
                "name": "Silver Augment",
                "tags": ["{b72bd3bf}", "{d11fd6d5}"],
            },
            {
                "apiName": "TFT_Augment_Gold1",
                "name": "Gold Augment",
                "tags": ["{b72bd3bf}", "{ce1fd21c}"],
            },
            {
                "apiName": "TFT_Item_NotInSet",
                "name": "Item From Another Set",
                "tags": ["{44ace175}"],
            },
        ],
        "setData": [
            {
                "number": set_number,
                "mutator": mutator,
                "name": "Set12",
                "items": ["TFT_Item_Support1", "TFT_Item_Artifact1"],
                "augments": ["TFT_Augment_Silver1", "TFT_Augment_Gold1"],
                "champions": [
                    {"name": "Zilean", "apiName": "TFT12_Zilean", "cost": 2, "traits": ["Chrono"]},
                    {"name": "TrainingDummy", "apiName": "TFT_TrainingDummy", "cost": 0, "traits": []},
                ],
                "traits": [
                    {
                        "name": "Chrono",
                        "apiName": "TFT12_Chrono",
                        "desc": "Chrono desc",
                        "effects": [{"minUnits": 2, "maxUnits": 4, "style": 3}],
                    },
                    {
                        "name": "Preserver",
                        "apiName": "TFT12_Preserver",
                        "desc": "Preserver desc",
                        "effects": [{"minUnits": 1, "maxUnits": 25, "style": 1}],
                    },
                ],
            }
        ],
    }


def make_metatft_base():
    return {
        "units": [
            {
                "name": "Zilean",
                "apiName": "TFT12_Zilean",
                "cost": 2,
                "role": "support",
                "traits": ["Chrono"],
                "stats": {"hp": 550.0},
            },
        ],
        "traits": [
            {
                "name": "Chrono",
                "apiName": "TFT12_Chrono",
                "desc": "Chrono desc",
                "effects": [{"minUnits": 2, "maxUnits": 4, "style": 3}],
            },
        ],
        "items": [
            {
                "apiName": "DA_AdaptiveHelm",
                "name": "Adaptive Helm",
                "tags": ["Item.Equippable.Item.Artifact"],
                "effects": {},
                "incompatibleTraits": [],
                "unique": False,
                "composition": [],
            },
        ],
        "augments": [
            {
                "apiName": "DA_AdvancedLoan",
                "name": "Advanced Loan",
                "rarity": "Gold",
                "effects": {},
            },
        ],
        "_metadata": {"set": "TFTSet12", "patch": "pbe"},
    }


@pytest.fixture(autouse=True)
def clear_datasource_env(monkeypatch):
    for var in ("TFT_DATASOURCE_ORDER", "TFT_LOCAL_PATH"):
        monkeypatch.delenv(var, raising=False)


def test_from_dict_with_explicit_set_num():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    assert set_data.mutator == "TFTSet12"


def test_defaults_to_latest_set_when_set_num_omitted():
    base = make_base(set_number=12)
    base["setData"].append(
        {
            "number": 13,
            "mutator": "TFTSet13",
            "name": "Set13",
            "items": [],
            "augments": [],
            "champions": [],
            "traits": [],
        }
    )
    set_data = TFTSetData(DictDataSource(base))
    assert set_data.mutator == "TFTSet13"


def test_missing_set_raises():
    with pytest.raises(ValueError):
        TFTSetData(DictDataSource(make_base()), set_num=999)


def test_get_items_excludes_augments_and_other_sets():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    names = {item["apiName"] for item in set_data.get_items()}
    assert names == {"TFT_Item_Support1", "TFT_Item_Artifact1"}


def test_get_items_filtered_by_type():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    names = {item["apiName"] for item in set_data.get_items(ItemType.ARTIFACT)}
    assert names == {"TFT_Item_Artifact1"}


def test_get_augments_returns_only_augments():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    names = {item["apiName"] for item in set_data.get_augments()}
    assert names == {"TFT_Augment_Silver1", "TFT_Augment_Gold1"}


def test_get_augments_filtered_by_tier():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    names = {item["apiName"] for item in set_data.get_augments(AugmentTier.GOLD)}
    assert names == {"TFT_Augment_Gold1"}


def test_get_shop_units_excludes_traitless_champions():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    names = {c["name"] for c in set_data.get_shop_units()}
    assert names == {"Zilean"}


def test_get_units_includes_traitless_champions():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    names = {c["name"] for c in set_data.get_units()}
    assert names == {"Zilean", "TrainingDummy"}


def test_get_traits_returns_full_detail():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    names = {t["name"] for t in set_data.get_traits()}
    assert names == {"Chrono", "Preserver"}


def test_get_unique_traits():
    set_data = TFTSetData(DictDataSource(make_base()), set_num=12)
    assert set_data.get_unique_traits() == ["Preserver"]


def test_from_tft_data_source(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(make_base()), encoding="utf-8")

    set_data = TFTSetData(LocalDataSource(path), set_num=12)

    assert set_data.mutator == "TFTSet12"


def test_from_none_uses_datasource_order(monkeypatch, tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(make_base()), encoding="utf-8")
    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "local")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(path))

    set_data = TFTSetData(set_num=12)

    assert set_data.mutator == "TFTSet12"


class _DeclaringDataSource(DictDataSource):
    """A DictDataSource that declares a schema via get_schema(), like a real origin source."""

    def __init__(self, data, schema):
        super().__init__(data)
        self.schema = schema


def test_uses_declared_schema_without_sniffing():
    from tft_set_info_tools.schema import CDragonSchema

    set_data = TFTSetData(_DeclaringDataSource(make_base(), CDragonSchema), set_num=12)
    assert set_data.mutator == "TFTSet12"


def test_raises_when_data_does_not_match_declared_schema():
    from tft_set_info_tools.schema import MetaTFTSchema

    with pytest.raises(ValueError):
        TFTSetData(_DeclaringDataSource(make_base(), MetaTFTSchema), set_num=12)


def make_cdragon_item_base():
    base = make_base()
    for item in base["items"]:
        item.setdefault("effects", {})
        item.setdefault("incompatibleTraits", [])
        item.setdefault("unique", False)
        item.setdefault("composition", [])
    return base


def test_normalized_getters_work_for_both_cdragon_and_metatft_sources():
    """TFTSetData and its normalized getters must not be CDragon-only.

    get_equippable_items()/_item_component_counts() previously read raw
    CDragon hash tags/api names directly; now that's delegated to the
    schema, so this should produce the same shape of result regardless of
    which source the data came from.
    """
    cdragon_data = TFTSetData(DictDataSource(make_cdragon_item_base()), set_num=12)
    metatft_data = TFTSetData(DictDataSource(make_metatft_base()), set_num=12)

    cdragon_items = {i.api_name: i for i in cdragon_data.get_equippable_items()}
    metatft_items = {i.api_name: i for i in metatft_data.get_equippable_items()}

    assert cdragon_items["TFT_ITEM_ARTIFACT1"].type_counts["artifacts"] == 1
    assert metatft_items["DA_ADAPTIVEHELM"].type_counts["artifacts"] == 1

    assert {a.api_name for a in cdragon_data.get_normalized_augments()} == {
        "TFT_AUGMENT_SILVER1",
        "TFT_AUGMENT_GOLD1",
    }
    assert {a.api_name for a in metatft_data.get_normalized_augments()} == {
        "DA_ADVANCEDLOAN"
    }
