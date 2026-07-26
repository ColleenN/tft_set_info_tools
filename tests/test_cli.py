import json

import pytest

from tft_set_info_tools.scripts.cli import main


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


def test_requires_a_subcommand():
    with pytest.raises(SystemExit):
        main([])


def test_unknown_subcommand_exits():
    with pytest.raises(SystemExit):
        main(["not-a-real-command"])


@pytest.fixture
def fake_cdragon_client(monkeypatch):
    payload = {"items": []}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    class FakeClient:
        def get(self, url):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient)
    return payload


def test_update_src_subcommand_returns_zero_on_success(fake_cdragon_client, monkeypatch, tmp_path):
    dst_path = tmp_path / "out.json"
    monkeypatch.setenv("TFT_LOCAL_PATH", str(dst_path))

    assert main(["update-src", "cdragon", "local"]) == 0
    assert json.loads(dst_path.read_text(encoding="utf-8")) == fake_cdragon_client


def test_update_src_subcommand_returns_one_on_unknown_source():
    assert main(["update-src", "not_a_real_source", "local"]) == 1


def test_generate_seed_subcommand_returns_zero_on_success(monkeypatch, tmp_path):
    src_path = tmp_path / "src.json"
    src_path.write_text(json.dumps(make_base()), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))
    out_dir = tmp_path / "out"

    exit_code = main(
        [
            "generate-seed",
            "--src",
            "local",
            "--dst-path",
            str(out_dir),
            "--set",
            "12",
            "--type",
            "all",
        ]
    )

    assert exit_code == 0
    assert (out_dir / "seed_items.csv").exists()
    assert (out_dir / "seed_units.csv").exists()
    assert (out_dir / "seed_traits.csv").exists()
    assert (out_dir / "seed_unit_innate_traits.csv").exists()


def test_generate_seed_subcommand_returns_one_on_bad_type(monkeypatch, tmp_path):
    src_path = tmp_path / "src.json"
    src_path.write_text(json.dumps(make_base()), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))

    exit_code = main(
        [
            "generate-seed",
            "--src",
            "local",
            "--dst-path",
            str(tmp_path),
            "--type",
            "not_a_real_type",
        ]
    )

    assert exit_code == 1
