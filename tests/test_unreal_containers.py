import pytest

from tests.test_unreal_codecs import KRAKEN_BLOCK, PLAINTEXT
from tests.unreal_builders import KEY, PakSpec, build_iostore, build_pak
from tft_set_info_tools.unreal import IoStoreReader, PakFile, open_container
from tft_set_info_tools.unreal.pak import mount_root

BIG = bytes(i * 7 % 251 for i in range(5000))
SMALL = b"Set 19 unit data"


# mount points

@pytest.mark.parametrize(("mount", "root"), [
    ("../../../", ""),
    ("../../../TFT/Content/", "TFT/Content/"),
    ("/Game", "Game/"),
])
def test_mount_root(mount, root):
    assert mount_root(mount) == root


# pak

@pytest.fixture
def pak(tmp_path):
    path = tmp_path / "pakchunk0-WindowsClient.pak"
    build_pak(path, [
        PakSpec("TFT/Content/raw.bin", SMALL),
        PakSpec("TFT/Content/Data/zlib.bin", BIG, method="Zlib"),
        PakSpec("TFT/Content/Data/one_block.bin", SMALL * 3, method="Zlib"),
        PakSpec("Engine/full.bin", BIG, method="Zlib", encoded=False),
        PakSpec("root.txt", b"top level", encoded=False),
    ])
    return path


def test_pak_lists_entries(pak):
    reader = PakFile(pak)
    assert reader.version == 11
    assert reader.methods == ["None", "Zlib", "Oodle"]
    assert {e.path: e.length for e in reader.entries} == {
        "TFT/Content/raw.bin": len(SMALL),
        "TFT/Content/Data/zlib.bin": len(BIG),
        "TFT/Content/Data/one_block.bin": len(SMALL) * 3,
        "Engine/full.bin": len(BIG),
        "root.txt": 9,
    }


def test_pak_reads_entries(pak):
    reader = PakFile(pak)
    contents = {e.path: reader.read(e) for e in reader.entries}
    assert contents["TFT/Content/raw.bin"] == SMALL
    assert contents["TFT/Content/Data/zlib.bin"] == BIG
    assert contents["TFT/Content/Data/one_block.bin"] == SMALL * 3
    assert contents["Engine/full.bin"] == BIG
    assert contents["root.txt"] == b"top level"


def test_pak_zlib_entry_uses_several_blocks(pak):
    entry, = PakFile(pak).find("*/zlib.bin")
    assert len(entry.blocks) == 3
    assert entry.block_size == 2048


def test_pak_find_and_extract(pak, tmp_path):
    reader = PakFile(pak)
    entries = reader.find("TFT/Content/*", "root.*")
    assert sorted(e.path for e in entries) == [
        "TFT/Content/Data/one_block.bin", "TFT/Content/Data/zlib.bin", "TFT/Content/raw.bin", "root.txt",
    ]
    out = tmp_path / "out"
    reader.extract(out, entries)
    assert (out / "TFT/Content/Data/zlib.bin").read_bytes() == BIG
    assert (out / "root.txt").read_bytes() == b"top level"
    assert not (out / "Engine").exists()


def test_pak_extract_can_skip_existing_files(pak, tmp_path):
    out = tmp_path / "out"
    (out / "TFT/Content").mkdir(parents=True)
    (out / "TFT/Content/raw.bin").write_bytes(b"kept")
    PakFile(pak).extract(out, overwrite=False)
    assert (out / "TFT/Content/raw.bin").read_bytes() == b"kept"
    assert (out / "root.txt").read_bytes() == b"top level"


def test_pak_paths_include_the_mount_point(tmp_path):
    path = tmp_path / "mounted.pak"
    build_pak(path, [PakSpec("Data/a.bin", SMALL)], mount_point="../../../TFT/Content/")
    reader = PakFile(path)
    assert [e.path for e in reader.entries] == ["TFT/Content/Data/a.bin"]


def test_encrypted_pak(tmp_path):
    path = tmp_path / "encrypted.pak"
    build_pak(path, [
        PakSpec("a/raw.bin", SMALL, encrypted=True),
        PakSpec("a/zlib.bin", BIG, method="Zlib", encrypted=True),
        PakSpec("a/one_block.bin", SMALL * 3, method="Zlib", encrypted=True),
        PakSpec("a/full.bin", SMALL, encrypted=True, encoded=False),
    ], key=KEY, encrypt_index=True)
    with pytest.raises(ValueError, match="AES key is required"):
        PakFile(path)
    reader = PakFile(path, aes_key=KEY)
    assert {e.path: reader.read(e) for e in reader.entries} == {
        "a/raw.bin": SMALL, "a/zlib.bin": BIG, "a/one_block.bin": SMALL * 3, "a/full.bin": SMALL,
    }


def test_oodle_pak_entry(tmp_path):
    path = tmp_path / "oodle.pak"
    build_pak(path, [PakSpec("a.bin", PLAINTEXT, method="Oodle", blocks=[KRAKEN_BLOCK])])
    reader = PakFile(path)
    assert reader.read(reader.entries[0]) == PLAINTEXT


def test_not_a_pak(tmp_path):
    path = tmp_path / "junk.pak"
    path.write_bytes(b"\0" * 300)
    with pytest.raises(ValueError, match="not a pak file"):
        PakFile(path)


def test_old_pak_version(tmp_path):
    path = tmp_path / "old.pak"
    build_pak(path, [PakSpec("a.bin", SMALL)], version=9)
    with pytest.raises(ValueError, match="unsupported pak version 9"):
        PakFile(path)


# IoStore

IO_FILES = [
    ("TFT/Plugins/GameFeatures/Set_19/Content/units.uasset", BIG),
    ("TFT/Plugins/GameFeatures/Set_19/Content/traits.uasset", SMALL),
    ("TFT/Plugins/GameFeatures/Set_18/Content/units.uasset", SMALL * 10),
    ("TFT/Content/Localization/Game.locres", b"strings"),
    ("readme.txt", b""),
]


@pytest.mark.parametrize("compress", [True, False])
def test_iostore_reads_entries(tmp_path, compress):
    utoc = tmp_path / "pakchunk1-WindowsClient.utoc"
    build_iostore(utoc, IO_FILES, compress=compress)
    reader = IoStoreReader(utoc)
    assert reader.methods == ["None", "Zlib"]
    assert reader.block_size == 64
    assert {e.path: reader.read(e) for e in reader.entries} == dict(IO_FILES)


def test_iostore_chunk_ids_follow_the_toc(tmp_path):
    utoc = tmp_path / "c.utoc"
    build_iostore(utoc, IO_FILES)
    reader = IoStoreReader(utoc)
    assert reader.chunk_id(2) == (3, 0, 2)
    entry, = reader.find("*/Set_18/*")
    assert entry.toc_index == 2


def test_iostore_find_and_extract(tmp_path):
    utoc = tmp_path / "c.utoc"
    build_iostore(utoc, IO_FILES)
    reader = IoStoreReader(utoc)
    entries = reader.find("TFT/Plugins/GameFeatures/Set_19/*")
    assert sorted(e.path.rsplit("/", 1)[1] for e in entries) == ["traits.uasset", "units.uasset"]
    out = tmp_path / "out"
    reader.extract(out, entries)
    assert (out / "TFT/Plugins/GameFeatures/Set_19/Content/units.uasset").read_bytes() == BIG
    assert not (out / "TFT/Content").exists()


def test_encrypted_iostore(tmp_path):
    utoc = tmp_path / "c.utoc"
    build_iostore(utoc, IO_FILES, key=KEY)
    with pytest.raises(ValueError, match="AES key is required"):
        IoStoreReader(utoc)
    reader = IoStoreReader(utoc, aes_key=KEY)
    assert {e.path: reader.read(e) for e in reader.entries} == dict(IO_FILES)


def test_iostore_spread_over_partitions(tmp_path):
    utoc = tmp_path / "c.utoc"
    build_iostore(utoc, IO_FILES, compress=False, partition_size=1024)
    assert (tmp_path / "c_s4.ucas").exists()
    reader = IoStoreReader(utoc)
    assert reader.partition_count > 1
    assert {e.path: reader.read(e) for e in reader.entries} == dict(IO_FILES)


def test_iostore_paths_include_the_mount_point(tmp_path):
    utoc = tmp_path / "c.utoc"
    build_iostore(utoc, [("a/b.bin", SMALL)], mount_point="../../../TFT/")
    assert [e.path for e in IoStoreReader(utoc).entries] == ["TFT/a/b.bin"]


def test_not_an_iostore(tmp_path):
    utoc = tmp_path / "c.utoc"
    utoc.write_bytes(b"\0" * 144)
    with pytest.raises(ValueError, match="not an IoStore"):
        IoStoreReader(utoc)


# open_container

def test_open_container_picks_the_reader(tmp_path, pak):
    utoc = tmp_path / "c.utoc"
    build_iostore(utoc, IO_FILES)
    assert isinstance(open_container(pak), PakFile)
    assert isinstance(open_container(utoc), IoStoreReader)
    from_ucas = open_container(tmp_path / "c.ucas")
    assert isinstance(from_ucas, IoStoreReader)
    assert from_ucas.path == str(utoc)


def test_open_container_rejects_other_files(tmp_path):
    with pytest.raises(ValueError, match="not an Unreal container"):
        open_container(tmp_path / "Game.locres")

