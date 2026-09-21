import json

import pytest

from tft_set_info_tools.datasource import CDragonDataSource
from tft_set_info_tools.scripts.update_src import run


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for var in ("TFT_DATASOURCE_ORDER", "TFT_LOCAL_PATH", "TFT_GCP_BUCKET", "TFT_GCP_BLOB_PATH"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def fake_cdragon_client(monkeypatch):
    payload = {"items": []}
    team_planner_payload = {"TFTSet18": []}
    merged = {**payload, CDragonDataSource.TEAM_PLANNER_CODES_KEY: team_planner_payload}
    requested_urls: list[str] = []

    class FakeResponse:
        def __init__(self, body):
            self._body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self._body

    class FakeClient:
        def get(self, url):
            requested_urls.append(url)
            if url.endswith("/cdragon/tft/en_us.json"):
                return FakeResponse(payload)
            return FakeResponse(team_planner_payload)

        def close(self):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient)
    return (merged, requested_urls)


def test_run_copies_cdragon_to_local(fake_cdragon_client, monkeypatch, tmp_path):
    merged, requested_urls = fake_cdragon_client
    dst_path = tmp_path / "out.json"
    monkeypatch.setenv("TFT_LOCAL_PATH", str(dst_path))

    run("cdragon", "local")

    assert json.loads(dst_path.read_text(encoding="utf-8")) == merged
    assert requested_urls == [
        "https://raw.communitydragon.org/latest/cdragon/tft/en_us.json",
        "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/"
        "global/default/v1/tftchampions-teamplanner.json",
    ]


def test_run_uses_src_patch_for_cdragon(fake_cdragon_client, monkeypatch, tmp_path):
    _, requested_urls = fake_cdragon_client
    dst_path = tmp_path / "out.json"
    monkeypatch.setenv("TFT_LOCAL_PATH", str(dst_path))

    run("cdragon", "local", src_patch="13.24")

    assert requested_urls == [
        "https://raw.communitydragon.org/13.24/cdragon/tft/en_us.json",
        "https://raw.communitydragon.org/13.24/plugins/rcp-be-lol-game-data/"
        "global/default/v1/tftchampions-teamplanner.json",
    ]


def test_run_raises_on_unknown_source():
    with pytest.raises(ValueError):
        run("not_a_real_source", "local")


def test_run_raises_when_dst_does_not_support_write(monkeypatch, tmp_path):
    src_path = tmp_path / "in.json"
    src_path.write_text(json.dumps({"n": 1}), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))

    with pytest.raises(NotImplementedError):
        run("local", "cdragon")
