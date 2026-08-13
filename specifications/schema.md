## schema

Top-level module holding the classification vocabulary and per-source extraction logic for TFT set metadata. Depends on neither `datasource` nor `set_data` — both of those depend on it instead, so it can be imported from either without risk of a circular import.

`ItemType(Enum)` - Enum for the different item types in TFT. Each member is a 2 item tuple consisting of:
* `name` (string): The name of the item type.
* `hash` (string): The CDragon hash tag that identifies a data entry as being of this type (used by `CDragonSchema`; other schemas keep their own vocabulary mapping to the same enum members).

`AugmentTier(Enum)` - Enum for the different augment tiers in TFT. Each member is a string identifying a data entry as being of this augment tier under CDragon's tag vocabulary (used by `CDragonSchema`; other schemas map their own vocabulary to the same enum members).

`AUGMENT_HASH_MARKER` - the CDragon tag that marks an entry in the shared `items` pool as an augment rather than an item. Only meaningful to `CDragonSchema`.

`SetDataSchema` (ABC) - interface for locating/classifying a set's data within one source's json shape.

Methods:
* `def matches(raw: dict) -> bool`: (staticmethod) Whether `raw` looks like this schema's shape.
* `def validate(self, raw: dict) -> None`: Concrete method, built on `matches()`. Raises `ValueError` unless `raw` actually matches this schema. Used to assert a source's declared schema (`TFTDataSource.get_schema()`, see `datasource_v3.md`) actually holds, rather than silently trusting it.
* `def latest_set_number(self, raw: dict) -> int`: The highest set number present in `raw`.
* `def extract(self, raw: dict, set_num: int) -> ExtractedSet`: Locates the given set's data within `raw`. Raises `ValueError` if not found.
* `def item_matches(self, item: dict, item_type: ItemType) -> bool`: Whether `item` belongs to `item_type`.
* `def augment_matches(self, augment: dict, tier: AugmentTier) -> bool`: Whether `augment` belongs to `tier`.

`ExtractedSet` (dataclass) - a set's data once located within a raw payload: `mutator`, `units`, `traits`, `items`, `augments`.

`def detect_schema(raw: dict) -> SetDataSchema`: Picks the matching schema by sniffing `raw` against each registered `SetDataSchema.matches()`. Raises `ValueError` if none match.

Concrete Schemas:
1. `CDragonSchema`: Community Dragon shape (`{"setData": [...], "items": [...]}`, one entry per set, augments living in the shared `items` pool marked with the `AUGMENT_HASH_MARKER` tag).
2. `MetaTFTSchema`: MetaTFT shape (one file per set; `units`/`traits`/`items`/`augments` as separate top-level lists; item category is a readable tag string via `ITEM_TYPE_TAGS`; augment tier is a plain `rarity` field via `AUGMENT_TIER_VALUES`; set number is parsed out of `_metadata.set`, e.g. `"TFTSet18"` → `18`).
   * `ITEM_TYPE_TAGS` only covers item categories observed in a sample response (artifact, emblem, radiant, component) — `item_matches()` for an unmapped `ItemType` always returns `False`.
