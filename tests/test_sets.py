import logging

from tft_set_info_tools.loader.sets import sets_to_load


def payload(*mutators_by_number):
    return {
        "setData": [
            {"number": number, "mutator": mutator}
            for number, mutators in mutators_by_number
            for mutator in mutators
        ]
    }


RAW = payload(
    (1, ["TFTSetTutorial"]),
    (7, ["TFTSet7", "TFTSet7_PAIRS"]),
    (16, ["TFTSet16_PVEMODE", "TFTSet16", "TFTSetEventER"]),
    (17, ["TFTSet17", "TFTSet17_PAIRS"]),
)


def test_loads_sets_from_the_floor_up():
    assert sets_to_load(RAW, 16) == [16, 17]


def test_floor_above_every_set_loads_nothing():
    assert sets_to_load(RAW, 18) == []


def test_each_set_is_listed_once_whatever_its_variants():
    assert sets_to_load(RAW, 7) == [7, 16, 17]


def test_skips_a_set_without_a_standard_entry(caplog):
    with caplog.at_level(logging.WARNING):
        assert sets_to_load(RAW, 1) == [7, 16, 17]
    assert "set 1 has no TFTSet1 entry" in caplog.text
