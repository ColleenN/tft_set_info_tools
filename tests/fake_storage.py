"""A fake storage client that lists blob names and metadata."""


class FakeBlob:
    def __init__(self, name, metadata):
        self.name = name
        self.metadata = metadata


class FakeClient:
    def __init__(self, blobs):
        self.blobs = blobs
        self.listed = []

    def list_blobs(self, bucket, prefix):
        self.listed.append((bucket, prefix))
        return [b for b in self.blobs if b.name.startswith(prefix)]
