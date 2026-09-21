import json

import pytest

from tft_set_info_tools.datasource import CDragonDataSource
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
    team_planner_payload = {"TFTSet18": []}

    class FakeResponse:
        def __init__(self, body):
            self._body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self._body

    class FakeClient:
        def get(self, url):
            if url.endswith("/cdragon/tft/en_us.json"):
                return FakeResponse(payload)
            return FakeResponse(team_planner_payload)

        def close(self):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient)
    return {**payload, CDragonDataSource.TEAM_PLANNER_CODES_KEY: team_planner_payload}


def test_update_src_subcommand_returns_zero_on_success(fake_cdragon_client, monkeypatch, tmp_path):
    dst_path = tmp_path / "out.json"
    monkeypatch.setenv("TFT_LOCAL_PATH", str(dst_path))

    assert main(["update-src", "cdragon", "local"]) == 0
    assert json.loads(dst_path.read_text(encoding="utf-8")) == fake_cdragon_client


def test_update_src_subcommand_returns_one_on_unknown_source():
    assert main(["update-src", "not_a_real_source", "local"]) == 1


def test_update_src_subcommand_accepts_src_patch_flag(fake_cdragon_client, monkeypatch, tmp_path):
    dst_path = tmp_path / "out.json"
    monkeypatch.setenv("TFT_LOCAL_PATH", str(dst_path))

    exit_code = main(["update-src", "cdragon", "local", "--src-patch", "13.24"])

    assert exit_code == 0
    assert json.loads(dst_path.read_text(encoding="utf-8")) == fake_cdragon_client


def test_update_src_src_patch_rejected_for_non_cdragon_source(monkeypatch, tmp_path):
    src_path = tmp_path / "src.json"
    src_path.write_text(json.dumps(make_base()), encoding="utf-8")
    dst_path = tmp_path / "out.json"
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))

    exit_code = main(
        ["update-src", "local", "gcp", "--src-patch", "13.24"]
    )

    assert exit_code == 1


def test_env_file_sets_unset_variables(fake_cdragon_client, tmp_path):
    dst_path = tmp_path / "out.json"
    env_file = tmp_path / ".env"
    env_file.write_text(f"TFT_LOCAL_PATH={dst_path}\n", encoding="utf-8")

    exit_code = main(["--env-file", str(env_file), "update-src", "cdragon", "local"])

    assert exit_code == 0
    assert json.loads(dst_path.read_text(encoding="utf-8")) == fake_cdragon_client


def test_env_file_does_not_override_existing_env(fake_cdragon_client, monkeypatch, tmp_path):
    dst_path = tmp_path / "out.json"
    other_path = tmp_path / "other.json"
    monkeypatch.setenv("TFT_LOCAL_PATH", str(dst_path))
    env_file = tmp_path / ".env"
    env_file.write_text(f"TFT_LOCAL_PATH={other_path}\n", encoding="utf-8")

    exit_code = main(["--env-file", str(env_file), "update-src", "cdragon", "local"])

    assert exit_code == 0
    assert dst_path.exists()
    assert not other_path.exists()


def test_env_file_missing_returns_one(tmp_path):
    missing = tmp_path / "does_not_exist.env"
    assert main(["--env-file", str(missing), "update-src", "cdragon", "local"]) == 1


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
    assert (out_dir / "seed_trait_tiers.csv").exists()
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
