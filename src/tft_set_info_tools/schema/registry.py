"""Schema detection: picks the matching SetDataSchema for a raw payload."""

from __future__ import annotations

from tft_set_info_tools.schema.base import SetDataSchema
from tft_set_info_tools.schema.cdragon import CDragonSchema
from tft_set_info_tools.schema.metatft import MetaTFTSchema

SCHEMAS: tuple[SetDataSchema, ...] = (CDragonSchema(), MetaTFTSchema())


def detect_schema(raw: dict) -> SetDataSchema:
    for schema in SCHEMAS:
        if schema.matches(raw):
            return schema
    raise ValueError("Could not determine the schema of the provided data")
