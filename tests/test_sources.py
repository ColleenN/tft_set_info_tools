import pytest

from tft_set_info_tools.datasource import (
    CDragonDataSource,
    DefaultDataSource,
    GCPDataSource,
    LocalDataSource,
)
from tft_set_info_tools.scripts._sources import build_source


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for var in (
        "TFT_DATASOURCE_ORDER",
        "TFT_LOCAL_PATH",
        "TFT_GCP_BUCKET",
        "TFT_GCP_BLOB_PATH",
    ):
        monkeypatch.delenv(var, raising=False)


def test_build_source_local(monkeypatch, tmp_path):
    monkeypatch.setenv("TFT_LOCAL_PATH", str(tmp_path / "data.json"))
    assert isinstance(build_source("local"), LocalDataSource)


def test_build_source_gcp(monkeypatch):
    monkeypatch.setenv("TFT_GCP_BUCKET", "my-bucket")
    monkeypatch.setenv("TFT_GCP_BLOB_PATH", "path/to/blob")
    assert isinstance(build_source("gcp"), GCPDataSource)


def test_build_source_cdragon():
    assert isinstance(build_source("cdragon"), CDragonDataSource)


def test_build_source_default_by_name():
    assert isinstance(build_source("default"), DefaultDataSource)


def test_build_source_none_means_default():
    assert isinstance(build_source(None), DefaultDataSource)


def test_build_source_unknown_name_raises():
    with pytest.raises(ValueError):
        build_source("not_a_real_source")
