import json

import pytest

from tft_set_info_tools.scripts.update_src import run


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for var in ("TFT_DATASOURCE_ORDER", "TFT_LOCAL_PATH", "TFT_GCP_BUCKET", "TFT_GCP_BLOB_PATH"):
        monkeypatch.delenv(var, raising=False)


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


def test_run_copies_cdragon_to_local(fake_cdragon_client, monkeypatch, tmp_path):
    dst_path = tmp_path / "out.json"
    monkeypatch.setenv("TFT_LOCAL_PATH", str(dst_path))

    run("cdragon", "local")

    assert json.loads(dst_path.read_text(encoding="utf-8")) == fake_cdragon_client


def test_run_raises_on_unknown_source():
    with pytest.raises(ValueError):
        run("not_a_real_source", "local")


def test_run_raises_when_dst_does_not_support_write(monkeypatch, tmp_path):
    src_path = tmp_path / "in.json"
    src_path.write_text(json.dumps({"n": 1}), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(src_path))

    with pytest.raises(NotImplementedError):
        run("local", "cdragon")
