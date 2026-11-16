"""Read-only source for one gzipped snapshot stored in GCS."""

from __future__ import annotations

import gzip
import json

from tft_set_info_tools.datasource.cdragon import CDragonDataSource
from tft_set_info_tools.datasource.gcp import GCPDataSource


class SnapshotDataSource(GCPDataSource):
    """Reads one gzipped JSON object from GCS. Its GCS object metadata is
    available as ``metadata`` after read().

    Unlike GCPDataSource, the bucket and object name must be passed
    explicitly; the ``TFT_GCP_*`` bucket and blob path variables point at a
    different object.
    """

    def __init__(self, bucket: str, object_name: str, client=None):
        if not bucket or not object_name:
            raise ValueError("bucket and object_name are required")
        super().__init__(bucket, object_name, client)
        self._metadata: dict[str, str] | None = None

    @property
    def metadata(self) -> dict[str, str]:
        if self._metadata is None:
            raise RuntimeError("metadata is only available after read()")
        return self._metadata

    def _read_object(self, object_name: str) -> tuple[dict, dict[str, str]]:
        blob = self._get_client().bucket(self._bucket_name).get_blob(object_name)
        if blob is None:
            raise FileNotFoundError(f"gs://{self._bucket_name}/{object_name} not found")
        return json.loads(gzip.decompress(blob.download_as_bytes())), dict(blob.metadata or {})

    def _read(self) -> dict:
        data, self._metadata = self._read_object(self._blob_path)
        return data

    def _write(self, data: dict) -> None:
        raise NotImplementedError("Snapshots are read-only.")


class CDragonSnapshotDataSource(SnapshotDataSource):
    """A CDragon data snapshot with a Team Planner snapshot bundled in, the
    way CDragonDataSource bundles the live Team Planner file.

    Without ``team_planner_object`` the payload has no Team Planner codes,
    so only TFTSetData's Team Planner methods are affected. The Team Planner
    object's metadata is available as ``team_planner_metadata`` after read().
    """

    def __init__(
        self,
        bucket: str,
        object_name: str,
        team_planner_object: str | None = None,
        client=None,
    ):
        super().__init__(bucket, object_name, client)
        self._team_planner_object = team_planner_object
        self._team_planner_metadata: dict[str, str] | None = None

    @property
    def team_planner_metadata(self) -> dict[str, str]:
        if self._team_planner_metadata is None:
            raise RuntimeError("team_planner_metadata is only available after read()")
        return self._team_planner_metadata

    def _read(self) -> dict:
        data = super()._read()
        if self._team_planner_object is None:
            self._team_planner_metadata = {}
            return data
        codes, self._team_planner_metadata = self._read_object(self._team_planner_object)
        return {**data, CDragonDataSource.TEAM_PLANNER_CODES_KEY: codes}
