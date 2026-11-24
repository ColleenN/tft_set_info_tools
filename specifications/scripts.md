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
`load` - append mirrored Community Dragon snapshots to the BigQuery reference tables. The scheduled loader job runs this from the image built by `cloudbuild.yaml`.

Each run loads every capture under `snapshots/cdragon/<channel>/` that isn't in the dataset's `loaded_captures` table yet, paired with its Team Planner capture. For each set from `--min-set` up (standard mode only), the reference table generators' rows are appended with version columns: `channel`, `build` (in match-record form, e.g. `16.21.829.8620`), `cdragon_version`, `cdragon_status`, `captured_at`, `source_object`, `set_number` and `mutator`. Tables are created if missing.

- A capture whose CDragon status wasn't `done` is recorded as skipped. Captures saved before the mirror recorded a status are loaded with a NULL `cdragon_status`.
- A capture that fails is retried on the next run; the command exits with an error after trying the rest. Rows left by a capture that failed partway are deleted before it's loaded again.
- Credentials come from application default credentials; `TFT_GCP_PROJECT` sets the project if needed.

Each option falls back to an environment variable, so the job can keep its settings in a file passed with `--env-file`:
- `--bucket` / `TFT_LOADER_BUCKET`: bucket holding the snapshots. Required.
- `--dataset` / `TFT_LOADER_DATASET`: BigQuery dataset for the reference tables, as `[project.]dataset`. Required.
- `--min-set` / `TFT_LOADER_MIN_SET`: lowest set number to load. Required.
- `--channels` / `TFT_LOADER_CHANNELS`: comma-separated channels. Defaults to `live,pbe`.

`unreal` - list, extract and convert files from the standalone TFT client's Unreal containers: `.pak` files and IoStore containers (`.utoc` plus its `.ucas` files). Files come out decrypted and decompressed. Needs the `unreal` extra, which brings in `cryptography` for decryption and `pyooz` for Oodle.

Paths are relative to the game root, e.g. `TFT/Plugins/GameFeatures/Set_19/...`.

Subcommands:
- `list <container>`: print each file's uncompressed size and path.
- `extract <container>`: write the files under `-o`/`--output` (defaults to the container's path without its extension), at their container paths. `--lazy` skips files that already exist.
- `locres-dump <locres>...`: merge `.locres` string tables in order, later files winning, and write them as JSON keyed by namespace, then key. `-o`/`--output` names the file; stdout otherwise.
- `convert <extracted>...`: build a CDragon-shaped capture of a set from folders of extracted files, for upload while CDragon has no export for the client. Each folder is an `extract` output; where folders share a path, the first wins. Writes `<timestamp>_en_us.json.gz` and `metadata_<timestamp>.json` into `-o`/`--output`, with the metadata fields mirrored captures carry, and prints a summary. The folders need the set's `DA_*` and `CT_*` assets, `DT_<set>_ChampionsTable`, the item assets, and the locale's `.locres` files.
  - `-b` / `--build`: the client build, e.g. `rls-19.1.0.6018196`, which sets `build` and `cdragon-version`.
  - `-s` / `--set`: the set number. Defaults to the highest set with champions.
  - `--locale`: the strings' locale. Defaults to `en-US`.
  - `--previous` and `--previous-raw`, together: the previous upload's capture and the `--raw` export written with it. Item tags translated to CDragon's codes by hand are reused for items whose client tags haven't changed, and so is the set's split into items and augments. The command stops, naming the items, when a tag translation or split is needed for an item. Without them, tags stay as the client's and the set's items split by asset kind.
  - Whichever way tags are translated, items with the client tag `Item.Equippable.Item.Tacticians` get CDragon's Tactician item code (`{d304f83b}`), and items with `Item.Equippable.Item.ThiefsGloves` get its Thief's Gloves code (`{218b53a5}`).
  - `--raw`: also write the export before those fixes, to pass as `--previous-raw` next time.

  The capture fills in names, descriptions, costs, roles, traits, stats, icons, item tags and recipes, plus curve-table values: attack damage by star level, ability variables and trait breakpoint variables. Each champion gets `shopUnit` from the champions table. Trait breakpoints get CDragon's styles, and a trait with none gets a single breakpoint at one unit.

`list` and `extract` also take:
- `-p` / `--pattern`: only files whose path matches this shell-style pattern. Repeatable.
- `-k` / `--aes-key` / `TFT_UE_AES_KEY`: the container's AES-256 key, as hex. Needed only for encrypted containers.
