## set_data

Module that converts a metadata dictionary into a structured object that represents a single set's metadata.

`ItemType(Enum)` - Enum for the different item types in TFT. Each member is a 2 item tuple consisting of:
* `name` (string): The name of the item type.
* `hash` (string): The hash value that identifies a data entry as being of this type.

`AugmentTier(Enum)` - Enum for the different augment tiers in TFT. Each member is a string identifying a data entry as being of this augment tier.

`TFTSetData` - core class for representing a set's metadata.

Methods:
* `def __init__(self, data_src: dict|TFTDataSource|None = None, set_num: int|None = None)`: Constructor. 
  * Will use data from data_src if provided. Can be a dictionary of TFT data, or a `TFTDataSource` object.
  * If data_src is `None`, will try data sources in the order specified by env variable `TFT_DATASOURCE_ORDER`.
  * Will target the specified set if provided. 
  * If set_num is `None`, will instead target the latest set in the data source.

* `def get_unique_traits(self) -> list[str]`: Returns a list of unique trait names in the set.
* `def get_items(self, item_type: ItemType = None) -> dict[str, str]`: Returns a list of dictionaries describing items, optionally filtered to the specified type.
* `def get_shop_units(self)`: Returns a list of dictionaries describing shop units in the set.
  * Note: "Shop Units" are defined as units that possess one or more trait tags.
* `def get_augments(self, tier: AugmentTier = None)`: Returns a list of dictionaries describing augments in the set, optionally filtered to the specified augment tier.

Properties:
* `def mutator(self) -> str`: Returns the set's "mutator", its unique identifier in the data source.