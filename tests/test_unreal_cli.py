import json

import pytest

from tests.unreal_builders import KEY, PakSpec, build_iostore, build_locres, build_pak
from tft_set_info_tools.scripts.cli import main
from tft_set_info_tools.scripts.unreal import AES_KEY_ENV_VAR

UNITS = b"units" * 40
TRAITS = b"traits"
FILES = [
    ("TFT/Plugins/GameFeatures/Set_19/Content/units.uasset", UNITS),
    ("TFT/Plugins/GameFeatures/Set_19/Content/traits.uasset", TRAITS),
    ("TFT/Content/other.uasset", b"other"),
]


@pytest.fixture(autouse=True)
def no_key_in_env(monkeypatch):
    monkeypatch.delenv(AES_KEY_ENV_VAR, raising=False)


@pytest.fixture
def utoc(tmp_path):
    path = tmp_path / "pakchunk1-WindowsClient.utoc"
    build_iostore(path, FILES)
    return path


def test_list(utoc, capsys):
    assert main(["unreal", "list", "-p", "*/Set_19/*", str(utoc)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "         6 TFT/Plugins/GameFeatures/Set_19/Content/traits.uasset",
        "       200 TFT/Plugins/GameFeatures/Set_19/Content/units.uasset",
    ]


def test_list_everything(utoc, capsys):
    assert main(["unreal", "list", str(utoc)]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 3


def test_extract(utoc, tmp_path):
    out = tmp_path / "out"
    assert main(["unreal", "extract", "-o", str(out), "-p", "*/units.uasset", "-p", "*/other.*", str(utoc)]) == 0
    assert (out / "TFT/Plugins/GameFeatures/Set_19/Content/units.uasset").read_bytes() == UNITS
    assert (out / "TFT/Content/other.uasset").read_bytes() == b"other"
    assert not (out / "TFT/Plugins/GameFeatures/Set_19/Content/traits.uasset").exists()


def test_extract_defaults_to_a_folder_named_after_the_container(utoc, tmp_path):
    assert main(["unreal", "extract", str(utoc)]) == 0
    assert (tmp_path / "pakchunk1-WindowsClient/TFT/Content/other.uasset").read_bytes() == b"other"


def test_lazy_extract_keeps_existing_files(utoc, tmp_path):
    out = tmp_path / "out"
    kept = out / "TFT/Content/other.uasset"
    kept.parent.mkdir(parents=True)
    kept.write_bytes(b"kept")
    assert main(["unreal", "extract", "--lazy", "-o", str(out), str(utoc)]) == 0
    assert kept.read_bytes() == b"kept"
    assert (out / "TFT/Plugins/GameFeatures/Set_19/Content/traits.uasset").read_bytes() == TRAITS


def test_extract_into_a_file_fails(utoc, tmp_path):
    out = tmp_path / "out"
    out.write_text("")
    assert main(["unreal", "extract", "-o", str(out), str(utoc)]) == 1


def test_aes_key_from_flag_or_env(tmp_path, monkeypatch, capsys):
    pak = tmp_path / "encrypted.pak"
    build_pak(pak, [PakSpec("a.bin", b"secret", encrypted=True)], key=KEY, encrypt_index=True)

    assert main(["unreal", "list", str(pak)]) == 1
    assert "AES key is required" in capsys.readouterr().err

    assert main(["unreal", "list", "-k", "0x" + KEY.hex(), str(pak)]) == 0
    assert capsys.readouterr().out.split() == ["6", "a.bin"]

    monkeypatch.setenv(AES_KEY_ENV_VAR, KEY.hex())
    assert main(["unreal", "list", str(pak)]) == 0
    assert capsys.readouterr().out.split() == ["6", "a.bin"]


def test_missing_container(tmp_path, capsys):
    assert main(["unreal", "list", str(tmp_path / "nope.pak")]) == 1
    assert "container file not found" in capsys.readouterr().err


def test_locres_dump_merges_in_order(tmp_path, capsys):
    base = tmp_path / "Game.locres"
    chunk = tmp_path / "Game_locchunk1.locres"
    base.write_bytes(build_locres({"": {"a": "A", "b": "B"}}))
    chunk.write_bytes(build_locres({"": {"b": "B2", "c": "Ç"}}))

    assert main(["unreal", "locres-dump", str(base), str(chunk)]) == 0
    assert json.loads(capsys.readouterr().out) == {"": {"a": "A", "b": "B2", "c": "Ç"}}

    out = tmp_path / "strings.json"
    assert main(["unreal", "locres-dump", "-o", str(out), str(base), str(chunk)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == {"": {"a": "A", "b": "B2", "c": "Ç"}}


def test_locres_dump_missing_file(tmp_path):
    assert main(["unreal", "locres-dump", str(tmp_path / "nope.locres")]) == 1
