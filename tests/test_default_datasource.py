import json

import pytest

from tft_set_info_tools.datasource import DefaultDataSource, TFTDataSource


@pytest.fixture(autouse=True)
def clear_datasource_env(monkeypatch):
    for var in (
        "TFT_DATASOURCE_ORDER",
        "TFT_LOCAL_PATH",
        "TFT_GCP_BUCKET",
        "TFT_GCP_BLOB_PATH",
    ):
        monkeypatch.delenv(var, raising=False)


def test_requires_an_order():
    with pytest.raises(ValueError):
        DefaultDataSource()


def test_order_can_be_passed_explicitly(monkeypatch, tmp_path):
    path = tmp_path / "data.json"
    payload = {"champions": []}
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(path))

    source = DefaultDataSource(order="local")

    assert source.read() == payload


def test_falls_back_past_unconfigured_source(monkeypatch, tmp_path):
    payload = {"champions": []}
    path = tmp_path / "data.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "gcp,local")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(path))

    assert DefaultDataSource().read() == payload


def test_falls_back_past_a_read_failure(monkeypatch, tmp_path):
    missing_path = tmp_path / "does_not_exist.json"
    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "local,cdragon")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(missing_path))

    cdragon_payload = {"items": []}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return cdragon_payload

    class FakeClient:
        def get(self, url):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient)

    assert DefaultDataSource().read() == cdragon_payload


def test_raises_when_every_source_fails_to_read(monkeypatch, tmp_path):
    missing_path = tmp_path / "does_not_exist.json"
    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "local")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(missing_path))

    with pytest.raises(RuntimeError):
        DefaultDataSource().read()


def test_raises_on_unknown_name(monkeypatch):
    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "not_a_real_source")
    with pytest.raises(RuntimeError):
        DefaultDataSource().read()


def test_caches_resolved_source_across_read_calls(monkeypatch, tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"n": 1}), encoding="utf-8")
    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "local")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(path))

    source = DefaultDataSource()
    source.read()
    resolved_after_first_read = source._resolved

    path.write_text(json.dumps({"n": 2}), encoding="utf-8")
    source.read()

    assert source._resolved is resolved_after_first_read


def test_write_delegates_to_first_configured_source(monkeypatch, tmp_path):
    path = tmp_path / "data.json"
    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "gcp,local")
    monkeypatch.setenv("TFT_LOCAL_PATH", str(path))

    DefaultDataSource().write({"champions": ["Ahri"]})

    assert json.loads(path.read_text(encoding="utf-8")) == {"champions": ["Ahri"]}


def test_write_does_not_fall_back_on_write_failure(monkeypatch):
    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "cdragon,local")

    with pytest.raises(NotImplementedError):
        DefaultDataSource().write({"champions": []})


def test_context_manager_closes_resolved_source(monkeypatch, tmp_path):
    payload = {"items": []}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    class FakeClient:
        closed = False

        def get(self, url):
            return FakeResponse()

        def close(self):
            self.closed = True

    monkeypatch.setattr("httpx.Client", FakeClient)
    monkeypatch.setenv("TFT_DATASOURCE_ORDER", "cdragon")

    with DefaultDataSource() as source:
        source.read()
        client = source._resolved._client

    assert client.closed


def test_is_a_tft_data_source():
    assert issubclass(DefaultDataSource, TFTDataSource)
