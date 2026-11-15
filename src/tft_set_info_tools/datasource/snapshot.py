"""Read-only source for one gzipped snapshot stored in GCS."""

from __future__ import annotations

import gzip
import json

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

    def _read(self) -> dict:
        blob = self._get_client().bucket(self._bucket_name).get_blob(self._blob_path)
        if blob is None:
            raise FileNotFoundError(f"gs://{self._bucket_name}/{self._blob_path} not found")
        data = json.loads(gzip.decompress(blob.download_as_bytes()))
        self._metadata = dict(blob.metadata or {})
        return data

    def _write(self, data: dict) -> None:
        raise NotImplementedError("Snapshots are read-only.")
