"""Google Cloud Storage TFT metadata json data source."""

from __future__ import annotations

import json
import os
from types import TracebackType

from tft_set_info_tools.datasource.base import TFTDataSource


class GCPDataSource(TFTDataSource):
    """Reads/writes TFT metadata json from/to a Google Cloud Storage bucket.

    Bucket, blob path, and credentials are read from environment variables
    unless passed explicitly.
    """

    BUCKET_ENV_VAR = "TFT_GCP_BUCKET"
    BLOB_PATH_ENV_VAR = "TFT_GCP_BLOB_PATH"
    CREDENTIALS_ENV_VAR = "TFT_GCP_CREDENTIALS"
    PROJECT_ENV_VAR = "TFT_GCP_PROJECT"

    def __init__(self, bucket: str | None = None, blob_path: str | None = None):
        super().__init__()
        self._bucket_name = bucket or os.environ.get(self.BUCKET_ENV_VAR)
        self._blob_path = blob_path or os.environ.get(self.BLOB_PATH_ENV_VAR)
        if not self._bucket_name:
            raise ValueError(
                f"GCS bucket not specified; pass bucket= or set {self.BUCKET_ENV_VAR}"
            )
        if not self._blob_path:
            raise ValueError(
                f"GCS blob path not specified; pass blob_path= or set {self.BLOB_PATH_ENV_VAR}"
            )
        self._project = os.environ.get(self.PROJECT_ENV_VAR)
        self._credentials_path = os.environ.get(self.CREDENTIALS_ENV_VAR)
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import storage

            if self._credentials_path:
                self._client = storage.Client.from_service_account_json(
                    self._credentials_path, project=self._project
                )
            else:
                self._client = storage.Client(project=self._project)
        return self._client

    def _get_blob(self):
        bucket = self._get_client().bucket(self._bucket_name)
        return bucket.blob(self._blob_path)

    def _read(self) -> dict:
        return json.loads(self._get_blob().download_as_text())

    def _write(self, data: dict) -> None:
        self._get_blob().upload_from_string(
            json.dumps(data), content_type="application/json"
        )

    def __enter__(self) -> GCPDataSource:
        self._get_client()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
