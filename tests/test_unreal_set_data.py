import pytest

from tests.unreal_client import SET, build_client, write
from tft_set_info_tools.unreal.assets import (
    ExtractedFiles,
    icon_path,
    load_assets,
    package_path,
    read_strings,
    scan_recipes,
)
from tft_set_info_tools.unreal.set_data import build_tft_data, enrich, latest_set, set_entry


@pytest.fixture
def files(tmp_path):
    build_client(tmp_path)
    return ExtractedFiles(tmp_path)


@pytest.fixture
def data(files):
    return build_tft_data(load_assets(files, read_strings(files)), 19)


def test_package_and_icon_paths():
    assert package_path(f"{SET}/Champions/Kalista/DA_Kalista19.uasset") == "/Set_19/Champions/Kalista/DA_Kalista19"
    assert package_path("TFT/Content/UI/DA_Thing.uasset") == "/Game/UI/DA_Thing"
    assert icon_path("/Set_19/A/T_X") == "tft/plugins/gamefeatures/set_19/content/a/t_x.png"
    assert icon_path("/Game/UI/T_X") == "tft/content/ui/t_x.png"


def test_extracted_files_from_several_folders(tmp_path):
    write(tmp_path / "a", "TFT/one.uasset", b"a")
    write(tmp_path / "b", "TFT/one.uasset", b"b")
    write(tmp_path / "b", "TFT/two.uasset", b"two")
    files = ExtractedFiles(tmp_path / "a", tmp_path / "b")
    assert sorted(files.files) == ["TFT/one.uasset", "TFT/two.uasset"]
    assert files.read("TFT/one.uasset") == b"a"


def test_extracted_files_needs_a_folder(tmp_path):
    with pytest.raises(NotADirectoryError):
        ExtractedFiles(tmp_path / "missing")


def test_strings_merge_later_tables_over_earlier(files):
    assert read_strings(files).get("00000000000000000000000000000002") == "Piercing Spear"


def test_strings_need_the_locale(files):
    with pytest.raises(FileNotFoundError, match="fr-FR"):
        read_strings(files, "fr-FR")


def test_loads_only_readable_tft_assets(files):
    assets = load_assets(files)
    assert sorted(a.api_name for a in assets) == [
        "DA_Component_BFSword", "DA_CyberneticBulk", "DA_Deathblade", "DA_Kalista19", "DA_Ranger"]
    assert latest_set(assets) == 19


def test_champion(data):
    kalista, = set_entry(data, 19)["champions"]
    assert kalista == {
        "ability": {
            "desc": "Kalista fires a spear that deals 200 damage.",
            "icon": "tft/plugins/gamefeatures/set_19/content/champions/kalista/t_kalista_spellicon.png",
            "name": "Piercing Spear",
            "variables": [],
        },
        "apiName": "DA_Kalista19",
        "characterName": "Kalista",
        "cost": 2,
        "icon": "tft/plugins/gamefeatures/set_19/content/champions/kalista/t_kalista_pc.png",
        "name": "Kalista",
        "role": "DA_Role_ADCarry",
        "squareIcon": None,
        "stats": {"armor": 30, "attackSpeed": 0.7, "critChance": None, "critMultiplier": None, "damage": None,
                  "hp": 650, "initialMana": 0, "magicResist": None, "mana": None, "range": 1},
        "tileIcon": None,
        "traits": ["Ranger"],
    }


def test_trait(data):
    ranger, = set_entry(data, 19)["traits"]
    assert ranger["name"] == "Ranger"
    assert ranger["desc"] == "Rangers gain Attack Speed.\n(2) 10% Attack Speed\n(4) 25% Attack Speed"
    assert ranger["effects"] == [
        {"maxUnits": 3, "minUnits": 2, "style": None, "variables": {}},
        {"maxUnits": 25, "minUnits": 4, "style": None, "variables": {}},
    ]
    assert ranger["icon"] == "tft/plugins/gamefeatures/set_19/content/traits/ranger/t_ranger.png"


def test_items_and_augments(data):
    items = {i["apiName"]: i for i in data["items"]}
    assert items["DA_Deathblade"]["name"] == "Deathblade"
    assert items["DA_Deathblade"]["desc"] == "Gain 50% Attack Damage."
    assert items["DA_Deathblade"]["tags"] == ["Item.Completed"]
    assert items["DA_Deathblade"]["composition"] == ["DA_Component_BFSword"]
    assert items["DA_CyberneticBulk"]["tags"] == ["Augment.Silver"]
    s = set_entry(data, 19)
    assert s["items"] == ["DA_Component_BFSword", "DA_Deathblade"]
    assert s["augments"] == ["DA_CyberneticBulk"]


def test_sets_entry_is_a_separate_copy(data):
    set_entry(data, 19)["champions"][0]["name"] = "changed"
    assert data["sets"]["19"]["champions"][0]["name"] == "Kalista"


def test_recipes(files):
    assert scan_recipes(files) == {"Identifier.Item.Deathblade": ["BFSword", "BFSword"]}


def test_enrich(files, data):
    assert enrich(files, data, scan_recipes(files), 19) == {"champions": 1, "traits": 1, "recipes": 1}
    s = set_entry(data, 19)
    kalista, = s["champions"]
    assert kalista["stats"]["damage"] == 50
    assert kalista["stats"]["damageByStar"] == [50, 75, 112.5, 168.75]
    assert kalista["ability"]["variables"] == [{"name": "Damage", "value": [200, 300, 450, 450]}]
    ranger, = s["traits"]
    assert [e["variables"] for e in ranger["effects"]] == [{"AttackSpeed": 10}, {"AttackSpeed": 25}]
    deathblade = next(i for i in data["items"] if i["apiName"] == "DA_Deathblade")
    assert deathblade["composition"] == ["DA_Component_BFSword", "DA_Component_BFSword"]
    assert data["sets"]["19"]["champions"][0]["stats"]["damage"] is None


def test_enrich_skips_tables_that_are_not_curves(files, data, tmp_path):
    write(tmp_path, f"{SET}/Champions/Kalista/CT_Kalista.uasset", b"\0" * 80)
    assert enrich(ExtractedFiles(tmp_path), data, {}, 19) == {"traits": 1}
