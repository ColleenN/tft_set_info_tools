## scripts

Module with executable scripts for interacting with set metadata.

Supported commands:

`update_src` - Copy set metadata from src to dst.

Arguments:
- src: Type of DataSource to read from. Can be any source supported by the DataSource class.
- dst: Type of DataSource to write to. Can be any source supported by the DataSource class that implements the write method.

`generate_seed` - export set metadata to csv "seed" file(s).

Arguments:
- src: Type of DataSource to read from. Can be any source supported by the DataSource class. Will use DefaultDataSource if not specified.
- dst_path: Path to the directory where the seed files will be written. Defaults to the current working directory.
- set: Set number to generate seed files for. Defaults to the latest set in the data source.
- type: Type of seed files to generate. Can be a comma-separated list of types.
Allowed values:
  - "all" (default)
  - "traits"
  - "items"
  - "units"
  - "unit_innate_traits"
  - "augments"