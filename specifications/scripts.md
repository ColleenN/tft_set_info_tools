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
