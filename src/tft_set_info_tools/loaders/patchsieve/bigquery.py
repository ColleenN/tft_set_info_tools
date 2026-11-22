"""The client_deploys table: one row per saved Patchsieve copy.

A run appends all of its new rows in one load job, so a run that dies partway
leaves nothing behind to clean up.
"""

from __future__ import annotations

from datetime import datetime, timezone

from tft_set_info_tools.loaders.bigquery import TableWriter

CLIENT_DEPLOYS_TABLE = "client_deploys"
CLIENT_DEPLOYS_COLUMNS = {
    "version_set": "STRING",
    "channel": "STRING",
    "region": "STRING",
    "platform": "STRING",
    "artifact_type": "STRING",
    "release_id": "STRING",
    "release_created_at": "TIMESTAMP",
    "stream": "STRING",
    "patch": "STRING",
    "revision": "STRING",
    "artifact_version_id": "STRING",
    "captured_at": "TIMESTAMP",
    "source_object": "STRING",
    "loaded_at": "TIMESTAMP",
}


class DeployWriter(TableWriter):
    def ensure_table(self) -> None:
        super().ensure_table(CLIENT_DEPLOYS_TABLE, CLIENT_DEPLOYS_COLUMNS)

    def loaded_objects(self) -> set[str]:
        """Patchsieve copies already in client_deploys."""
        rows = self.query(f"SELECT DISTINCT source_object FROM `{self.table_id(CLIENT_DEPLOYS_TABLE)}`")
        return {row["source_object"] for row in rows}

    def append(self, rows: list[dict]) -> None:
        loaded_at = datetime.now(timezone.utc)
        self.load_rows(CLIENT_DEPLOYS_TABLE, CLIENT_DEPLOYS_COLUMNS, [{**row, "loaded_at": loaded_at} for row in rows])
