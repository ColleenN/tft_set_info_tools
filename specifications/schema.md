## schema

Top-level package holding the classification vocabulary and per-source extraction logic for TFT set metadata. Depends on neither `datasource` nor `set_data` — both of those depend on it instead, so it can be imported from either without risk of a circular import. Everything below is re-exported from `tft_set_info_tools.schema` regardless of which submodule defines it: `vocab.py` (enums), `models.py` (normalized dataclasses), `base.py` (`SetDataSchema`), `cdragon.py`/`metatft.py` (concrete schemas), `registry.py` (`SCHEMAS`/`detect_schema`).

`ItemType(Enum)` - Enum for the different item types in TFT. Each member is a 2 item tuple consisting of:
* `name` (string): The name of the item type.
* `hash` (string): The CDragon hash tag that identifies a data entry as being of this type (used by `CDragonSchema`; other schemas keep their own vocabulary mapping to the same enum members).

`AugmentTier(Enum)` - Enum for the different augment tiers in TFT. Each member is a string identifying a data entry as being of this augment tier under CDragon's tag vocabulary (used by `CDragonSchema`; other schemas map their own vocabulary to the same enum members).

`Component(Enum)` - Enum for the 10 basic TFT component items (`SWORD`/`VEST`/`PAN`/`BELT`/`ROD`/`CLOAK`/`BOW`/`GLOVES`/`SPATULA`/`TEAR`), common to every set. Unlike `ItemType`, no member carries a source-specific vocabulary value -- each concrete `SetDataSchema` owns its own raw-api-name-to-`Component` mapping entirely privately (see `get_component()` below), since sources aren't consistent about what api name a given component uses (e.g. CDragon's `TFT_Item_BFSword` vs. MetaTFT's `DA_Component_BFSword`).

`TraitStyle(Enum)` - Enum for the different trait activation styles in TFT (`BRONZE`/`SILVER`/`GOLD`/`LEGENDARY`/`PRISMATIC`), keyed by the numeric `style` code raw trait effects carry on every known source.

`TraitTier(dataclass, frozen)` - One activation threshold of a trait, normalized to the fields common across every source (`trait_name`, `trait_api_name`, `trait_desc`, `min_units`, `max_units`, `style: TraitStyle`, `variables: dict`). Sources aren't consistent about what *else* they attach to a raw effect dict beyond this core (e.g. MetaTFT sometimes adds a per-tier `desc` that CDragon never has, and not on every tier) -- consumers should use this normalized shape (via `TFTSetData.get_trait_tiers()`) rather than reading raw trait `effects` dicts directly, so they aren't exposed to that per-source variance.

`Augment(dataclass, frozen)` - One augment, normalized to `name`, `api_name`, `tier: AugmentTier | None`, `effects: dict`. Built by `TFTSetData.get_normalized_augments()`, which classifies `tier` polymorphically via `SetDataSchema.get_augment_tier()` -- unlike `Item` below, this works the same for every registered schema.

`Item(dataclass, frozen)` - One equippable item, normalized to the fields the legacy seed CSV schema needs: `name`, `api_name`, `effects: dict`, `trait_granted`, `unique`, `num_craftables`, `type_counts: dict[str, int]` (keyed by seed column suffix, e.g. `"artifacts"`), `component_counts: dict[str, int]` (keyed by full seed column name, e.g. `"num_swords"`). Built by `TFTSetData.get_equippable_items()`, entirely through polymorphic `SetDataSchema` methods (`get_item_types()`, `get_component()`, `is_equippable_item()`) -- no CDragon/MetaTFT-specific logic lives in `set_data.py` itself. `MetaTFTSchema.is_equippable_item()` is still a best-effort approximation though (see its docstring), so a MetaTFT-sourced set may under-include real equipment the same way `get_item_types()` does.

`Unit(dataclass, frozen)` - One playable/summon unit, normalized to `name`, `api_name`, `cost`, `role: str | None`, `shop_unit: bool`, `stats: dict`. Built by `TFTSetData.get_normalized_units()`, which includes shop units (one or more trait tags) plus known summon units (the legacy `SUMMON_UNITS` api-name set).

`UnitTrait(dataclass, frozen)` - One (unit, innate trait) pairing, normalized to `unit_name`, `unit_api_name`, `trait_name`, `trait_api_name`. Built by `TFTSetData.get_normalized_unit_traits()`, which joins each unit's raw trait names to that trait's api name.

`AUGMENT_HASH_MARKER` - the CDragon tag that marks an entry in the shared `items` pool as an augment rather than an item. Only meaningful to `CDragonSchema`.

`SetDataSchema` (ABC) - interface for locating/classifying a set's data within one source's json shape.

Methods:
* `def matches(raw: dict) -> bool`: (staticmethod) Whether `raw` looks like this schema's shape.
* `def validate(self, raw: dict) -> None`: Concrete method, built on `matches()`. Raises `ValueError` unless `raw` actually matches this schema. Used to assert a source's declared schema (`TFTDataSource.get_schema()`, see `datasource_v3.md`) actually holds, rather than silently trusting it.
* `def latest_set_number(self, raw: dict) -> int`: The highest set number present in `raw`.
* `def extract(self, raw: dict, set_num: int) -> ExtractedSet`: Locates the given set's data within `raw`. Raises `ValueError` if not found.
* `def get_item_types(self, item: dict) -> frozenset[ItemType]`: Every `ItemType` that `item` belongs to.
* `def get_augment_tier(self, augment: dict) -> AugmentTier | None`: The `AugmentTier` that `augment` belongs to, or `None` if it doesn't match any known tier.
* `def get_component(self, item: dict) -> Component | None`: The `Component` that `item` is, or `None` if it isn't one of the 10 basic components (e.g. it's a craftable/completed item). Only reads `item["apiName"]`, so a minimal dict works too (e.g. one built from a craftable item's raw `"composition"` list of api names).
* `def is_equippable_item(self, item: dict) -> bool`: Whether `item` is real equippable gear, excluding consumables/markers/other non-equipment entries that share the same raw items pool on some sources.

`ExtractedSet` (dataclass) - a set's data once located within a raw payload: `mutator`, `units`, `traits`, `items`, `augments`.

`def detect_schema(raw: dict) -> SetDataSchema`: Picks the matching schema by sniffing `raw` against each registered `SetDataSchema.matches()`. Raises `ValueError` if none match.

Concrete Schemas:
1. `CDragonSchema`: Community Dragon shape (`{"setData": [...], "items": [...]}`, one entry per set, augments living in the shared `items` pool marked with the `AUGMENT_HASH_MARKER` tag).
   * `get_component()`/`is_equippable_item()` use the legacy CDragon-hash-tag/api-name vocabulary (`_COMPONENT_API_NAMES`, `_EQUIPPABLE_ITEM_HASHES`, `_NON_EQUIPPABLE_ITEM_HASHES`), ported byte-for-byte from the `tft_tools` `seed_gen` package.
2. `MetaTFTSchema`: MetaTFT shape (one file per set; `units`/`traits`/`items`/`augments` as separate top-level lists; item category is a readable tag string via `ITEM_TYPE_TAGS`; augment tier is a plain `rarity` field via `AUGMENT_TIER_VALUES`; component api names are mapped via `COMPONENT_API_NAMES`; set number is parsed out of `_metadata.set`, e.g. `"TFTSet18"` → `18`).
   * `ITEM_TYPE_TAGS` only covers item categories observed in a sample response (artifact, emblem, radiant, component) — `get_item_types()` never includes an unmapped `ItemType`, and since `is_equippable_item()` is defined in terms of `get_item_types()`, an item of an unmapped type is also never considered equippable.
