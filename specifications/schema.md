## schema

Top-level module holding the classification vocabulary and per-source extraction logic for TFT set metadata. Depends on neither `datasource` nor `set_data` — both of those depend on it instead, so it can be imported from either without risk of a circular import.

`ItemType(Enum)` - Enum for the different item types in TFT. Each member is a 2 item tuple consisting of:
* `name` (string): The name of the item type.
* `hash` (string): The CDragon hash tag that identifies a data entry as being of this type (used by `CDragonSchema`; other schemas keep their own vocabulary mapping to the same enum members).

`AugmentTier(Enum)` - Enum for the different augment tiers in TFT. Each member is a string identifying a data entry as being of this augment tier under CDragon's tag vocabulary (used by `CDragonSchema`; other schemas map their own vocabulary to the same enum members).

`TraitStyle(Enum)` - Enum for the different trait activation styles in TFT (`BRONZE`/`SILVER`/`GOLD`/`LEGENDARY`/`PRISMATIC`), keyed by the numeric `style` code raw trait effects carry on every known source.

`TraitTier(dataclass, frozen)` - One activation threshold of a trait, normalized to the fields common across every source (`trait_name`, `trait_api_name`, `trait_desc`, `min_units`, `max_units`, `style: TraitStyle`, `variables: dict`). Sources aren't consistent about what *else* they attach to a raw effect dict beyond this core (e.g. MetaTFT sometimes adds a per-tier `desc` that CDragon never has, and not on every tier) -- consumers should use this normalized shape (via `TFTSetData.get_trait_tiers()`) rather than reading raw trait `effects` dicts directly, so they aren't exposed to that per-source variance.

`Augment(dataclass, frozen)` - One augment, normalized to `name`, `api_name`, `tier: AugmentTier | None`, `effects: dict`. Built by `TFTSetData.get_seed_augments()`, which classifies `tier` polymorphically via `SetDataSchema.augment_matches()` -- unlike `Item` below, this works the same for every registered schema.

`Item(dataclass, frozen)` - One equippable item, normalized to the fields the legacy seed CSV schema needs: `name`, `api_name`, `effects: dict`, `trait_granted`, `unique`, `num_craftables`, `type_counts: dict[str, int]` (keyed by seed column suffix, e.g. `"artifacts"`), `component_counts: dict[str, int]` (keyed by full seed column name, e.g. `"num_swords"`). Built by `TFTSetData.get_seed_items()`. `type_counts` is classified polymorphically via `item_matches()`, but the item inclusion filter and component-composition parsing are still the legacy CDragon-hash-tag vocabulary ported byte-for-byte from `tft_tools`' `seed_gen` package -- see the `_EQUIPPABLE_ITEM_HASHES`/`_NON_EQUIPPABLE_ITEM_HASHES`/`_COMPONENT_NAME_MAP` constants and `_is_seedable_item()` in `set_data.py`. These only recognize CDragon's shape; a MetaTFT-sourced set will currently see every item filtered out.

`Unit(dataclass, frozen)` - One playable/summon unit, normalized to `name`, `api_name`, `cost`, `role: str | None`, `shop_unit: bool`, `stats: dict`. Built by `TFTSetData.get_seed_units()`, which includes shop units (one or more trait tags) plus known summon units (the legacy `_SUMMON_UNITS` api-name set).

`UnitTrait(dataclass, frozen)` - One (unit, innate trait) pairing, normalized to `unit_name`, `unit_api_name`, `trait_name`, `trait_api_name`. Built by `TFTSetData.get_seed_unit_traits()`, which joins each unit's raw trait names to that trait's api name.

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
