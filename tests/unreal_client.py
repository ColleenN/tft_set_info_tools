"""A small extracted client: Set 19 data assets, a curve table and the English strings."""

from __future__ import annotations

import struct
from pathlib import Path

from tests.unreal_builders import build_locres, build_zen, curve_table, text_property

SET = "TFT/Plugins/GameFeatures/Set_19/Content"
ITEMS = "TFT/Plugins/GameFeatures/Item_Shared/Content/Item"
LOCALIZATION = "TFT/Content/Localization"

STRINGS = {
    "": {
        "00000000000000000000000000000001": "Kalista",
        "00000000000000000000000000000002": "Pierce",
        "00000000000000000000000000000003": "Kalista fires a spear that deals 200 damage.",
        "00000000000000000000000000000004": "Ranger",
        "00000000000000000000000000000005": "Rangers gain Attack Speed.",
        "00000000000000000000000000000006": "(2) 10% Attack Speed\n(4) 25% Attack Speed",
        "00000000000000000000000000000007": "Deathblade",
        "00000000000000000000000000000008": "Gain 50% Attack Damage.",
        "00000000000000000000000000000009": "B.F. Sword",
        "0000000000000000000000000000000A": "Cybernetic Bulk",
        "0000000000000000000000000000000B": "Your units gain 200 Health.",
    },
}
CHUNK_STRINGS = {"": {"00000000000000000000000000000002": "Piercing Spear"}}


def stat(name: str, value: float) -> bytes:
    """A stat stored as a name/value pair."""
    raw = name.encode() + b"\0"
    return struct.pack("<i", len(raw)) + raw + struct.pack("<I", 1) + b"\0" * 8 + struct.pack("<iif", -1, -1, value)


def texts(*keys: int) -> bytes:
    return b"".join(text_property(f"{k:032X}", "source") for k in keys)


def component_references(names: list[str], component: str, count: int) -> bytes:
    path = names.index(f"/Item_Shared/Item/Component_{component}/DA_Component_{component}")
    asset = names.index(f"DA_Component_{component}")
    return struct.pack("<IIII", path, 0, asset, 0) * count


def write(root: Path, path: str, data: bytes) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def build_client(root: Path) -> None:
    write(root, f"{SET}/Champions/Kalista/DA_Kalista19.uasset", build_zen(
        ["DA_Kalista19", "Identifier.Champion.Kalista", "TwoCost", "DA_Role_ADCarry",
         "/Set_19/Champions/Kalista/T_Kalista_PC", "/Set_19/Champions/Kalista/T_Kalista_SpellIcon"],
        # The folder's case differs from the trait asset's, as some client references do.
        ["/Set_19/traits/ranger/DA_Ranger"],
        body=texts(1, 2, 3) + stat("Armor", 30) + stat("HealthMax", 650) + stat("AttackSpeed", 0.7),
    ))
    write(root, f"{SET}/Champions/Kalista/CT_Kalista.uasset", curve_table({
        "AutoAttackDamage": [(1, 50), (2, 75), (3, 112.5), (4, 168.75)],
        "Damage": [(1, 200), (2, 300), (3, 450)],
    }))
    write(root, f"{SET}/Traits/Ranger/DA_Ranger.uasset", build_zen(
        ["DA_Ranger", "Identifier.Trait.Ranger", "/Set_19/Traits/Ranger/T_Ranger"], body=texts(4, 5, 6)))
    write(root, f"{SET}/Traits/Ranger/CT_Ranger.uasset", curve_table({"AttackSpeed": [(1, 10), (2, 25)]}))
    deathblade = ["DA_Deathblade", "Identifier.Item.Deathblade", "Item.Completed", "/Item_Shared/Item/Deathblade/T_Deathblade",
                  "/Item_Shared/Item/Component_BFSword/DA_Component_BFSword", "DA_Component_BFSword"]
    write(root, f"{ITEMS}/Deathblade/DA_Deathblade.uasset", build_zen(
        deathblade, ["/Item_Shared/Item/Component_BFSword/DA_Component_BFSword"],
        body=texts(7, 8) + component_references(deathblade, "BFSword", 2),
    ))
    write(root, f"{ITEMS}/Component_BFSword/DA_Component_BFSword.uasset", build_zen(
        ["DA_Component_BFSword", "Identifier.Item.BFSword", "Item.Component"], body=texts(9)))
    write(root, f"{SET}/Augments/DA_CyberneticBulk.uasset", build_zen(
        ["DA_CyberneticBulk", "Identifier.Augment.CyberneticBulk", "Augment.Silver"], body=texts(10, 11)))
    write(root, f"{SET}/Champions/DA_NotAnAsset.uasset", b"\0" * 8)
    write(root, f"{SET}/DT_19_ChampionsTable.uasset", build_zen(
        ["DT_19_ChampionsTable", "DA_Kalista19", "/Set_19/Champions/Kalista/DA_Kalista19"]))
    write(root, f"{LOCALIZATION}/Game/en-US/Game.locres", build_locres(STRINGS))
    write(root, f"{LOCALIZATION}/Game_locchunk1/en-US/Game_locchunk1.locres", build_locres(CHUNK_STRINGS))
