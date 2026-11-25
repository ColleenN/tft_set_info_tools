import gzip
import json

import pytest
import time_machine

from tests.unreal_builders import build_zen
from tests.unreal_client import ITEMS, SET, build_client, texts, write
from tft_set_info_tools.scripts.cli import main
from tft_set_info_tools.unreal.upload import ConversionError, cdragon_version, convert, trait_styles

BUILD = "rls-19.1.0.6018196"
NOW = "2026-11-24T03:00:00Z"


@pytest.fixture
def client(tmp_path):
    root = tmp_path / "extracted"
    build_client(root)
    return root


def read_capture(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def previous_upload(tmp_path, client):
    """A first upload, with its tags translated and its items split by hand."""
    raw = tmp_path / "raw.json"
    convert([client], BUILD, tmp_path / "first", raw_output=raw)
    capture, = (tmp_path / "first").glob("*.json.gz")
    data = read_capture(capture)
    for item in data["items"]:
        item["tags"] = [{"Item.Completed": "{d1e0c3b7}"}.get(t, t) for t in item["tags"]]
    data["setData"][0]["items"] = ["DA_Deathblade", "DA_Component_BFSword"]
    capture.write_bytes(gzip.compress(json.dumps(data).encode()))
    return capture, raw


@time_machine.travel(NOW, tick=False)
def test_writes_capture_and_metadata(client, tmp_path):
    summary = convert([client], BUILD, tmp_path / "upload")
    capture = tmp_path / "upload" / "20261124T030000Z_en_us.json.gz"
    raw = gzip.decompress(capture.read_bytes())
    assert json.loads((tmp_path / "upload" / "metadata_20261124T030000Z.json").read_text()) == {
        "mirror-target": "manual-pbe-client-extract",
        "source-url": "manual:tft-pbe-client-extract-set19",
        "captured-at": NOW,
        "sha256": summary["sha256"],
        "size-bytes": str(len(raw)),
        "channel": "pbe",
        "cdragon-version": "19.1.6018196+rls-19.1.0.6018196",
        "cdragon-status": f"{NOW} done",
    }
    assert summary["set"] == 19
    assert summary["shop_units"] == 1
    assert summary["enriched_recipes"] == 1

    data = json.loads(raw)
    assert data["build"] == BUILD
    s = data["setData"][0]
    assert [c["shopUnit"] for c in s["champions"]] == [True]
    assert [c["shopUnit"] for c in data["sets"]["19"]["champions"]] == [True]
    assert s["champions"][0]["stats"]["damage"] == 50
    assert [e["style"] for e in s["traits"][0]["effects"]] == [1, 4]
    assert all(item["unique"] is False for item in data["items"])
    assert s["augments"] == ["DA_CyberneticBulk"]


def test_unchanged_items_reuse_the_previous_decisions(client, tmp_path):
    previous, previous_raw = previous_upload(tmp_path, client)
    convert([client], BUILD, tmp_path / "second", previous=previous, previous_raw=previous_raw)
    data = read_capture(next((tmp_path / "second").glob("*.json.gz")))
    items = {i["apiName"]: i for i in data["items"]}
    assert items["DA_Deathblade"]["tags"] == ["{d1e0c3b7}"]
    assert data["setData"][0]["items"] == ["DA_Deathblade", "DA_Component_BFSword"]
    assert data["setData"][0]["augments"] == ["DA_CyberneticBulk"]


def test_stops_on_items_with_new_tags(client, tmp_path):
    previous, previous_raw = previous_upload(tmp_path, client)
    raw = json.loads(previous_raw.read_text())
    next(i for i in raw["items"] if i["apiName"] == "DA_Deathblade")["tags"] = ["Item.Old"]
    previous_raw.write_text(json.dumps(raw))
    with pytest.raises(ConversionError, match=r"translating by hand: \['DA_Deathblade'\]"):
        convert([client], BUILD, tmp_path / "second", previous=previous, previous_raw=previous_raw)


def test_stops_on_items_new_since_the_previous_upload(client, tmp_path):
    previous, previous_raw = previous_upload(tmp_path, client)
    data = read_capture(previous)
    data["setData"][0]["augments"] = []
    previous.write_bytes(gzip.compress(json.dumps(data).encode()))
    with pytest.raises(ConversionError, match=r"items/augments split: \['DA_CyberneticBulk'\]"):
        convert([client], BUILD, tmp_path / "second", previous=previous, previous_raw=previous_raw)


def test_previous_needs_its_raw_export(client, tmp_path):
    with pytest.raises(ValueError, match="go together"):
        convert([client], BUILD, tmp_path / "upload", previous=tmp_path / "x.json.gz")


def test_needs_the_champions_table(client, tmp_path):
    (client / SET / "DT_19_ChampionsTable.uasset").unlink()
    with pytest.raises(FileNotFoundError, match="DT_19_ChampionsTable"):
        convert([client], BUILD, tmp_path / "upload")


def test_set_without_champions(client, tmp_path):
    with pytest.raises(ConversionError, match="no Set 20 champions"):
        convert([client], BUILD, tmp_path / "upload", set_number=20)


def test_no_champions_at_all(client, tmp_path):
    for path in (client / SET / "Champions").rglob("DA_*.uasset"):
        path.unlink()
    with pytest.raises(ConversionError, match="no set's champions"):
        convert([client], BUILD, tmp_path / "upload")


@pytest.mark.parametrize("build", ["19.1.0.6018196", "rls-19.1.6018196", "rls-latest"])
def test_rejects_builds_without_a_version(build):
    with pytest.raises(ValueError, match="not a client build"):
        cdragon_version(build)


def test_trait_styles():
    assert trait_styles([{}, {}, {}]) == [{"style": 1}, {"style": 3}, {"style": 4}]
    assert trait_styles([]) == [{"maxUnits": 25, "minUnits": 1, "style": 6, "variables": {}}]


@time_machine.travel(NOW, tick=False)
def test_cli(client, tmp_path, capsys):
    raw = tmp_path / "raw.json"
    assert main(["unreal", "convert", "-b", BUILD, "-s", "19", "-o", str(tmp_path / "upload"),
                 "--raw", str(raw), str(client)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["file"] == "20261124T030000Z_en_us.json.gz"
    assert json.loads(raw.read_text())["items"][0]["tags"] == ["Item.Component"]


def add_tactician_and_thief_items(client):
    for name, tag in [("TacticiansCrown", "Item.Equippable.Item.Tacticians"),
                      ("ThiefsGloves", "Item.Equippable.Item.ThiefsGloves")]:
        write(client, f"{ITEMS}/{name}/DA_{name}.uasset", build_zen(
            [f"DA_{name}", f"Identifier.Item.{name}", "Item.Equippable.Item.Craftable", tag], body=texts(7)))


def test_marks_tactician_and_thief_items(client, tmp_path):
    add_tactician_and_thief_items(client)
    convert([client], BUILD, tmp_path / "upload")
    items = {i["apiName"]: i for i in read_capture(next((tmp_path / "upload").glob("*.json.gz")))["items"]}
    assert items["DA_TacticiansCrown"]["tags"] == [
        "Item.Equippable.Item.Craftable", "Item.Equippable.Item.Tacticians", "{d304f83b}"]
    assert items["DA_ThiefsGloves"]["tags"][-1] == "{218b53a5}"
    assert items["DA_Deathblade"]["tags"] == ["Item.Completed"]


def test_augments_and_consumables_naming_those_items_are_not_marked(client, tmp_path):
    write(client, f"{SET}/Augments/DA_BandOfThieves.uasset", build_zen(
        ["DA_BandOfThieves", "Identifier.Augment.BandOfThieves", "Augment.Tier.Silver",
         "Item.Equippable.Item.ThiefsGloves"], body=texts(10)))
    write(client, f"{ITEMS}/Salvager/DA_ScissorSalvager.uasset", build_zen(
        ["DA_ScissorSalvager", "Identifier.Item.ScissorSalvager", "Item.Equippable.Consumable",
         "Item.Equippable.Item.Tacticians"], body=texts(7)))
    convert([client], BUILD, tmp_path / "upload")
    items = {i["apiName"]: i for i in read_capture(next((tmp_path / "upload").glob("*.json.gz")))["items"]}
    assert "{218b53a5}" not in items["DA_BandOfThieves"]["tags"]
    assert "{d304f83b}" not in items["DA_ScissorSalvager"]["tags"]


def test_marks_them_on_top_of_the_previous_translation(client, tmp_path):
    add_tactician_and_thief_items(client)
    previous, previous_raw = previous_upload(tmp_path, client)
    data = read_capture(previous)
    for item in data["items"]:
        if item["apiName"] in ("DA_TacticiansCrown", "DA_ThiefsGloves"):
            item["tags"] = ["{7ea41d13}"]
    data["setData"][0]["items"] += ["DA_TacticiansCrown", "DA_ThiefsGloves"]
    previous.write_bytes(gzip.compress(json.dumps(data).encode()))
    convert([client], BUILD, tmp_path / "second", previous=previous, previous_raw=previous_raw)
    items = {i["apiName"]: i for i in read_capture(next((tmp_path / "second").glob("*.json.gz")))["items"]}
    assert items["DA_TacticiansCrown"]["tags"] == ["{7ea41d13}", "{d304f83b}"]
    assert items["DA_ThiefsGloves"]["tags"] == ["{7ea41d13}", "{218b53a5}"]
