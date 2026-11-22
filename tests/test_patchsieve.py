import gzip
import json

import pytest

from tft_set_info_tools.loaders.patchsieve.captures import (
    channel_and_region,
    list_patchsieve_captures,
    parse_release,
    patch_from_stream,
)


def response(revision="5964148", stream="rls-18.7.0", wrapped=True):
    def label(value):
        return {"values": [value]} if wrapped else value

    return {
        "releases": [
            {
                "release": {
                    "product": "teamfighttactics",
                    "id": "C00FB038C03890EE",
                    "created_at": "2026-11-16T20:45:00.000Z",
                    "labels": {
                        "Stream": label(stream),
                        "riot:revision": label(revision),
                        "riot:artifact_version_id": label(f"{stream}.{revision}.Set18FullPC.Shipping.live"),
                    },
                },
                "compat_version": {},
                "download": {"url": "https://example.invalid/manifest"},
            }
        ]
    }


class FakeBlob:
    def __init__(self, name, payload=None, metadata=None):
        self.name = name
        self.metadata = metadata
        self._content = gzip.compress(json.dumps(payload or response()).encode())

    def download_as_bytes(self):
        return self._content


class FakeStorage:
    def __init__(self, blobs):
        self.blobs = {blob.name: blob for blob in blobs}

    def list_blobs(self, bucket, prefix):
        return [blob for name, blob in self.blobs.items() if name.startswith(prefix)]

    def bucket(self, bucket_name):
        blobs = self.blobs

        class FakeBucket:
            def get_blob(self, name):
                return blobs.get(name)

        return FakeBucket()


def copy(version_set, stamp, payload=None, **metadata):
    return FakeBlob(
        f"patchsieve/{version_set}/{stamp}_{version_set}.gz",
        payload,
        {"version-set": version_set, "platform": "windows", "artifact-type": "client", **metadata},
    )


@pytest.mark.parametrize("wrapped", [True, False])
def test_parse_release_reads_plain_and_listed_labels(wrapped):
    fields = parse_release(gzip.compress(json.dumps(response(wrapped=wrapped)).encode()))
    assert fields == {
        "release_id": "C00FB038C03890EE",
        "release_created_at": "2026-11-16T20:45:00.000Z",
        "stream": "rls-18.7.0",
        "patch": "18.7",
        "revision": "5964148",
        "artifact_version_id": "rls-18.7.0.5964148.Set18FullPC.Shipping.live",
    }


def test_parse_release_accepts_uncompressed_content():
    assert parse_release(json.dumps(response()).encode())["revision"] == "5964148"


def test_parse_release_rejects_anything_but_one_release():
    with pytest.raises(ValueError, match="one release"):
        parse_release(json.dumps({"releases": []}).encode())


def test_parse_release_needs_a_revision():
    payload = response()
    del payload["releases"][0]["release"]["labels"]["riot:revision"]
    with pytest.raises(ValueError, match="riot:revision"):
        parse_release(json.dumps(payload).encode())


def test_patch_from_stream():
    assert patch_from_stream("rls-19.1.0") == "19.1"
    assert patch_from_stream("main") is None
    assert patch_from_stream(None) is None


def test_channel_and_region():
    assert channel_and_region("live-NA1") == ("live", "NA1")
    assert channel_and_region("pbe-global") == ("pbe", None)


def test_lists_every_version_set_oldest_first():
    storage = FakeStorage(
        [
            copy("live-NA1", "20261118T000000Z"),
            copy("pbe-global", "20261117T000000Z"),
            copy("live-NA1", "20261117T120000Z"),
            FakeBlob("patchsieve/patchsieve.yaml", metadata={}),
        ]
    )
    captures = list_patchsieve_captures(storage, "bucket")
    assert [(c.version_set, c.captured_at.isoformat()) for c in captures] == [
        ("pbe-global", "2026-11-17T00:00:00+00:00"),
        ("live-NA1", "2026-11-17T12:00:00+00:00"),
        ("live-NA1", "2026-11-18T00:00:00+00:00"),
    ]


class TestLoadClientDeploys:
    @pytest.fixture(autouse=True)
    def _needs_bigquery(self):
        pytest.importorskip("google.cloud.bigquery")

    def run(self, storage, bigquery=None):
        from tests.test_bigquery import FakeClient as FakeBigQuery
        from tft_set_info_tools.loaders.patchsieve.run import load_client_deploys

        bigquery = bigquery or FakeBigQuery()
        return load_client_deploys(storage, bigquery, "bucket", "ref", "patchsieve"), bigquery

    def test_appends_one_row_per_copy_in_one_load(self):
        storage = FakeStorage(
            [copy("live-JP1", "20261116T210000Z"), copy("pbe-global", "20261117T000000Z", response("6014015", "rls-19.1.0"))]
        )

        result, bigquery = self.run(storage)

        assert len(result.loaded) == 2
        [(destination, rows, _)] = bigquery.loads
        assert destination == "proj.ref.client_deploys"
        jp1, pbe = rows
        assert jp1["region"] == "JP1"
        assert jp1["channel"] == "live"
        assert jp1["platform"] == "windows"
        assert jp1["revision"] == "5964148"
        assert jp1["captured_at"] == "2026-11-16T21:00:00+00:00"
        assert pbe["region"] is None
        assert pbe["patch"] == "19.1"
        assert all(row["loaded_at"] for row in rows)

    def test_skips_copies_already_loaded(self):
        from tests.test_bigquery import FakeClient as FakeBigQuery

        loaded = copy("live-NA1", "20261117T000000Z")
        new = copy("live-NA1", "20261118T000000Z")
        bigquery = FakeBigQuery(
            {"SELECT DISTINCT source_object FROM `proj.ref.client_deploys`": [{"source_object": loaded.name}]}
        )

        result, bigquery = self.run(FakeStorage([loaded, new]), bigquery)

        assert result.loaded == [new.name]

    def test_a_bad_copy_is_left_out_and_the_rest_still_load(self):
        bad = copy("live-NA1", "20261117T000000Z", {"releases": []})
        good = copy("live-NA1", "20261118T000000Z")

        result, bigquery = self.run(FakeStorage([bad, good]))

        assert result.failed == [bad.name]
        assert [row["source_object"] for row in bigquery.loads[0][1]] == [good.name]


def test_load_patchsieve_reads_settings_from_the_env_file(tmp_path, monkeypatch):
    from tft_set_info_tools.scripts import load_patchsieve
    from tft_set_info_tools.scripts.cli import main

    for var in (load_patchsieve.BUCKET_ENV_VAR, load_patchsieve.DATASET_ENV_VAR, load_patchsieve.PATH_ENV_VAR):
        monkeypatch.delenv(var, raising=False)
    env_file = tmp_path / "patchsieve.env"
    env_file.write_text(f"{load_patchsieve.BUCKET_ENV_VAR}=bucket\n{load_patchsieve.DATASET_ENV_VAR}=tft_reference\n")
    seen = []
    monkeypatch.setattr(load_patchsieve, "load", seen.append)

    assert main(["--env-file", str(env_file), "load", "patchsieve"]) == 0
    assert seen == [load_patchsieve.PatchsieveLoadConfig("bucket", "tft_reference", "patchsieve")]


def test_load_needs_a_source():
    from tft_set_info_tools.scripts.cli import main

    with pytest.raises(SystemExit):
        main(["load"])
