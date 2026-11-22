"""RAM map for Crash Bandicoot (PS1, NTSC-U SCUS-94900).

Addresses are PS1 virtual addresses (0x80xxxxxx); BizHawk's "MainRAM" domain is offset by 0x80000000.
Comments say OK (confirmed in BizHawk, see tools/VERIFY.md), BAD (wrong) or VERIFY.
Everything marked VERIFY comes from the decompilation / GOOL dumps and still needs to be confirmed in BizHawk
(see tools/VERIFY.md). Values are little-endian 32-bit words unless noted.
"""
import struct
from dataclasses import dataclass

DOMAIN = "MainRAM"
RAM_BASE = 0x80000000


def offset(address: int) -> int:
    """Convert a PS1 virtual address into a MainRAM offset."""
    return address - RAM_BASE


# GOOL globals block
GLOBALS_START = 0x8006188C
LEVEL = 0x8006188C             # OK: current level ID << 8 (fixed point); the client uses CURRENT_LID instead
GAMESTATE = 0x800618D0         # OK
CURRENT_NODE = 0x800618DC      # OK: (1 after entering node 1): CURRENTLEVEL, the map node last entered (IslandProgress)
LIFE_COUNT = 0x800618EC        # OK: lives << 8; only synced from the level at its end
HEALTH = 0x800618F0            # OK: Aku Aku masks << 8; synced at level end
FRUIT_COUNT = 0x800618F4       # OK: fruit << 8; synced at level end
LEVEL_COUNT = 0x80061944       # VERIFY
LEVELS_UNLOCKED = 0x80061948   # OK: 1 on a new game, +1 when the furthest level is won; writes VERIFY
ITEM_POOL1 = 0x80061988        # OK: (N. Sanity Beach gem = bit 1)
ITEM_POOL2 = 0x800619AC        # VERIFY
MAP_LEVEL_LINKS = 0x800619B0   # OK: the map recomputes (1 << (LEVELS_UNLOCKED + 1)) - 1 on entry
MAP_KEY_LINKS = 0x800619B8     # VERIFY: the map copies ITEM_POOL2 here on entry
DEATH_COUNT = 0x80061A3C       # BAD: << 8, missed most deaths, resets on exit; death link needs in-level lives
GLOBALS_END = DEATH_COUNT + 4
GLOBALS_SIZE = GLOBALS_END - GLOBALS_START

# Engine (not GOOL) state
LID_BLOCK = 0x80056710
CURRENT_LID = 0x80056710       # OK: plain level ID
NEXT_LID = 0x80056714          # OK: -1 when idle; holds the level ID for ~3 frames during a load
LID_BLOCK_SIZE = 8

# Values
GAMESTATE_MAP = 0x000          # OK: standing on the map
GAMESTATE_PLAYING = 0x100      # OK: in a level (also the end-of-level screen)
GAMESTATE_GAME_OVER = 0x200    # OK: out of lives; straight to the map, then continue reloads the save
GAMESTATE_EXIT_TO_MAP = 0x300  # OK: leaving a won level for the map (directly, or from the end screen)
GAMESTATE_QUIT_TO_MAP = 0x400  # OK: quit from the pause menu (lives/fruit still sync); never a completion
GAMESTATE_LEVEL_WON = 0x500    # OK: level won AND a gem screen follows (no gem: straight to 0x300)
GAMESTATE_TITLE = 0x600        # VERIFY

LID_MAP = 0x19                 # shared with the title screen
NO_LEVEL = 0xFFFFFFFF          # NEXT_LID when nothing is loading
LID_GAME_WIN = 0x39
LID_LEVEL_END = 0x2D
BONUS_LIDS = frozenset({0x24, 0x25, 0x26, 0x33, 0x34})
"""Bonus rounds return to the level they were entered from"""

UNIT = 0x100                   # OK: lives, masks and fruit are stored << 8
MAX_HEALTH = 2 * UNIT          # VERIFY: two masks; a third gives temporary invincibility
MAX_FRUIT = 99 * UNIT
MAX_LIVES = 99 * UNIT

# Item bits
POOL1_GEM_BITS = frozenset({1, 2, 3, 4, 5, 7, 8, 9, 10, 12, 13, 14, 15, 16, 18, 19, 20, 21, 23, 24, 25, 26, 27, 29})
POOL2_GEM_BITS = frozenset({8, 18})
COLORED_GEM_BITS: dict[str, int] = {  # ITEM_POOL1 bit per colored gem = its vanilla node
    "Green": 12,   # OK: poke shows the Jungle Rollers path
    "Red": 24,
    "Orange": 20,
    "Blue": 21,    # OK: node 21 (Toxic Waste); gem bits are node numbers
    "Purple": 25,
    "Yellow": 29,  # OK: poke shows The Great Gate path
}


def gem_slot(node: int) -> "tuple[int, int] | None":
    """(pool, bit) of the gem a map node awards when its level is finished with every box.

    OK: verified in BizHawk. The gem goes by the node a level was entered from: N. Sanity Beach on node 1 gave bit 1,
    Toxic Waste on node 4 gave bit 4, and N. Sanity Beach on node 6 (Papu Papu's, no gem in vanilla) gave bit 6. So every
    node has a slot; vanilla's POOL1_GEM_BITS only lacks the boss nodes and 30 because those levels have no boxes.
    Node 30 is assumed to behave like node 6 (VERIFY). The secret nodes 40 and 50 map to ITEM_POOL2 bits 8 and 18.
    """
    if 1 <= node <= 30:
        return 1, node
    if node >= 32 and node - 32 in POOL2_GEM_BITS:
        return 2, node - 32
    return None


def mask(bits: "frozenset[int] | set[int] | list[int]") -> int:
    value = 0
    for bit in bits:
        value |= 1 << bit
    return value


POOL1_CLEAR_GEM_MASK = mask(POOL1_GEM_BITS) & ~mask(list(COLORED_GEM_BITS.values()))
POOL2_CLEAR_GEM_MASK = mask(POOL2_GEM_BITS)


@dataclass(frozen=True)
class Snapshot:
    level: int
    gamestate: int
    current_node: int
    lives: int
    health: int
    fruit: int
    levels_unlocked: int
    pool1: int
    pool2: int
    death_count: int
    next_lid: int

    @property
    def on_map(self) -> bool:
        return self.level == LID_MAP and self.gamestate != GAMESTATE_TITLE

    @property
    def on_title(self) -> bool:
        return self.gamestate == GAMESTATE_TITLE



def read_requests() -> list[tuple[int, int, str]]:
    return [
        (offset(GLOBALS_START), GLOBALS_SIZE, DOMAIN),
        (offset(LID_BLOCK), LID_BLOCK_SIZE, DOMAIN),
    ]


def _word(block: bytes, block_start: int, address: int) -> int:
    return struct.unpack_from("<I", block, address - block_start)[0]


def parse(globals_block: bytes, lid_block: bytes) -> Snapshot:
    def g(address: int) -> int:
        return _word(globals_block, GLOBALS_START, address)

    return Snapshot(
        level=_word(lid_block, LID_BLOCK, CURRENT_LID),
        gamestate=g(GAMESTATE),
        current_node=g(CURRENT_NODE),
        lives=g(LIFE_COUNT),
        health=g(HEALTH),
        fruit=g(FRUIT_COUNT),
        levels_unlocked=g(LEVELS_UNLOCKED),
        pool1=g(ITEM_POOL1),
        pool2=g(ITEM_POOL2),
        death_count=g(DEATH_COUNT),
        next_lid=_word(lid_block, LID_BLOCK, NEXT_LID),
    )


def word_bytes(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)
