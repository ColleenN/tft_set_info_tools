## scripts

Module with executable scripts for interacting with set metadata.

Global options:
- `--env-file`: Path to a .env file with `KEY=VALUE` lines to load into the environment before running the command. Variables already set in the environment take precedence over values from the file.

Supported commands:

`update_src` - Copy set metadata from src to dst.

Arguments:
- src: Type of DataSource to read from. Can be any source supported by the DataSource class.
- dst: Type of DataSource to write to. Can be any source supported by the DataSource class that implements the write method.
- `--src-patch`: Community Dragon patch/version to fetch (e.g. "13.24"). Only valid when src is "cdragon". Defaults to "latest".

`generate_seed` - export set metadata to csv "seed" file(s).

Arguments:
- src: Type of DataSource to read from. Can be any source supported by the DataSource class. Will use DefaultDataSource if not specified.
- dst_path: Path to the directory where the seed files will be written. Defaults to the current working directory.
- set: Set number to generate seed files for. Defaults to the latest set in the data source.
- type: Type of seed files to generate. Can be a comma-separated list of types.
Allowed values:
  - "all" (default)
  - "trait_tiers"
  - "items"
  - "units"
  - "unit_innate_traits"
  - "augments"