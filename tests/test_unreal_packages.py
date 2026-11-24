import pytest

from tests.unreal_builders import build_zen, curve_table, fstring, text_property
from tft_set_info_tools.unreal.curves import evaluate, read_curve_table
from tft_set_info_tools.unreal.textkeys import TextReference, find_text_references
from tft_set_info_tools.unreal.zen import ZenPackage

KEY = "1F777F094AD4B14BB621D38CB4D91A86"
OTHER_KEY = "0123456789ABCDEF0123456789ABCDEF"


@pytest.mark.parametrize("versioning", [False, True])
def test_zen_names_imports_and_body(versioning):
    data = build_zen(["DA_Kalista19", "Identifier.Champion.Kalista"], ["/Set_19/Traits/DA_Ranger"],
                     body=b"BODY", versioning=versioning)
    package = ZenPackage(data)
    assert package.names == ["DA_Kalista19", "Identifier.Champion.Kalista"]
    assert package.imported_packages == ["/Set_19/Traits/DA_Ranger"]
    assert package.body == b"BODY"
    assert package.identifier() == "Identifier.Champion.Kalista"


def test_zen_without_imports_or_identifier():
    package = ZenPackage(build_zen(["DA_Thing"]))
    assert package.imported_packages == []
    assert package.identifier() is None


def test_text_references_in_order():
    data = b"junk" + text_property(KEY, "Kalista") + b"\x07" + text_property(OTHER_KEY, "Pierce", "TFT")
    assert find_text_references(data) == [
        TextReference("", KEY, "Kalista"),
        TextReference("TFT", OTHER_KEY, "Pierce"),
    ]


def test_text_reference_with_utf16_source():
    data = fstring("") + fstring(KEY) + fstring("Gain 20% – stacking", utf16=True)
    assert find_text_references(data) == [TextReference("", KEY, "Gain 20% – stacking")]


def test_key_without_a_source_string_is_skipped():
    assert find_text_references(fstring("") + fstring(KEY) + b"\x05\x00\x00\x00abc") == []


def test_curve_table_rows():
    rows = {"AutoAttackDamage": [(1, 50), (2, 75), (3, 112.5)], "Damage": [(1, 200)]}
    assert read_curve_table(curve_table(rows)) == {
        "AutoAttackDamage": [(1, 50), (2, 75), (3, 112.5)],
        "Damage": [(1, 200)],
    }


def test_curve_table_that_does_not_end_at_the_tag():
    with pytest.raises(ValueError, match="package tag"):
        read_curve_table(curve_table({"Damage": [(1, 200)]})[:-1] + b"\0")


@pytest.mark.parametrize("x, y", [(0, 50), (1, 50), (1.5, 62.5), (3, 112.5), (4, 112.5)])
def test_evaluate(x, y):
    assert evaluate([(1, 50), (2, 75), (3, 112.5)], x) == y
