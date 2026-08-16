import pytest

from tft_set_info_tools.schema import (
    AugmentTier,
    CDragonSchema,
    ItemType,
    MetaTFTSchema,
    detect_schema,
)


def make_cdragon_base():
    return {
        "items": [
            {
                "apiName": "TFT_Item_Artifact1",
                "name": "Artifact Item",
                "tags": ["{44ace175}"],
            },
            {
                "apiName": "TFT_Augment_Gold1",
                "name": "Gold Augment",
                "tags": ["{b72bd3bf}", "{ce1fd21c}"],
            },
        ],
        "setData": [
            {
                "number": 12,
                "mutator": "TFTSet12",
                "items": ["TFT_Item_Artifact1"],
                "augments": ["TFT_Augment_Gold1"],
                "champions": [{"name": "Zilean", "apiName": "TFT12_Zilean"}],
                "traits": [{"name": "Chrono", "apiName": "TFT12_Chrono"}],
            },
            {
                "number": 13,
                "mutator": "TFTSet13",
                "items": [],
                "augments": [],
                "champions": [],
                "traits": [],
            },
        ],
    }


def make_metatft_base():
    return {
        "units": [{"name": "Alune", "apiName": "TFT18_Alune"}],
        "traits": [{"name": "Attuned", "apiName": "DA_AluneUniqueTrait18"}],
        "items": [
            {
                "apiName": "DA_AdaptiveHelm",
                "name": "Adaptive Helm",
                "tags": ["Item.Equippable.Item.Artifact"],
            }
        ],
        "augments": [
            {"apiName": "DA_AdvancedLoan", "name": "Advanced Loan", "rarity": "Gold"}
        ],
        "_metadata": {"set": "TFTSet18", "patch": "pbe"},
    }


def test_detect_schema_picks_cdragon():
    assert isinstance(detect_schema(make_cdragon_base()), CDragonSchema)


def test_detect_schema_picks_metatft():
    assert isinstance(detect_schema(make_metatft_base()), MetaTFTSchema)


def test_detect_schema_raises_on_unrecognized_shape():
    with pytest.raises(ValueError):
        detect_schema({"nonsense": True})


def test_validate_passes_for_matching_shape():
    CDragonSchema().validate(make_cdragon_base())
    MetaTFTSchema().validate(make_metatft_base())


def test_validate_raises_for_mismatched_shape():
    with pytest.raises(ValueError):
        CDragonSchema().validate(make_metatft_base())
    with pytest.raises(ValueError):
        MetaTFTSchema().validate(make_cdragon_base())


def test_cdragon_schema_latest_set_number():
    assert CDragonSchema().latest_set_number(make_cdragon_base()) == 13


def test_cdragon_schema_extract():
    extracted = CDragonSchema().extract(make_cdragon_base(), 12)
    assert extracted.mutator == "TFTSet12"
    assert [u["apiName"] for u in extracted.units] == ["TFT12_Zilean"]
    assert [t["apiName"] for t in extracted.traits] == ["TFT12_Chrono"]
    assert [i["apiName"] for i in extracted.items] == ["TFT_Item_Artifact1"]
    assert [a["apiName"] for a in extracted.augments] == ["TFT_Augment_Gold1"]


def test_cdragon_schema_extract_missing_set_raises():
    with pytest.raises(ValueError):
        CDragonSchema().extract(make_cdragon_base(), 999)


def test_cdragon_schema_get_item_types_and_augment_tier():
    schema = CDragonSchema()
    item = {"tags": ["{44ace175}"]}
    augment = {"tags": ["{b72bd3bf}", "{ce1fd21c}"]}
    assert schema.get_item_types(item) == {ItemType.ARTIFACT}
    assert schema.get_augment_tier(augment) == AugmentTier.GOLD


def test_metatft_schema_latest_set_number():
    assert MetaTFTSchema().latest_set_number(make_metatft_base()) == 18


def test_metatft_schema_extract():
    extracted = MetaTFTSchema().extract(make_metatft_base(), 18)
    assert extracted.mutator == "TFTSet18"
    assert [u["apiName"] for u in extracted.units] == ["TFT18_Alune"]
    assert [t["apiName"] for t in extracted.traits] == ["DA_AluneUniqueTrait18"]
    assert [i["apiName"] for i in extracted.items] == ["DA_AdaptiveHelm"]
    assert [a["apiName"] for a in extracted.augments] == ["DA_AdvancedLoan"]


def test_metatft_schema_extract_wrong_set_raises():
    with pytest.raises(ValueError):
        MetaTFTSchema().extract(make_metatft_base(), 999)


def test_metatft_schema_get_item_types_and_augment_tier():
    schema = MetaTFTSchema()
    item = {"tags": ["Item.Equippable.Item.Artifact"]}
    augment = {"rarity": "Gold"}
    assert schema.get_item_types(item) == {ItemType.ARTIFACT}
    assert schema.get_augment_tier(augment) == AugmentTier.GOLD


def test_metatft_schema_unmapped_item_type_never_matches():
    schema = MetaTFTSchema()
    item = {"tags": ["Item.Equippable.Category.Attack"]}
    assert schema.get_item_types(item) == frozenset()
