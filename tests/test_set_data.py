import json

import pytest

from tests.conftest import DictDataSource
from tft_set_info_tools.datasource import CDragonDataSource, LocalDataSource
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


def _team_planner_code(mutator, *champion_ids):
    slots = list(champion_ids) + [0] * (10 - len(champion_ids))
    return "01" + "".join(f"{champ_id:02X}" for champ_id in slots) + mutator


def _make_champ(name, api_name, cost=1, traits=("Chrono",)):
    return {"name": name, "apiName": api_name, "cost": cost, "traits": list(traits)}


def make_team_planner_base(set_number=12, mutator="TFTSet12"):
    base = make_base(set_number=set_number, mutator=mutator)
    base["setData"][0]["champions"] = [
        _make_champ("Zilean", "TFT12_Zilean"),
        _make_champ("Ahri", "TFT12_Ahri"),
        _make_champ("TrainingDummy", "TFT_TrainingDummy", cost=0, traits=[]),
    ]
    return base


def test_get_team_planner_champion_order_sorts_shop_units_alphabetically():
    set_data = TFTSetData(DictDataSource(make_team_planner_base()), set_num=12)
    names = [c["name"] for c in set_data.get_team_planner_champion_order()]
    assert names == ["Ahri", "Zilean"]


def test_decode_team_planner_code_matches_gist_example():
    # Verbatim example from the spec, using its 10-champion alphabetical list.
    base = make_team_planner_base()
    base["setData"][0]["champions"] = [
        _make_champ(f"Champ{i}", f"TFT12_Champ{i:02d}") for i in range(1, 11)
    ]
    set_data = TFTSetData(DictDataSource(base), set_num=12)
    code = _team_planner_code("TFTSet12", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    assert code == "010102030405060708090ATFTSet12"

    units = set_data.decode_team_planner_code(code)
    assert [u["name"] for u in units] == [f"Champ{i}" for i in range(1, 11)]


def test_decode_team_planner_code_orders_and_leaves_empty_slots():
    set_data = TFTSetData(DictDataSource(make_team_planner_base()), set_num=12)
    # Alphabetically: TFT12_Ahri -> 01, TFT12_Zilean -> 02.
    code = _team_planner_code("TFTSet12", 1, 2)
    units = set_data.decode_team_planner_code(code)
    assert [u["name"] if u else None for u in units] == [
        "Ahri",
        "Zilean",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ]


def test_decode_team_planner_code_rejects_malformed_code():
    set_data = TFTSetData(DictDataSource(make_team_planner_base()), set_num=12)
    with pytest.raises(ValueError):
        set_data.decode_team_planner_code("not-a-code")


def test_decode_team_planner_code_rejects_mismatched_mutator():
    set_data = TFTSetData(DictDataSource(make_team_planner_base()), set_num=12)
    with pytest.raises(ValueError):
        set_data.decode_team_planner_code(_team_planner_code("TFTSet13", 1))


def test_decode_team_planner_code_rejects_out_of_range_champion_id():
    set_data = TFTSetData(DictDataSource(make_team_planner_base()), set_num=12)
    with pytest.raises(ValueError):
        set_data.decode_team_planner_code(_team_planner_code("TFTSet12", 99))


def _team_planner_code_v2(mutator, *champion_ids):
    slots = list(champion_ids) + [0] * (10 - len(champion_ids))
    return "02" + "".join(f"{champ_id:03X}" for champ_id in slots) + mutator


def make_team_planner_v2_base(mutator="TFTSet12", team_planner_mutator=None):
    base = make_team_planner_base(mutator=mutator)
    base[CDragonDataSource.TEAM_PLANNER_CODES_KEY] = {
        team_planner_mutator or mutator: [
            {"character_id": "TFT12_Ahri", "team_planner_code": 1041},
            {"character_id": "TFT12_Zilean", "team_planner_code": 1055},
        ]
    }
    return base


def test_decode_team_planner_code_v2_uses_real_team_planner_code_ids():
    set_data = TFTSetData(DictDataSource(make_team_planner_v2_base()), set_num=12)
    code = _team_planner_code_v2("TFTSet12", 1041, 1055)

    units = set_data.decode_team_planner_code(code)

    assert [u["name"] if u else None for u in units] == [
        "Ahri",
        "Zilean",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ]


def test_decode_team_planner_code_v2_rejects_missing_mutator_in_bundled_data():
    base = make_team_planner_v2_base(team_planner_mutator="TFTSet13")
    set_data = TFTSetData(DictDataSource(base), set_num=12)
    code = _team_planner_code_v2("TFTSet12", 1041)

    with pytest.raises(ValueError):
        set_data.decode_team_planner_code(code)


def test_decode_team_planner_code_v2_rejects_unmapped_champion_id():
    set_data = TFTSetData(DictDataSource(make_team_planner_v2_base()), set_num=12)
    code = _team_planner_code_v2("TFTSet12", 9999)

    with pytest.raises(ValueError):
        set_data.decode_team_planner_code(code)


def test_decode_team_planner_code_v2_rejects_when_source_has_no_bundled_data():
    # e.g. a TFTSetData built from a non-CDragon source has no team planner codes at all.
    set_data = TFTSetData(DictDataSource(make_team_planner_base()), set_num=12)
    code = _team_planner_code_v2("TFTSet12", 1041)

    with pytest.raises(ValueError):
        set_data.decode_team_planner_code(code)


def test_decode_team_planner_code_rejects_wrong_slot_width_for_version():
    set_data = TFTSetData(DictDataSource(make_team_planner_base()), set_num=12)
    # v1 header ("01"), but with v2-width (3 hex digit per slot) champion data.
    with pytest.raises(ValueError):
        set_data.decode_team_planner_code("01" + "0" * 30 + "TFTSet12")


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
