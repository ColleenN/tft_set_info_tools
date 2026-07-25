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

Concrete Subclasses:
1. `LocalDataSource`: A class that reads/writes TFT metadata json from/to a local file.
   * Constructor takes an optional `path` argument. Falls back to the `TFT_LOCAL_PATH` environment variable when not passed explicitly; raises `ValueError` if neither is set.
2. `GCPDataSource`: A class that reads/writes TFT metadata json from/to a Google Cloud Storage bucket.
   * Constructor takes optional `bucket`/`blob_path` arguments, falling back to the `TFT_GCP_BUCKET`/`TFT_GCP_BLOB_PATH` environment variables; raises `ValueError` if either is unset after that fallback.
   * Credentials and project are read from environment variables: `TFT_GCP_CREDENTIALS` (path to a service account json file; falls back to application default credentials if unset) and `TFT_GCP_PROJECT` (optional).
   * `__enter__`/`__exit__` create and close the underlying GCS client so it's reused across `read()`/`write()` calls.
3. `CDragonDataSource`: A class that reads TFT metadata json from the Community Dragon CDN.
   * A read-only data source. Calling `write()` raises `NotImplementedError`.
   * Constructor takes an optional `patch` argument specifying the patch to retrieve (e.g. `"14.1"`). If not specified, defaults to `"latest"`.
   * Exposes a `url` property returning the resolved CommunityDragon URL for the configured patch.
   * `__enter__`/`__exit__` create and close an `httpx.Client` so it's reused across `read()` calls.
4. `DefaultDataSource`: A read-only class that reads from the first working source in a priority order, so callers don't have to pick a concrete source themselves.
   * Order is a comma-separated list of registry names (`"local"`, `"gcp"`, `"cdragon"`), taken from the `TFT_DATASOURCE_ORDER` environment variable. Defaults to `"gcp,cdragon,local"` if unset; raises `ValueError` if explicitly set to an empty/blank value.
   * `read()`/`_read()` tries each name in turn, skipping one that's unconfigured (its constructor raises `ValueError`) or fails to read (network error, missing file, malformed response, etc.), and caches whichever source works for cleanup via `__exit__`. Raises `RuntimeError` (aggregating each attempt's failure) if none work.
   * Calling `read(force=True)` re-runs the whole fallback search from scratch, closing whichever source was previously resolved first to avoid leaking its connection.
   * A read-only data source. Calling `write()` raises `NotImplementedError`, since there's no single unambiguous backend to write to across an ordered list of sources.
