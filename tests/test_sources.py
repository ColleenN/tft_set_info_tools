import pytest

from tft_set_info_tools.datasource import (
    CDragonDataSource,
    DefaultDataSource,
    GCPDataSource,
    LocalDataSource,
    MetaTFTDataSource,
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


def test_build_source_metatft():
    assert isinstance(build_source("metatft"), MetaTFTDataSource)


def test_build_source_cdragon_with_patch():
    source = build_source("cdragon", patch="13.24")
    assert isinstance(source, CDragonDataSource)
    assert source.url.endswith("/13.24/cdragon/tft/en_us.json")


def test_build_source_patch_rejected_for_non_cdragon_source(monkeypatch, tmp_path):
    monkeypatch.setenv("TFT_LOCAL_PATH", str(tmp_path / "data.json"))
    with pytest.raises(ValueError):
        build_source("local", patch="13.24")


def test_build_source_default_by_name():
    assert isinstance(build_source("default"), DefaultDataSource)


def test_build_source_none_means_default():
    assert isinstance(build_source(None), DefaultDataSource)


def test_build_source_unknown_name_raises():
    with pytest.raises(ValueError):
        build_source("not_a_real_source")
