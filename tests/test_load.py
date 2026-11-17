import pytest

from tft_set_info_tools.scripts import load
from tft_set_info_tools.scripts.cli import main
from tft_set_info_tools.scripts.load import LoadConfig, resolve_config

ENV_VARS = (load.BUCKET_ENV_VAR, load.DATASET_ENV_VAR, load.MIN_SET_ENV_VAR, load.CHANNELS_ENV_VAR)


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_arguments():
    assert resolve_config("bucket", "proj.tft_reference", 17, "pbe") == LoadConfig(
        "bucket", "proj.tft_reference", 17, ("pbe",)
    )


def test_environment_fallback(monkeypatch):
    monkeypatch.setenv(load.BUCKET_ENV_VAR, "bucket")
    monkeypatch.setenv(load.DATASET_ENV_VAR, "tft_reference")
    monkeypatch.setenv(load.MIN_SET_ENV_VAR, "17")
    monkeypatch.setenv(load.CHANNELS_ENV_VAR, "live, pbe")

    assert resolve_config() == LoadConfig("bucket", "tft_reference", 17, ("live", "pbe"))


def test_arguments_override_environment(monkeypatch):
    monkeypatch.setenv(load.MIN_SET_ENV_VAR, "17")
    assert resolve_config("bucket", "tft_reference", 16).min_set == 16


def test_channels_default_to_live_and_pbe():
    assert resolve_config("bucket", "tft_reference", 17).channels == ("live", "pbe")


def test_min_set_zero_is_allowed():
    assert resolve_config("bucket", "tft_reference", 0).min_set == 0


def test_missing_settings_are_all_named():
    with pytest.raises(ValueError, match="--bucket.*--dataset.*--min-set"):
        resolve_config()


def test_blank_channels_are_rejected():
    with pytest.raises(ValueError, match="no channels"):
        resolve_config("bucket", "tft_reference", 17, " , ")


def test_cli_reads_settings_from_the_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "loader.env"
    env_file.write_text(
        f"{load.BUCKET_ENV_VAR}=bucket\n{load.DATASET_ENV_VAR}=tft_reference\n{load.MIN_SET_ENV_VAR}=17\n"
    )
    seen = []
    monkeypatch.setattr(load, "load", seen.append)

    assert main(["--env-file", str(env_file), "load", "--channels", "pbe"]) == 0
    assert seen == [LoadConfig("bucket", "tft_reference", 17, ("pbe",))]


def test_cli_fails_until_the_loader_exists(capsys):
    assert main(["load", "--bucket", "b", "--dataset", "d", "--min-set", "17"]) == 1
    assert "S5" in capsys.readouterr().err
