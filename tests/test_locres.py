import pytest

from tests.unreal_builders import build_locres
from tft_set_info_tools.unreal.locres import LocresFile

STRINGS = {
    "": {
        "TFT19_Kalista_Name": "Kalista",
        "TFT19_Kalista_Title": "Kalista",
        "TFT19_Trait_Desc": "Gain 20% Attack Speed – stacking",
    },
    "UI": {"Shop_Refresh": "Reroll"},
}


@pytest.mark.parametrize("version", [0, 1, 2, 3])
def test_reads_every_version(version):
    table = LocresFile(build_locres(STRINGS, version))
    assert table.version == version
    assert table.entries == STRINGS
    assert len(table) == 4


def test_reads_a_file(tmp_path):
    path = tmp_path / "Game.locres"
    path.write_bytes(build_locres(STRINGS))
    assert LocresFile(path).entries == STRINGS


def test_get():
    table = LocresFile(build_locres(STRINGS))
    assert table.get("TFT19_Kalista_Name") == "Kalista"
    assert table.get("Shop_Refresh", namespace="UI") == "Reroll"
    assert table.get("missing", default="?") == "?"


def test_update_merges_and_later_tables_win():
    table = LocresFile(build_locres(STRINGS))
    table.update(LocresFile(build_locres({"": {"TFT19_Kalista_Name": "Kalista!", "New": "Key"}})))
    assert table.get("TFT19_Kalista_Name") == "Kalista!"
    assert table.get("New") == "Key"
    assert table.get("Shop_Refresh", namespace="UI") == "Reroll"


def test_unsupported_version():
    data = bytearray(build_locres(STRINGS))
    data[16] = 4
    with pytest.raises(ValueError, match="unsupported locres version 4"):
        LocresFile(bytes(data))
