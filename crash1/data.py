"""Static game data for Crash Bandicoot (PS1, NTSC-U SCUS-94900).

Sources:
- Level IDs: esplonky/c1 ``src/common.h`` (``LID_*``), consistent with goocdump ``goolstdlib.gooc`` level codes
  read as base-62 (``'0'-'9'``, ``'a'-'z'`` = 10-35, ``'A'-'Z'`` = 36-61).
- Map node order and key branches: goocdump ``Crash 1/NTSC-J/IsldC.gooc`` (``MapSetLevelParams``). The NTSC-J build
  swaps Sunset Vista (node 24 in J) and Slippery Climb (node 16 in J); this table uses the NTSC-U order.
- Colored gems: N. Sane Trilogy guides (The Escapist, Nintendo Life). Bits: goolstdlib NTSC-U aliases.

Anything marked VERIFY still needs to be confirmed in an emulator; see docs/DESIGN.md and tools/VERIFY.md at the repository root.
"""
from dataclasses import dataclass, field
from enum import Enum


class Kind(Enum):
    LEVEL = "level"
    BOSS = "boss"
    FINAL_BOSS = "final_boss"
    SECRET = "secret"


class Gem(Enum):
    NONE = "none"
    CLEAR = "clear"
    GREEN = "Green"
    ORANGE = "Orange"
    BLUE = "Blue"
    RED = "Red"
    PURPLE = "Purple"
    YELLOW = "Yellow"

    @property
    def is_colored(self) -> bool:
        return self not in (Gem.NONE, Gem.CLEAR)

    @property
    def item_name(self) -> str:
        return f"{self.value} Gem"


@dataclass(frozen=True)
class Level:
    name: str
    lid: int
    """In-game level ID (``LID_*``)"""
    vanilla_node: int
    """Map node in vanilla NTSC-U. Secret levels use the map script's branch node IDs (40, 50)."""
    kind: Kind
    gem: Gem = Gem.CLEAR
    """The gem this level awards"""
    gem_requires: tuple[Gem, ...] = field(default=())
    """Colored gems whose path is in this level (needed for all boxes, hence for the gem)"""

    @property
    def is_boss(self) -> bool:
        return self.kind in (Kind.BOSS, Kind.FINAL_BOSS)

    @property
    def complete_location(self) -> str:
        return f"{self.name} - Defeated" if self.is_boss else f"{self.name} - Complete"

    @property
    def gem_location(self) -> str:
        return f"{self.name} - Gem"


LEVELS: tuple[Level, ...] = (
    # Island 1 (N. Sanity Island)
    Level("N. Sanity Beach", 0x09, 1, Kind.LEVEL),
    Level("Jungle Rollers", 0x0C, 2, Kind.LEVEL, gem_requires=(Gem.GREEN,)),
    Level("The Great Gate", 0x12, 3, Kind.LEVEL, gem_requires=(Gem.YELLOW,)),
    Level("Boulders", 0x0E, 4, Kind.LEVEL),
    Level("Upstream", 0x0F, 5, Kind.LEVEL, gem_requires=(Gem.ORANGE,)),
    Level("Papu Papu", 0x0A, 6, Kind.BOSS, gem=Gem.NONE),
    Level("Rolling Stones", 0x15, 7, Kind.LEVEL, gem_requires=(Gem.BLUE,)),
    Level("Hog Wild", 0x11, 8, Kind.LEVEL),
    Level("Native Fortress", 0x1A, 9, Kind.LEVEL, gem_requires=(Gem.RED,)),
    # Island 2 (Wumpa Island)
    Level("Up the Creek", 0x18, 10, Kind.LEVEL),
    Level("Ripper Roo", 0x17, 11, Kind.BOSS, gem=Gem.NONE),
    Level("The Lost City", 0x20, 12, Kind.LEVEL, gem=Gem.GREEN),
    Level("Temple Ruins", 0x1C, 13, Kind.LEVEL),
    Level("Road to Nowhere", 0x14, 14, Kind.LEVEL, gem_requires=(Gem.RED,)),
    Level("Boulder Dash", 0x13, 15, Kind.LEVEL, gem_requires=(Gem.PURPLE,)),
    Level("Sunset Vista", 0x23, 16, Kind.LEVEL),  # VERIFY: node 16 on NTSC-U (node 24 on NTSC-J)
    Level("Koala Kong", 0x21, 17, Kind.BOSS, gem=Gem.NONE),
    # Island 3 (Cortex Island)
    Level("Heavy Machinery", 0x06, 18, Kind.LEVEL),
    Level("Cortex Power", 0x03, 19, Kind.LEVEL, gem_requires=(Gem.BLUE,)),
    Level("Generator Room", 0x05, 20, Kind.LEVEL, gem=Gem.ORANGE),
    Level("Toxic Waste", 0x07, 21, Kind.LEVEL, gem=Gem.BLUE),
    Level("Pinstripe", 0x08, 22, Kind.BOSS, gem=Gem.NONE),
    Level("The High Road", 0x16, 23, Kind.LEVEL),
    Level("Slippery Climb", 0x2E, 24, Kind.LEVEL, gem=Gem.RED),  # VERIFY: node 24 on NTSC-U
    # VERIFY: whether the Yellow path in Lights Out is needed for its gem (it leads to an alternate exit)
    Level("Lights Out", 0x28, 25, Kind.LEVEL, gem=Gem.PURPLE),
    Level("Jaws of Darkness", 0x1D, 26, Kind.LEVEL, gem_requires=(Gem.BLUE,)),
    Level("Castle Machinery", 0x37, 27, Kind.LEVEL, gem_requires=(Gem.GREEN,)),
    Level("Dr. N. Brio", 0x1B, 28, Kind.BOSS, gem=Gem.NONE),
    Level("The Lab", 0x29, 29, Kind.LEVEL, gem=Gem.YELLOW),
    Level("The Great Hall", 0x2C, 30, Kind.LEVEL, gem=Gem.NONE),  # VERIFY: assumed to be the level without a gem
    Level("Dr. N. Cortex", 0x1F, 31, Kind.FINAL_BOSS, gem=Gem.NONE),
    # Secret levels (map branches)
    Level("Whole Hog", 0x1E, 50, Kind.SECRET),
    Level("Fumbling in the Dark", 0x2A, 40, Kind.SECRET),
)

LEVEL_BY_NAME: dict[str, Level] = {level.name: level for level in LEVELS}
LEVEL_BY_LID: dict[int, Level] = {level.lid: level for level in LEVELS}

MAP_NODES = 31
"""Number of nodes on the main map path. Node 31 is always Dr. N. Cortex."""

FINAL_BOSS: Level = LEVEL_BY_NAME["Dr. N. Cortex"]
MAIN_LEVELS: tuple[Level, ...] = tuple(sorted(
    (level for level in LEVELS if level.kind != Kind.SECRET),
    key=lambda level: level.vanilla_node,
))
SHUFFLABLE_LEVELS: tuple[Level, ...] = tuple(level for level in MAIN_LEVELS if level.kind != Kind.FINAL_BOSS)
SECRET_LEVELS: tuple[Level, ...] = tuple(level for level in LEVELS if level.kind == Kind.SECRET)
GEM_LEVELS: tuple[Level, ...] = tuple(level for level in LEVELS if level.gem != Gem.NONE)
COLORED_GEMS: tuple[Gem, ...] = (Gem.GREEN, Gem.ORANGE, Gem.BLUE, Gem.RED, Gem.PURPLE, Gem.YELLOW)
CLEAR_GEM_COUNT = sum(1 for level in GEM_LEVELS if level.gem == Gem.CLEAR)


@dataclass(frozen=True)
class Key:
    item_name: str
    opens: str
    """The secret level this key opens"""
    branch_node: int
    """Map node where the secret path branches off (fixed: the map script checks the node, not the level)"""
    source: str
    """Level whose Cortex bonus round awards the key in vanilla"""
    pool2_bit: int

    @property
    def location(self) -> str:
        return f"{self.source} - Key"


KEYS: tuple[Key, ...] = (
    # IsldC.gooc: at node 25 (Lights Out), ITEM_KEY1 (ITEMPOOL2 bit 10, "jaws of darkness key") opens node 40.
    Key("Fumbling in the Dark Key", "Fumbling in the Dark", 25, "Jaws of Darkness", 10),
    # IsldC.gooc: at node 15 (Boulder Dash), ITEM_KEY2 (ITEMPOOL2 bit 20, "sunset vista key") opens node 50.
    Key("Whole Hog Key", "Whole Hog", 15, "Sunset Vista", 20),
)
KEY_BY_SECRET: dict[str, Key] = {key.opens: key for key in KEYS}

assert len(MAIN_LEVELS) == MAP_NODES
assert [level.vanilla_node for level in MAIN_LEVELS] == list(range(1, MAP_NODES + 1))
assert len(GEM_LEVELS) == 26, len(GEM_LEVELS)
assert sorted(level.gem.value for level in GEM_LEVELS if level.gem.is_colored) == sorted(
    gem.value for gem in COLORED_GEMS
), "every colored gem must have exactly one source level"
