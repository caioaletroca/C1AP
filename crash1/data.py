"""Static game data for Crash Bandicoot (PS1, NTSC-U SCUS-94900).

Sources:
- Level IDs: esplonky/c1 ``src/common.h`` (``LID_*``), consistent with goocdump ``goolstdlib.gooc`` level codes
  read as base-62 (``'0'-'9'``, ``'a'-'z'`` = 10-35, ``'A'-'Z'`` = 36-61).
- Map node order and key branches: goocdump ``Crash 1/NTSC-J/IsldC.gooc`` (``MapSetLevelParams``). The NTSC-J build
  swaps Sunset Vista (node 24 in J) and Slippery Climb (node 16 in J); this table uses the NTSC-U order.
- Colored gems: N. Sane Trilogy guides (The Escapist, Nintendo Life). Bits: goolstdlib NTSC-U aliases.
- Box totals and bonus rounds: the level table on crashbandicoot.fandom.com ("Crash Bandicoot (game)"), NTSC-U values
  (the NTSC-J entries are ignored). VERIFY: the client logs the real total whenever a level's gem is won.

Anything marked VERIFY still needs to be confirmed in an emulator; see docs/DESIGN.md and tools/VERIFY.md at the repository root.
"""
from dataclasses import dataclass, field
from enum import Enum


class Kind(Enum):
    LEVEL = "level"
    BOSS = "boss"
    FINAL_BOSS = "final_boss"
    SECRET = "secret"


class Bonus(Enum):
    """Bonus round kinds; three tokens of one kind in a level take Crash to that bonus round"""
    TAWNA = "Tawna"
    BRIO = "Brio"
    CORTEX = "Cortex"


BOX_MILESTONES: tuple[int, ...] = (25, 50, 75)
"""Percent of a level's boxes that are a check with box checks on. 100% is the gem."""
BOX_PERCENTS_BY_OPTION: dict[int, tuple[int, ...]] = {0: (), 1: (50,), 2: BOX_MILESTONES}
"""Box Checks option value (off, half, quarters) -> milestones"""
GEM_PATH_PERCENT = 75
"""From this milestone on, a level's colored gem path may be needed"""


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
    boxes: int = 0
    """Boxes in the level (NTSC-U), as counted by BOX_COUNT for the gem"""
    bonuses: tuple[Bonus, ...] = field(default=())
    """Bonus rounds reached from this level"""

    @property
    def is_boss(self) -> bool:
        return self.kind in (Kind.BOSS, Kind.FINAL_BOSS)

    @property
    def complete_location(self) -> str:
        return f"{self.name} - Defeated" if self.is_boss else f"{self.name} - Complete"

    @property
    def gem_location(self) -> str:
        return f"{self.name} - Gem"

    @staticmethod
    def box_location_name(level_name: str, percent: int) -> str:
        return f"{level_name} - {percent}% Boxes"

    def box_location(self, percent: int) -> str:
        return self.box_location_name(self.name, percent)

    def box_threshold(self, percent: int) -> int:
        """Boxes needed for a milestone (rounded up, at least 1)"""
        return max(1, -(-self.boxes * percent // 100))

    def bonus_location(self, bonus: Bonus) -> str:
        return f"{self.name} - {bonus.value} Bonus"

    def bonus_clear_location(self, bonus: Bonus) -> str:
        return f"{self.name} - {bonus.value} Bonus Cleared"

    @property
    def check_bonuses(self) -> tuple[Bonus, ...]:
        """Bonus rounds that are checks: the Cortex ones already award the keys"""
        return tuple(bonus for bonus in self.bonuses if bonus != Bonus.CORTEX)


LEVELS: tuple[Level, ...] = (
    # Island 1 (N. Sanity Island)
    Level("N. Sanity Beach", 0x09, 1, Kind.LEVEL, boxes=49),
    Level("Jungle Rollers", 0x0C, 2, Kind.LEVEL, gem_requires=(Gem.GREEN,), boxes=38, bonuses=(Bonus.TAWNA,)),
    Level("The Great Gate", 0x12, 3, Kind.LEVEL, gem_requires=(Gem.YELLOW,), boxes=26, bonuses=(Bonus.TAWNA,)),
    Level("Boulders", 0x0E, 4, Kind.LEVEL, boxes=16),
    Level("Upstream", 0x0F, 5, Kind.LEVEL, gem_requires=(Gem.ORANGE,), boxes=14, bonuses=(Bonus.TAWNA,)),
    Level("Papu Papu", 0x0A, 6, Kind.BOSS, gem=Gem.NONE),
    Level("Rolling Stones", 0x15, 7, Kind.LEVEL, gem_requires=(Gem.BLUE,), boxes=46, bonuses=(Bonus.TAWNA, Bonus.BRIO)),
    Level("Hog Wild", 0x11, 8, Kind.LEVEL, boxes=24),
    Level("Native Fortress", 0x1A, 9, Kind.LEVEL, gem_requires=(Gem.RED,), boxes=42, bonuses=(Bonus.TAWNA,)),
    # Island 2 (Wumpa Island)
    Level("Up the Creek", 0x18, 10, Kind.LEVEL, boxes=15, bonuses=(Bonus.TAWNA,)),
    Level("Ripper Roo", 0x17, 11, Kind.BOSS, gem=Gem.NONE),
    Level("The Lost City", 0x20, 12, Kind.LEVEL, gem=Gem.GREEN, boxes=31, bonuses=(Bonus.TAWNA, Bonus.BRIO)),
    Level("Temple Ruins", 0x1C, 13, Kind.LEVEL, boxes=67),
    Level("Road to Nowhere", 0x14, 14, Kind.LEVEL, gem_requires=(Gem.RED,), boxes=33, bonuses=(Bonus.TAWNA,)),
    Level("Boulder Dash", 0x13, 15, Kind.LEVEL, gem_requires=(Gem.PURPLE,), boxes=35),
    # VERIFY: node 16 on NTSC-U (node 24 on NTSC-J)
    Level("Sunset Vista", 0x23, 16, Kind.LEVEL, boxes=50, bonuses=(Bonus.TAWNA, Bonus.CORTEX)),
    Level("Koala Kong", 0x21, 17, Kind.BOSS, gem=Gem.NONE),
    # Island 3 (Cortex Island)
    Level("Heavy Machinery", 0x06, 18, Kind.LEVEL, boxes=33, bonuses=(Bonus.TAWNA, Bonus.BRIO)),
    Level("Cortex Power", 0x03, 19, Kind.LEVEL, gem_requires=(Gem.BLUE,), boxes=41),
    Level("Generator Room", 0x05, 20, Kind.LEVEL, gem=Gem.ORANGE, boxes=44, bonuses=(Bonus.TAWNA,)),
    Level("Toxic Waste", 0x07, 21, Kind.LEVEL, gem=Gem.BLUE, boxes=26, bonuses=(Bonus.TAWNA,)),
    Level("Pinstripe", 0x08, 22, Kind.BOSS, gem=Gem.NONE),
    Level("The High Road", 0x16, 23, Kind.LEVEL, boxes=18, bonuses=(Bonus.TAWNA,)),
    Level("Slippery Climb", 0x2E, 24, Kind.LEVEL, gem=Gem.RED, boxes=31, bonuses=(Bonus.BRIO,)),  # VERIFY: node 24 on NTSC-U
    # VERIFY: whether the Yellow path in Lights Out is needed for its gem (it leads to an alternate exit)
    Level("Lights Out", 0x28, 25, Kind.LEVEL, gem=Gem.PURPLE, boxes=15),
    Level("Jaws of Darkness", 0x1D, 26, Kind.LEVEL, gem_requires=(Gem.BLUE,), boxes=65, bonuses=(Bonus.TAWNA, Bonus.CORTEX)),
    Level("Castle Machinery", 0x37, 27, Kind.LEVEL, gem_requires=(Gem.GREEN,), boxes=24),
    Level("Dr. N. Brio", 0x1B, 28, Kind.BOSS, gem=Gem.NONE),
    Level("The Lab", 0x29, 29, Kind.LEVEL, gem=Gem.YELLOW, boxes=24, bonuses=(Bonus.TAWNA,)),
    Level("The Great Hall", 0x2C, 30, Kind.LEVEL, gem=Gem.NONE),  # VERIFY: assumed to be the level without a gem
    Level("Dr. N. Cortex", 0x1F, 31, Kind.FINAL_BOSS, gem=Gem.NONE),
    # Secret levels (map branches)
    Level("Whole Hog", 0x1E, 50, Kind.SECRET, boxes=24),
    Level("Fumbling in the Dark", 0x2A, 40, Kind.SECRET, boxes=18),
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

BOX_LEVELS: tuple[Level, ...] = tuple(level for level in LEVELS if level.boxes)


def box_percents(level: Level, box_checks: int, gem_checks: bool) -> tuple[int, ...]:
    """Box milestones that are checks for a level. Without gem checks the colored gems aren't items, so milestones
    that may need a gem path are left out of levels that have one."""
    if not level.boxes:
        return ()
    percents = BOX_PERCENTS_BY_OPTION[box_checks]
    if level.gem_requires and not gem_checks:
        percents = tuple(percent for percent in percents if percent < GEM_PATH_PERCENT)
    return percents

BONUS_LEVELS: tuple[Level, ...] = tuple(level for level in LEVELS if level.check_bonuses)
LIFE_COUNTS: tuple[int, ...] = tuple(range(5, 100))
"""Life counts that can be checks (the Life Count Checks option)"""

assert len(MAIN_LEVELS) == MAP_NODES
assert [level.vanilla_node for level in MAIN_LEVELS] == list(range(1, MAP_NODES + 1))
assert len(GEM_LEVELS) == 26, len(GEM_LEVELS)
assert {level.name for level in BOX_LEVELS} == {level.name for level in GEM_LEVELS}, "every gem level has boxes"
assert all(key.source in {level.name for level in LEVELS if Bonus.CORTEX in level.bonuses} for key in KEYS)
assert sorted(level.gem.value for level in GEM_LEVELS if level.gem.is_colored) == sorted(
    gem.value for gem in COLORED_GEMS
), "every colored gem must have exactly one source level"
