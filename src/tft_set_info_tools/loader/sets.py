"""Which sets in a snapshot get loaded.

Every CDragon snapshot carries every set it has data for (currently sets 1, 3,
7 and 13 onward), so without a floor each capture would reload years-old sets
nobody queries. Older sets do parse, but with a lot of unrecognized-tag
warnings.

Only each set's standard mode ("TFTSet<n>", the entry TFTSetData selects) is
loaded. Match data is joined to reference data on tft_set_number alone, so
PAIRS, PvE, TURBO and event entries would have nothing to join to, and their
units and traits mostly duplicate the standard set's.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def sets_to_load(raw: dict, min_set: int) -> list[int]:
    """Set numbers from min_set up that have a standard-mode entry in a CDragon payload."""
    numbers = {entry["number"] for entry in raw["setData"] if entry["number"] >= min_set}
    standard = {entry["mutator"] for entry in raw["setData"]}
    selected = []
    for number in sorted(numbers):
        if f"TFTSet{number}" in standard:
            selected.append(number)
        else:
            logger.warning("set %d has no TFTSet%d entry; not loading it", number, number)
    return selected
