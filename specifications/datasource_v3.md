## datasource

A package that provides classes for retrieving TFT metadata json from a particular source.

`TFTDataSource`: Main abstract parent base class. Defines the interface for reading/writing TFT metadata json. Implements python's context manager protocol to ensure proper resource management. `read()` and `write()` are concrete, caching methods; concrete subclasses implement the actual I/O by overriding `_read()`/`_write()` instead.

Methods:
* `def read(force: bool = False) -> dict`: Returns a dictionary containing the metadata. Caches its result the first time it succeeds; subsequent calls return the cached dict without re-fetching, unless `force=True` is passed, which bypasses the cache and re-runs `_read()`.
* `def _read() -> dict`: Abstract method. Concrete subclasses implement the actual read from the source here.
* `def write(data: dict|TFTDataSource) -> None`: Writes TFT metadata json to the source. If `data` is a `TFTDataSource`, it's resolved to a dict via `data.read()` first. Updates the cache to the (resolved) data just written, so a following `read()` reflects it without re-fetching.
* `def _write(data: dict) -> None`: Abstract method. Concrete subclasses implement the actual write to the source here; always receives an already-resolved dict.
* `def __enter__(self) -> TFTDataSource`: Abstract method to enter the context manager. Returns the instance of the class.
* `def __exit__(self, exc_type, exc_value, traceback) -> None`: Abstract method to exit the context manager.

Class attributes:
* `schema: type[SetDataSchema] | None`: The `schema.SetDataSchema` (see `schema.md`) this source's data is expected to match, if known ahead of time. `None` on the base class. An origin source that always fetches from one particular endpoint (e.g. `CDragonDataSource`, `MetaTFTDataSource`) sets this to its fixed schema class; a generic passthrough source that can hold data copied from any origin (`LocalDataSource`, `GCPDataSource`) leaves it `None`, since it has no way to know ahead of time.

Methods:
* `def get_schema(self) -> type[SetDataSchema] | None`: Returns `self.schema` by default. `TFTSetData` calls this to validate a declared schema via `SetDataSchema.validate()` instead of sniffing (see `setblob_v2.md`) when it returns non-`None`, and falls back to sniffing (`detect_schema()`) when it returns `None`. `DefaultDataSource` overrides this method (rather than just setting the `schema` class attribute) since its answer depends on runtime state — see below.

Note: `TFTDataSource` and its concrete subclasses are otherwise shape-agnostic about the json they carry — they only move bytes in and out. Different sources may return the same TFT content under structurally different json shapes (e.g. Community Dragon vs. MetaTFT); interpreting a given shape is `schema`'s job (see `schema.md`), not this package's. `schema`/`get_schema()` is the one exception: it's a declaration of intent (which schema class *should* apply), not an implementation of the interpretation itself. `datasource` depends on `schema` (a plain top-level import, no circularity — `schema` depends on neither `datasource` nor `set_data`).

Concrete Subclasses:
1. `LocalDataSource`: A class that reads/writes TFT metadata json from/to a local file.
   * Constructor takes an optional `path` argument. Falls back to the `TFT_LOCAL_PATH` environment variable when not passed explicitly; raises `ValueError` if neither is set.
   * `schema` is `None` (inherited default) — a local file can hold data copied from any origin via `update_src`.
2. `GCPDataSource`: A class that reads/writes TFT metadata json from/to a Google Cloud Storage bucket.
   * Constructor takes optional `bucket`/`blob_path` arguments, falling back to the `TFT_GCP_BUCKET`/`TFT_GCP_BLOB_PATH` environment variables; raises `ValueError` if either is unset after that fallback.
   * Credentials and project are read from environment variables: `TFT_GCP_CREDENTIALS` (path to a service account json file; falls back to application default credentials if unset) and `TFT_GCP_PROJECT` (optional).
   * `__enter__`/`__exit__` create and close the underlying GCS client so it's reused across `read()`/`write()` calls.
   * `schema` is `None` (inherited default), for the same reason as `LocalDataSource`.
3. `CDragonDataSource`: A class that reads TFT metadata json from the Community Dragon CDN.
   * A read-only data source. Calling `write()` raises `NotImplementedError`.
   * Constructor takes an optional `patch` argument specifying the patch to retrieve (e.g. `"14.1"`), falling back to the `TFT_CDRAGON_PATCH` environment variable. If not specified, defaults to `"latest"`.
   * Exposes a `url` property returning the resolved CommunityDragon URL for the configured patch. Its json covers every set at once (see `CDragonSchema` in `setblob_v2.md`).
   * `schema` is `CDragonSchema`.
   * `__enter__`/`__exit__` create and close an `httpx.Client` so it's reused across `read()` calls.
4. `MetaTFTDataSource`: A class that reads TFT metadata json from MetaTFT's lookup files.
   * A read-only data source. Calling `write()` raises `NotImplementedError`.
   * Unlike `CDragonDataSource`, MetaTFT publishes one file per set (e.g. `TFTSet18_pbe_en_us.json`), so there's no generic patch/set template to build a URL from. Constructor takes an optional `url` argument, falling back to the `TFT_METATFT_URL` environment variable, defaulting to `"https://data.metatft.com/lookups/TFTSet18_pbe_en_us.json"` if neither is set.
   * Exposes a `url` property returning the configured URL. Its json is scoped to a single set (see `MetaTFTSchema` in `setblob_v2.md`).
   * `schema` is `MetaTFTSchema`.
   * `__enter__`/`__exit__` create and close an `httpx.Client` so it's reused across `read()` calls.
   * Not included in `DefaultDataSource`'s default fallback order (its data is PBE/beta), even though it's registered by name — opt in explicitly via `TFT_DATASOURCE_ORDER`.
5. `DefaultDataSource`: A read-only class that reads from the first working source in a priority order, so callers don't have to pick a concrete source themselves.
   * Order is a comma-separated list of registry names (`"local"`, `"gcp"`, `"cdragon"`, `"metatft"`), taken from the `TFT_DATASOURCE_ORDER` environment variable. Defaults to `"gcp,cdragon,local"` if unset; raises `ValueError` if explicitly set to an empty/blank value.
   * `read()`/`_read()` tries each name in turn, skipping one that's unconfigured (its constructor raises `ValueError`) or fails to read (network error, missing file, malformed response, etc.), and caches whichever source works for cleanup via `__exit__`. Raises `RuntimeError` (aggregating each attempt's failure) if none work.
   * Calling `read(force=True)` re-runs the whole fallback search from scratch, closing whichever source was previously resolved first to avoid leaking its connection.
   * Overrides `get_schema()` to proxy to whichever concrete source resolved during the last `read()` (`None` before any successful read, or if that source is itself a generic passthrough with no fixed schema) — this can't be a plain `schema` class attribute since the answer depends on runtime resolution.
   * A read-only data source. Calling `write()` raises `NotImplementedError`, since there's no single unambiguous backend to write to across an ordered list of sources.
