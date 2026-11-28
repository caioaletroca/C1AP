"""RAM map for Crash Bandicoot (PS1, NTSC-U SCUS-94900).

Addresses are PS1 virtual addresses (0x80xxxxxx); BizHawk's "MainRAM" domain is offset by 0x80000000.
Comments say OK (confirmed in BizHawk, see tools/VERIFY.md), BAD (wrong) or VERIFY.
Everything marked VERIFY comes from the decompilation / GOOL dumps and still needs to be confirmed in BizHawk
(see tools/VERIFY.md). Values are little-endian 32-bit words unless noted.
"""
import struct
from dataclasses import dataclass, replace

DOMAIN = "MainRAM"
RAM_BASE = 0x80000000


def offset(address: int) -> int:
    """Convert a PS1 virtual address into a MainRAM offset."""
    return address - RAM_BASE


# GOOL globals block
GLOBALS_START = 0x8006188C
LEVEL = 0x8006188C             # OK: current level ID << 8 (fixed point); the client uses CURRENT_LID instead
RESPAWN_COUNT = 0x800618A0     # OK: +0x100 on every respawn after a death (checkpoints too), 0 at level start
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
BOX_COUNT = 0x80061984         # OK: boxes broken in this level << 8 (BoxsC adds 0x100 per box; the gem needs all)
DEATH_COUNT = 0x80061A3C       # BAD for death link: deaths since the last checkpoint (Aku Aku pity mask)
GLOBALS_END = DEATH_COUNT + 4
GLOBALS_SIZE = GLOBALS_END - GLOBALS_START

# Engine (not GOOL) state
LID_BLOCK = 0x80056710
CURRENT_LID = 0x80056710       # OK: plain level ID
NEXT_LID = 0x80056714          # OK: -1 when idle; holds the level ID for ~3 frames during a load
LID_BLOCK_SIZE = 8

# The Crash (player) GOOL object. In a level its own fields hold the counters; WillC copies them from LIFE_COUNT,
# FRUIT_COUNT and the token counts when it spawns and back when the level ends (kdecomp src/gool/WillC.gool, state_0
# and state_34). Writing the globals mid-level is overwritten at the end, so mid-level filler goes here.
CRASH_PTR = 0x800566B4         # OK (0 for a moment while a bonus round loads): `crash` (wc1 src/gool.c, .sbss), set to `player` when a level starts.
# BAD: 0x80056480 (kdecomp docs/names.md calls it `crash`) is `in_consts`, a GOOL buffer descriptor: BizHawk round 8
# read 0x1F800040 there, a scratchpad address.
PLAYER_PTR = 0x80060DB4        # OK: `player` (wc1), the allocated Crash object; logged as a cross-check
OBJ_FIELDS = 0x160             # GOOL object register 0x40 (`field-0`) is at object + 0x60 + 0x40 * 4
OBJ_FIELD_COUNT = 9
FIELD_FRUIT = 0                # OK: fruit << 8; at 100 the game subtracts 100 and adds a life (WillC loc_04F8)
FIELD_LIVES = 1                # OK: lives << 8, capped at 99 (WillC: 25344)
FIELD_CORTEX = 6               # OK (Tawna and Brio seen): token counts << 8 (loaded from CORTEX/BRIO/TAWNA_COUNT at spawn)
FIELD_BRIO = 7
FIELD_TAWNA = 8
RAM_SIZE = 0x200000

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
# goolstdlib level codes (base 62): BonusTawna1 'A', BonusBrio 'B', Bonus 'C', BonusTawna2 'P', BonusCortex 'Q'
LID_BONUS_BRIO = 0x25          # OK (Rolling Stones). Tawna: 0x24 (Jungle Rollers), 0x33 (Rolling Stones)
LID_BONUS_CORTEX = 0x34        # OK (Sunset Vista)
LID_BONUS_GENERIC = 0x26       # VERIFY: which kind is unknown; the client uses the token counts

UNIT = 0x100                   # OK: lives, masks and fruit are stored << 8
MAX_HEALTH = 2 * UNIT          # OK (second mask from the multiworld seen): two masks; a third gives temporary invincibility
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
class CrashFields:
    """Counters inside the Crash object while a level runs (all << 8)"""
    fruit: int
    lives: int
    cortex: int
    brio: int
    tawna: int

    @property
    def plausible(self) -> bool:
        """Guards against a stale pointer: the counters must look like counters"""
        return (self.lives % UNIT == 0 and 0 <= self.lives <= MAX_LIVES
                and self.fruit % UNIT == 0 and 0 <= self.fruit < 100 * UNIT
                and all(0 <= token <= 3 * UNIT for token in (self.cortex, self.brio, self.tawna)))


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
    respawn_count: int
    next_lid: int
    box_count: int = 0
    crash_ptr: int = 0
    player_ptr: int = 0
    """Logged only, to cross-check CRASH_PTR"""
    crash: CrashFields | None = None
    """Read only when ``crash_readable``; None otherwise"""

    @property
    def on_map(self) -> bool:
        return self.level == LID_MAP and self.gamestate != GAMESTATE_TITLE

    @property
    def on_title(self) -> bool:
        return self.gamestate == GAMESTATE_TITLE

    @property
    def crash_readable(self) -> bool:
        """In a level (or bonus round) with a pointer that can be followed"""
        return (self.gamestate == GAMESTATE_PLAYING and self.level not in (LID_MAP, LID_LEVEL_END)
                and RAM_BASE <= self.crash_ptr < RAM_BASE + RAM_SIZE - 0x200)

    @property
    def live(self) -> CrashFields | None:
        """The Crash object's counters, when they are the live ones"""
        if self.crash_readable and self.crash is not None and self.crash.plausible:
            return self.crash
        return None

    @property
    def current_lives(self) -> int | None:
        """Lives << 8 right now: the Crash object's in a level, the global on the map"""
        if self.live is not None:
            return self.live.lives
        if self.on_map and self.gamestate == GAMESTATE_MAP:
            return self.lives
        return None


def field_address(crash_ptr: int, field: int) -> int:
    return crash_ptr + OBJ_FIELDS + 4 * field



def read_requests() -> list[tuple[int, int, str]]:
    return [
        (offset(GLOBALS_START), GLOBALS_SIZE, DOMAIN),
        (offset(LID_BLOCK), LID_BLOCK_SIZE, DOMAIN),
        (offset(CRASH_PTR), 4, DOMAIN),
        (offset(PLAYER_PTR), 4, DOMAIN),
    ]


def crash_request(crash_ptr: int) -> tuple[int, int, str]:
    return offset(field_address(crash_ptr, 0)), OBJ_FIELD_COUNT * 4, DOMAIN


def _word(block: bytes, block_start: int, address: int) -> int:
    return struct.unpack_from("<I", block, address - block_start)[0]


def parse(globals_block: bytes, lid_block: bytes, crash_ptr_block: bytes = bytes(4),
          player_ptr_block: bytes = bytes(4)) -> Snapshot:
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
        respawn_count=g(RESPAWN_COUNT),
        next_lid=_word(lid_block, LID_BLOCK, NEXT_LID),
        box_count=g(BOX_COUNT),
        crash_ptr=struct.unpack_from("<I", crash_ptr_block)[0],
        player_ptr=struct.unpack_from("<I", player_ptr_block)[0],
    )


def with_crash(snap: Snapshot, fields_block: bytes) -> Snapshot:
    words = struct.unpack_from(f"<{OBJ_FIELD_COUNT}I", fields_block)
    return replace(snap, crash=CrashFields(
        fruit=words[FIELD_FRUIT], lives=words[FIELD_LIVES],
        cortex=words[FIELD_CORTEX], brio=words[FIELD_BRIO], tawna=words[FIELD_TAWNA],
    ))


def word_bytes(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)
