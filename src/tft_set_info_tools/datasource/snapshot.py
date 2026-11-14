"""Read-only source for one gzipped snapshot stored in GCS."""

from __future__ import annotations

import gzip
import json
from types import TracebackType

from tft_set_info_tools.datasource.base import TFTDataSource


class SnapshotDataSource(TFTDataSource):
    """Reads one gzipped JSON object from GCS. Its GCS object metadata is
    available as ``metadata`` after read().

    Pass ``client`` to share one ``google.cloud.storage.Client`` across many
    snapshots; it's left open on exit. Without one, a client is created on
    entry and closed on exit.
    """

    def __init__(self, bucket: str, object_name: str, client=None):
        super().__init__()
        if not bucket or not object_name:
            raise ValueError("bucket and object_name are required")
        self._bucket_name = bucket
        self._object_name = object_name
        self._client = client
        self._owns_client = client is None
        self._metadata: dict[str, str] | None = None

    @property
    def metadata(self) -> dict[str, str]:
        if self._metadata is None:
            raise RuntimeError("metadata is only available after read()")
        return self._metadata

    def _get_client(self):
        if self._client is None:
            from google.cloud import storage

            self._client = storage.Client()
        return self._client

    def _read(self) -> dict:
        blob = self._get_client().bucket(self._bucket_name).get_blob(self._object_name)
        if blob is None:
            raise FileNotFoundError(f"gs://{self._bucket_name}/{self._object_name} not found")
        data = json.loads(gzip.decompress(blob.download_as_bytes()))
        self._metadata = dict(blob.metadata or {})
        return data

    def _write(self, data: dict) -> None:
        raise NotImplementedError("Snapshots are read-only.")

    def __enter__(self) -> SnapshotDataSource:
        self._get_client()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None
