import json
import sys
import types

import pytest

from tft_set_info_tools.datasource import (
    CDragonDataSource,
    GCPDataSource,
    LocalDataSource,
    MetaTFTDataSource,
    TFTDataSource,
)


def test_tft_data_source_is_abstract():
    with pytest.raises(TypeError):
        TFTDataSource()


def test_local_data_source_has_no_schema(tmp_path):
    assert LocalDataSource(tmp_path / "data.json").get_schema() is None


def test_local_data_source_round_trip(tmp_path):
    path = tmp_path / "data.json"
    payload = {"champions": ["Zilean"]}

    with LocalDataSource(path) as source:
        source.write(payload)
    with LocalDataSource(path) as source:
        assert source.read() == payload


def test_read_caches_after_first_call(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"n": 1}), encoding="utf-8")

    source = LocalDataSource(path)
    first = source.read()

    path.write_text(json.dumps({"n": 2}), encoding="utf-8")
    second = source.read()

    assert first == {"n": 1}
    assert second == {"n": 1}


def test_read_force_bypasses_cache(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"n": 1}), encoding="utf-8")

    source = LocalDataSource(path)
    first = source.read()

    path.write_text(json.dumps({"n": 2}), encoding="utf-8")
    forced = source.read(force=True)
    cached_again = source.read()

    assert first == {"n": 1}
    assert forced == {"n": 2}
    assert cached_again == {"n": 2}


def test_write_updates_cache_to_written_data(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"n": 1}), encoding="utf-8")

    source = LocalDataSource(path)
    source.read()
    source.write({"n": 2})
    path.unlink()

    # read() must return the cached value from write(), not hit the (now
    # missing) file again.
    assert source.read() == {"n": 2}


def test_local_data_source_write_from_other_source(tmp_path):
    src_path = tmp_path / "src.json"
    dst_path = tmp_path / "dst.json"
    payload = {"traits": []}
    src_path.write_text(json.dumps(payload), encoding="utf-8")

    LocalDataSource(dst_path).write(LocalDataSource(src_path))

    assert json.loads(dst_path.read_text(encoding="utf-8")) == payload


def test_write_from_other_source_caches_the_resolved_dict(tmp_path):
    src_path = tmp_path / "src.json"
    dst_path = tmp_path / "dst.json"
    payload = {"traits": ["Chrono"]}
    src_path.write_text(json.dumps(payload), encoding="utf-8")

    dst = LocalDataSource(dst_path)
    dst.write(LocalDataSource(src_path))
    dst_path.unlink()

    # write()'s cache must hold the resolved dict, not the source object,
    # so read() works even though the destination file is now gone.
    assert dst.read() == payload


def test_gcp_data_source_has_no_schema(monkeypatch):
    monkeypatch.setenv("TFT_GCP_BUCKET", "my-bucket")
    monkeypatch.setenv("TFT_GCP_BLOB_PATH", "path/to/blob")
    assert GCPDataSource().get_schema() is None


def test_gcp_data_source_requires_bucket_and_blob_path(monkeypatch):
    monkeypatch.delenv("TFT_GCP_BUCKET", raising=False)
    monkeypatch.delenv("TFT_GCP_BLOB_PATH", raising=False)
    with pytest.raises(ValueError):
        GCPDataSource()


def test_gcp_data_source_falls_back_to_env_vars(monkeypatch):
    monkeypatch.setenv("TFT_GCP_BUCKET", "my-bucket")
    monkeypatch.setenv("TFT_GCP_BLOB_PATH", "path/to/blob")

    source = GCPDataSource()

    assert source._bucket_name == "my-bucket"
    assert source._blob_path == "path/to/blob"


@pytest.fixture
def fake_gcs(monkeypatch):
    payload = {"champions": []}

    class FakeBlob:
        def __init__(self, store, key):
            self._store = store
            self._key = key

        def download_as_text(self):
            return json.dumps(self._store[self._key])

        def upload_from_string(self, data, content_type=None):
            self._store[self._key] = json.loads(data)

    class FakeBucket:
        def __init__(self, store):
            self._store = store

        def blob(self, blob_path):
            return FakeBlob(self._store, blob_path)

    class FakeClient:
        closed = False

        def __init__(self, project=None):
            self.project = project

        def bucket(self, bucket_name):
            return FakeBucket(store)

        def close(self):
            self.closed = True

    store = {"path/to/blob": payload}

    storage_module = types.ModuleType("google.cloud.storage")
    storage_module.Client = FakeClient
    cloud_module = types.ModuleType("google.cloud")
    cloud_module.storage = storage_module
    google_module = types.ModuleType("google")
    google_module.cloud = cloud_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_module)

    return types.SimpleNamespace(store=store, client_cls=FakeClient)


def test_gcp_data_source_read_write(fake_gcs):
    with GCPDataSource(bucket="my-bucket", blob_path="path/to/blob") as source:
        assert source.read() == {"champions": []}
        source.write({"champions": ["Ahri"]})

    assert fake_gcs.store["path/to/blob"] == {"champions": ["Ahri"]}


def test_gcp_data_source_closes_client_on_exit(fake_gcs):
    with GCPDataSource(bucket="my-bucket", blob_path="path/to/blob") as source:
        client = source._client
    assert client.closed


def test_cdragon_data_source_schema():
    from tft_set_info_tools.schema import CDragonSchema

    assert CDragonDataSource().get_schema() is CDragonSchema


def test_cdragon_data_source_default_patch_is_latest():
    assert CDragonDataSource().url.endswith("/latest/cdragon/tft/en_us.json")


def test_cdragon_data_source_uses_requested_patch():
    assert CDragonDataSource(patch="14.1").url.endswith("/14.1/cdragon/tft/en_us.json")


def test_cdragon_data_source_uses_patch_env_var(monkeypatch):
    monkeypatch.setenv("TFT_CDRAGON_PATCH", "14.2")
    assert CDragonDataSource().url.endswith("/14.2/cdragon/tft/en_us.json")


def test_cdragon_data_source_explicit_patch_overrides_env_var(monkeypatch):
    monkeypatch.setenv("TFT_CDRAGON_PATCH", "14.2")
    assert CDragonDataSource(patch="14.1").url.endswith("/14.1/cdragon/tft/en_us.json")


def test_cdragon_data_source_write_raises():
    with pytest.raises(NotImplementedError):
        CDragonDataSource().write({})


def test_cdragon_data_source_read(monkeypatch):
    payload = {"items": []}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    def fake_get(url):
        assert url == CDragonDataSource().url
        return FakeResponse()

    monkeypatch.setattr("httpx.get", fake_get)

    assert CDragonDataSource().read() == payload


def test_cdragon_data_source_read_reuses_client_in_context(monkeypatch):
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

    with CDragonDataSource() as source:
        assert source.read() == payload
        client = source._client
    assert client.closed


def test_metatft_data_source_schema():
    from tft_set_info_tools.schema import MetaTFTSchema

    assert MetaTFTDataSource().get_schema() is MetaTFTSchema


def test_metatft_data_source_default_url():
    assert (
        MetaTFTDataSource().url
        == "https://data.metatft.com/lookups/TFTSet18_pbe_en_us.json"
    )


def test_metatft_data_source_explicit_url_overrides_default():
    source = MetaTFTDataSource(url="https://data.metatft.com/lookups/TFTSet19_live_en_us.json")
    assert source.url == "https://data.metatft.com/lookups/TFTSet19_live_en_us.json"


def test_metatft_data_source_uses_url_env_var(monkeypatch):
    monkeypatch.setenv(
        "TFT_METATFT_URL", "https://data.metatft.com/lookups/TFTSet19_live_en_us.json"
    )
    assert (
        MetaTFTDataSource().url
        == "https://data.metatft.com/lookups/TFTSet19_live_en_us.json"
    )


def test_metatft_data_source_explicit_url_overrides_env_var(monkeypatch):
    monkeypatch.setenv(
        "TFT_METATFT_URL", "https://data.metatft.com/lookups/TFTSet19_live_en_us.json"
    )
    source = MetaTFTDataSource(url="https://data.metatft.com/lookups/TFTSet20_live_en_us.json")
    assert source.url == "https://data.metatft.com/lookups/TFTSet20_live_en_us.json"


def test_metatft_data_source_write_raises():
    with pytest.raises(NotImplementedError):
        MetaTFTDataSource().write({})


def test_metatft_data_source_read(monkeypatch):
    payload = {"units": [], "_metadata": {"set": "TFTSet18"}}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    def fake_get(url):
        assert url == MetaTFTDataSource().url
        return FakeResponse()

    monkeypatch.setattr("httpx.get", fake_get)

    assert MetaTFTDataSource().read() == payload


def test_metatft_data_source_read_reuses_client_in_context(monkeypatch):
    payload = {"units": [], "_metadata": {"set": "TFTSet18"}}

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

    with MetaTFTDataSource() as source:
        assert source.read() == payload
        client = source._client
    assert client.closed
