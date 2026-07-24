## datasource

A module that provides classes for retrieving TFT metadata json from a particular source.

`TFTDataSource`: Main abstract parent base class. Defines the interface for retrieving TFT metadata json. Implements python's context manager protocol to ensure proper resource management.
Methods:
* `def read() -> dict`: Abstract method to read TFT metadata json from the source. Returns a dictionary containing the metadata.
* `def write(data: dict|TFTDataSource) -> None`: Abstract method to write TFT metadata json to the source.
* `def __enter__(self) -> TFTDataSource`: Abstract method to enter the context manager. Returns the instance of the class.
* `def __exit__(self, exc_type, exc_value, traceback) -> None`: Abstract method to exit the context manager.

Concrete Subclasses:
1. `LocalDataSource`: A class that retrieves TFT metadata json from a local file.
2. `GCPDataSource`: A class that retrieves TFT metadata json from a Google Cloud Storage bucket.
   * Uses environment variables to specify the target bucket + file path, and the credentials to access the bucket.
3. `CDragonDataSource`: A class that retrieves TFT metadata json from the Community Dragon CDN.
   * A read-only data source. Calling `write()` will raise an exception.
   * Constructor takes an optional argument that specifies the patch number to retrieve. If not specified, the latest patch is retrieved.