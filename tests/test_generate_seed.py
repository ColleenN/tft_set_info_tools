import csv
import json

import pytest

from tft_set_info_tools.scripts.generate_seed import _parse_types, run


def make_base():
    return {
        "items": [
            {
                "apiName": "TFT_Item_RecurveBow",
                "name": "Recurve Bow",
                "tags": ["component"],
                "effects": {},
                "incompatibleTraits": [],
                "unique": False,
                "composition": [],
            },
        ],
        "setData": [
            {
                "number": 12,
                "mutator": "TFTSet12",
                "name": "Set12",
                "items": ["TFT_Item_RecurveBow"],
                "augments": [],
                "champions": [
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
            }
        ],
    }


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for var in ("TFT_DATASOURCE_ORDER", "TFT_LOCAL_PATH", "TFT_GCP_BUCKET", "TFT_GCP_BLOB_PATH"):
        monkeypatch.delenv(var, raising=False)


def test_parse_types_expands_all():
    assert set(_parse_types("all")) == set(
        _parse_types("trait_tiers,items,units,unit_innate_traits,augments")
    )


def test_parse_types_rejects_unknown():
    with pytest.raises(ValueError):
        _parse_types("not_a_real_type")


def test_run_writes_only_requested_types(monkeypatch, tmp_path):
    src_path = tmp_path / "src.json"
    src_path.write_text(json.dumps(make_base()), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))
    out_dir = tmp_path / "out"

    run("local", str(out_dir), 12, "items,trait_tiers")

    assert (out_dir / "seed_items.csv").exists()
    assert (out_dir / "seed_trait_tiers.csv").exists()
    assert not (out_dir / "seed_units.csv").exists()

    with (out_dir / "seed_items.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["item_api_name"] == "TFT_ITEM_RECURVEBOW"


def test_run_skips_empty_seed_type(monkeypatch, tmp_path, capsys):
    src_path = tmp_path / "src.json"
    src_path.write_text(json.dumps(make_base()), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))
    out_dir = tmp_path / "out"

    run("local", str(out_dir), 12, "augments")

    assert not (out_dir / "seed_augments.csv").exists()
    assert "augments" in capsys.readouterr().err


def test_run_creates_dst_path_if_missing(monkeypatch, tmp_path):
    src_path = tmp_path / "src.json"
    src_path.write_text(json.dumps(make_base()), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))
    out_dir = tmp_path / "nested" / "out"

    run("local", str(out_dir), 12, "units")

    assert (out_dir / "seed_units.csv").exists()


def test_run_handles_rows_with_mismatched_keys(monkeypatch, tmp_path):
    """Regression test: champions can carry different stat keys (e.g. only
    some have a "damageByStar" stat), so seed_units.csv rows don't all share
    the same columns. csv.DictWriter must not be limited to the first row's
    keys, or it raises ValueError on a later row with an extra key.
    """
    base = make_base()
    base["setData"][0]["champions"].append(
        {
            "name": "Ryze",
            "apiName": "TFT12_Ryze",
            "cost": 3,
            "role": "caster",
            "traits": ["Chrono"],
            "stats": {"hp": 600.0, "damageByStar": [10, 20, 30]},
        }
    )
    src_path = tmp_path / "src.json"
    src_path.write_text(json.dumps(base), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))
    out_dir = tmp_path / "out"

    run("local", str(out_dir), 12, "units")

    with (out_dir / "seed_units.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_api_name = {r["api_name"]: r for r in rows}
    assert by_api_name["TFT12_ZILEAN"]["stats_damage_by_star"] == ""
    assert by_api_name["TFT12_RYZE"]["stats_damage_by_star"] == "[10, 20, 30]"


