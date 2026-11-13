import pytest

from tests.conftest import DictDataSource
from tests.test_seeds import make_full_base
from tft_set_info_tools.scripts.reference_tables import REFERENCE_TABLES
from tft_set_info_tools.set_data import TFTSetData


@pytest.fixture
def set_data():
    base = make_full_base()
    # Units carrying different stats would add different seed columns.
    base["setData"][0]["champions"][1]["stats"] = {"hp": 1000.0, "armor": 40.0}
    return TFTSetData(DictDataSource(base), set_num=12)


def rows(set_data, table):
    return REFERENCE_TABLES[table].generate(set_data)


@pytest.mark.parametrize("table", list(REFERENCE_TABLES))
def test_every_row_has_exactly_the_declared_columns(set_data, table):
    generated = rows(set_data, table)

    assert generated
    for row in generated:
        assert list(row) == list(REFERENCE_TABLES[table].columns)


def test_items_carry_no_type_or_component_columns(set_data):
    by_name = {r["item_api_name"]: r for r in rows(set_data, "items")}

    assert set(by_name) == {"TFT_ITEM_RECURVEBOW", "TFT_ITEM_GUINSOOSRAGEBLADE"}
    assert by_name["TFT_ITEM_GUINSOOSRAGEBLADE"]["num_craftables"] == 1
    assert by_name["TFT_ITEM_GUINSOOSRAGEBLADE"]["effects"] == {"a": 1}


def test_item_types_are_one_row_per_item_and_type(set_data):
    pairs = {(r["item_api_name"], r["item_type"]) for r in rows(set_data, "item_types")}

    assert pairs == {
        ("TFT_ITEM_RECURVEBOW", "component"),
        ("TFT_ITEM_GUINSOOSRAGEBLADE", "support"),
    }


def test_item_components_are_one_row_per_item_and_component(set_data):
    counts = {
        (r["item_api_name"], r["component"]): r["count"] for r in rows(set_data, "item_components")
    }

    assert counts == {
        ("TFT_ITEM_RECURVEBOW", "bow"): 1,
        ("TFT_ITEM_GUINSOOSRAGEBLADE", "bow"): 2,
    }


def test_unit_stats_are_one_json_value(set_data):
    by_name = {r["api_name"]: r for r in rows(set_data, "units")}

    assert by_name["TFT12_ZILEAN"]["stats"] == {"hp": 550.0, "mana": 70.0}
    assert by_name["TFT_TRAININGDUMMY"]["stats"] == {"hp": 1000.0, "armor": 40.0}


def test_json_columns_hold_parsed_values(set_data):
    tier = rows(set_data, "trait_tiers")[0]
    augment = rows(set_data, "augments")[0]

    assert tier["tier_variables"] == {}
    assert augment["effects"] == {"x": 1}
    assert augment["tier"] == "SILVER"
