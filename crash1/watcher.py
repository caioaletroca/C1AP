"""Game-state logic for the BizHawk client, kept free of I/O so it can be unit tested.

Each poll the client parses a ``Snapshot`` and calls ``Watcher.step``. The watcher returns ``Actions``: locations to
send, RAM words to write, and whether the goal was reached or Crash died. The client performs the I/O.

Gems belong to map nodes, not levels (verified in BizHawk): finishing a level with every box gives the gem of the node
it was entered from, ITEMPOOL1 bit = node (1-31), ITEMPOOL2 bit = node - 32 (secret nodes 40, 50). Colored gems are the
gems of nodes 12, 20, 21, 24, 25, 29.

Ownership rules (see docs/DESIGN.md §9):
- Colored gem bits (when gem checks are on) and key bits belong to the client: they mirror the received items.
- While Crash is in a level whose gem location is unchecked and whose node awards a colored gem, that bit is forced to
  0; the game setting it there means the player collected the gem. Keys work the same way with their source level.
- Clear gem bits are never written. The node's clear gem bit appearing while in a level is that level's gem check.
- The map's reachable nodes mirror the Map Progress items.

Tier 1 checks (v0.3):
- Box milestones: BOX_COUNT (<< 8) reaching a share of the played level's box total, while in that level.
- Bonus rounds: entering a Tawna or Brio bonus round from a level. The kind comes from the token counts in the Crash
  object (the one at 3), else from the bonus level's ID.
- Life counts: the current lives (the Crash object's in a level, the global on the map) reaching a count.
The Crash object's fields are only trusted when they look like counters on two polls in a row with the same pointer.
``Actions.notes`` carries what the client should log for verification (box totals, bonus kinds).
"""
from collections import Counter
from collections.abc import Collection
from dataclasses import dataclass, field

from . import ram
from .data import (
    COLORED_GEMS, FINAL_BOSS, KEYS, LEVEL_BY_LID, LEVEL_BY_NAME, MAP_NODES, Bonus, Gem, Level, box_percents,
)
from .items import CLEAR_GEM, MAP_PROGRESS
from .locations import life_count_location, location_name_to_id
from .options import Goal


@dataclass(frozen=True)
class SlotInfo:
    level_order: tuple[int, ...]
    """Level ID on each map node; index 0 is node 1"""
    starting_nodes: int
    gem_checks: bool
    goal: int
    box_checks: int = 0
    bonus_round_checks: bool = False
    life_count_checks: tuple[int, ...] = ()

    @classmethod
    def from_slot_data(cls, slot_data: dict) -> "SlotInfo":
        return cls(
            level_order=tuple(slot_data["level_order"]),
            starting_nodes=int(slot_data["starting_nodes"]),
            gem_checks=bool(slot_data["gem_checks"]),
            goal=int(slot_data["goal"]),
            box_checks=int(slot_data.get("box_checks", 0)),
            bonus_round_checks=bool(slot_data.get("bonus_round_checks", False)),
            life_count_checks=tuple(int(lives) for lives in slot_data.get("life_count_checks", ())),
        )


@dataclass(frozen=True)
class OwnedBit:
    """An item-pool bit that mirrors a received item"""
    pool: int
    """1 or 2"""
    bit: int
    item: str


@dataclass(frozen=True)
class Mask:
    """An owned bit held at 0 so the game can award it; the game awarding it checks ``location``"""
    pool: int
    bit: int
    location: int


def owned_bits(gem_checks: bool) -> list[OwnedBit]:
    bits = [OwnedBit(2, key.pool2_bit, key.item_name) for key in KEYS]
    if gem_checks:
        bits += [OwnedBit(1, ram.COLORED_GEM_BITS[gem.value], gem.item_name) for gem in COLORED_GEMS]
    return bits


@dataclass
class Actions:
    locations: set[int] = field(default_factory=set)
    writes: dict[int, int] = field(default_factory=dict)
    """address -> 32-bit value"""
    guards: dict[int, int] = field(default_factory=dict)
    """address -> value that must still be there for ``writes`` to apply"""
    goal: bool = False
    died: bool = False
    can_apply_filler: bool = False
    """On the map: every filler and trap can be applied (to the globals)"""
    can_apply_live_filler: bool = False
    """In a level with a trusted Crash object: Extra Life and Wumpa Fruit Bundle can be applied to it"""
    notes: list[str] = field(default_factory=list)
    """Lines for the client log (verification data)"""


class Watcher:
    def __init__(self, slot: SlotInfo) -> None:
        self.slot = slot
        self.owned = owned_bits(slot.gem_checks)
        self._owned_slots = {(owned.pool, owned.bit) for owned in self.owned}
        self.vanilla_lid_by_node = {level.vanilla_node: level.lid for level in LEVEL_BY_LID.values()}
        self.previous: ram.Snapshot | None = None
        self.level: Level | None = None
        """Level Crash is in (bonus rounds and the end-of-level screen count as the level they came from)"""
        self.masked: list[Mask] = []
        """Owned bits held at 0 after the last poll"""
        self.tokens: ram.CrashFields | None = None
        """Last trusted Crash fields in the tracked level (token counts for the bonus round kind)"""
        self.bonus_seen = False
        """A bonus round was entered during this level visit"""
        self.box_total_noted = False

    def step(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int]) -> Actions:
        actions = Actions()
        previous, self.previous = self.previous, snap

        if snap.on_title:
            self.level = None
            self.masked = []
            return actions

        self._track_level(snap)
        live = self._trusted_live(snap, previous)
        self._detect_tier1(snap, live, actions)  # before _detect_checks, which forgets the level on the map
        self._detect_checks(snap, previous, checked, actions)
        self._sync_pools(snap, received, checked, actions)
        if snap.on_map:
            self._sync_map(snap, received, actions)
        self._redirect_level(snap, actions)

        # Every respawn after a death bumps RESPAWN_COUNT; it drops back to 0 when a level starts.
        if (previous is not None and not previous.on_title and snap.level == previous.level
                and snap.respawn_count > previous.respawn_count):
            actions.died = True

        if snap.level == ram.LID_GAME_WIN and self._goal_items_met(received):
            actions.goal = True

        # Lives, masks and fruit are copied out of the level only when it ends, so filler is applied on the map
        # and carries into the next level.
        actions.can_apply_filler = snap.on_map and snap.gamestate == ram.GAMESTATE_MAP
        actions.can_apply_live_filler = live is not None
        return actions

    def _trusted_live(self, snap: ram.Snapshot, previous: ram.Snapshot | None) -> ram.CrashFields | None:
        """The Crash object's fields, when they looked like counters on this poll and the last with the same pointer"""
        live = snap.live
        if live is None or previous is None or previous.live is None or previous.crash_ptr != snap.crash_ptr:
            return None
        return live

    def _detect_tier1(self, snap: ram.Snapshot, live: ram.CrashFields | None, actions: Actions) -> None:
        level = self.level
        in_own_level = level is not None and snap.level == level.lid and snap.gamestate == ram.GAMESTATE_PLAYING

        if in_own_level and live is not None:
            self.tokens = live

        # Box milestones
        if in_own_level:
            boxes = snap.box_count // ram.UNIT
            for percent in box_percents(level, self.slot.box_checks, self.slot.gem_checks):
                if boxes >= level.box_threshold(percent):
                    actions.locations.add(location_name_to_id[level.box_location(percent)])

        # Box total, for verification: the count when the level is won (all boxes if the gem follows)
        if (level is not None and level.boxes and not self.box_total_noted
                and snap.gamestate == ram.GAMESTATE_LEVEL_WON and snap.level == level.lid):
            self.box_total_noted = True
            actions.notes.append(f"Boxes: {level.name} won with BOX_COUNT {snap.box_count // ram.UNIT} "
                                 f"(table total {level.boxes}; equal when the gem is won)")

        # Bonus rounds
        if (level is not None and snap.level in ram.BONUS_LIDS and snap.gamestate == ram.GAMESTATE_PLAYING
                and not self.bonus_seen):
            self.bonus_seen = True
            kind = self._bonus_kind(snap.level)
            tokens = self.tokens
            if tokens is None:
                token_text = "unknown"
            else:
                token_text = (f"Tawna {tokens.tawna // ram.UNIT}, Brio {tokens.brio // ram.UNIT}, "
                              f"Cortex {tokens.cortex // ram.UNIT}")
            actions.notes.append(f"Bonus round from {level.name}: level ID 0x{snap.level:02X}, tokens {token_text}, "
                                 f"counted as {kind.value if kind else 'unknown'}")
            if self.slot.bonus_round_checks and kind is not None:
                if kind in level.check_bonuses:
                    actions.locations.add(location_name_to_id[level.bonus_location(kind)])
                elif kind != Bonus.CORTEX:
                    actions.notes.append(f"Bonus round: {level.name} has no {kind.value} bonus in the table")

        # Life counts
        lives = live.lives if live is not None else (snap.lives if snap.on_map and snap.gamestate == ram.GAMESTATE_MAP
                                                      else None)
        if lives is not None:
            for count in self.slot.life_count_checks:
                if lives >= count * ram.UNIT:
                    actions.locations.add(location_name_to_id[life_count_location(count)])

    def _bonus_kind(self, bonus_lid: int) -> Bonus | None:
        tokens = self.tokens
        if tokens is not None:
            full = [kind for kind, count in ((Bonus.TAWNA, tokens.tawna), (Bonus.BRIO, tokens.brio),
                                             (Bonus.CORTEX, tokens.cortex)) if count >= 3 * ram.UNIT]
            if len(full) == 1:
                return full[0]
        if bonus_lid == ram.LID_BONUS_BRIO:
            return Bonus.BRIO
        if bonus_lid == ram.LID_BONUS_CORTEX:
            return Bonus.CORTEX
        if bonus_lid == ram.LID_BONUS_GENERIC:
            return None
        return Bonus.TAWNA

    # Level tracking

    def _track_level(self, snap: ram.Snapshot) -> None:
        if snap.level in LEVEL_BY_LID and snap.level != ram.LID_MAP:
            level = LEVEL_BY_LID[snap.level]
            if level is not self.level:
                self.tokens = None
                self.bonus_seen = False
                self.box_total_noted = False
            self.level = level

    def _detect_checks(self, snap: ram.Snapshot, previous: ram.Snapshot | None, checked: Collection[int],
                       actions: Actions) -> None:
        level = self.level
        if level is None:
            return

        if previous is not None and not previous.on_title:
            # Colored gems and keys: held at 0 while their location is unchecked, so a 0 -> 1 change on a bit that
            # was already masked last poll means the player collected it. (On the first poll in the level the bit may
            # still hold the received item; it is masked, not counted.)
            for mask in self.masked:
                bit = 1 << mask.bit
                if mask.location not in checked and not _pool(previous, mask.pool) & bit and _pool(snap, mask.pool) & bit:
                    actions.locations.add(mask.location)

            # Clear gems: the entry node's gem bit appearing.
            slot = ram.gem_slot(snap.current_node)
            if self.slot.gem_checks and level.gem != Gem.NONE and slot is not None and slot not in self._owned_slots:
                pool, bit = slot
                if not _pool(previous, pool) & (1 << bit) and _pool(snap, pool) & (1 << bit):
                    actions.locations.add(location_name_to_id[level.gem_location])

        # Completion: a normal exit to the map (0x300) or the gem screen being queued (0x500) after a tracked level.
        # 0x300 shows with the level's own ID for only 1-2 frames, then with the map's for ~400, so the map ID counts
        # too (``level`` is cleared once the map is reached, so it fires once). A game over (0x200) and a quit (0x400)
        # use neither state; bonus rounds don't count.
        if (snap.gamestate in (ram.GAMESTATE_LEVEL_WON, ram.GAMESTATE_EXIT_TO_MAP)
                and snap.level not in ram.BONUS_LIDS and level is not FINAL_BOSS):
            actions.locations.add(location_name_to_id[level.complete_location])

        if snap.on_map:
            self.level = None

    # Writes

    def _desired_pools(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int]) -> tuple[int, int]:
        pools = {1: snap.pool1, 2: snap.pool2}
        self.masked = self._masks(snap, checked)
        masked_slots = {(mask.pool, mask.bit) for mask in self.masked}
        for owned in self.owned:
            if received[owned.item] > 0 and (owned.pool, owned.bit) not in masked_slots:
                pools[owned.pool] |= 1 << owned.bit
            else:
                pools[owned.pool] &= ~(1 << owned.bit)
        return pools[1], pools[2]

    def _masks(self, snap: ram.Snapshot, checked: Collection[int]) -> list[Mask]:
        level = self.level
        if level is None:
            return []
        masks = [
            Mask(2, key.pool2_bit, location_name_to_id[key.location])
            for key in KEYS
            if key.source == level.name and location_name_to_id[key.location] not in checked
        ]
        if self.slot.gem_checks and level.gem != Gem.NONE:
            slot = ram.gem_slot(snap.current_node)
            location = location_name_to_id[level.gem_location]
            if slot in self._owned_slots and location not in checked:
                masks.append(Mask(slot[0], slot[1], location))
        return masks

    def _sync_pools(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int],
                    actions: Actions) -> None:
        pool1, pool2 = self._desired_pools(snap, received, set(checked) | actions.locations)
        if pool1 != snap.pool1:
            actions.writes[ram.ITEM_POOL1] = pool1
            actions.guards[ram.ITEM_POOL1] = snap.pool1
        if pool2 != snap.pool2:
            actions.writes[ram.ITEM_POOL2] = pool2
            actions.guards[ram.ITEM_POOL2] = snap.pool2

    def open_nodes(self, received: Counter[str]) -> int:
        return min(MAP_NODES, self.slot.starting_nodes + received[MAP_PROGRESS])

    def _sync_map(self, snap: ram.Snapshot, received: Counter[str], actions: Actions) -> None:
        nodes = self.open_nodes(received)
        if snap.levels_unlocked != nodes:
            actions.writes[ram.LEVELS_UNLOCKED] = nodes
            actions.writes[ram.MAP_LEVEL_LINKS] = (1 << (nodes + 1)) - 1
        if ram.ITEM_POOL2 in actions.writes:
            actions.writes[ram.MAP_KEY_LINKS] = actions.writes[ram.ITEM_POOL2]

    def _redirect_level(self, snap: ram.Snapshot, actions: Actions) -> None:
        """Level shuffle: make the map's node load the shuffled level instead of its vanilla one.

        Writing NEXT_LID makes the engine load that level (verified in BizHawk). The map's own request only sits in
        NEXT_LID for ~3 frames, so it is usually missed; then the vanilla level is already loading and asking for the
        shuffled one replaces it.
        """
        node = snap.current_node
        if not 1 <= node <= MAP_NODES:
            return  # secret branches (40, 50) are not shuffled
        vanilla = self.vanilla_lid_by_node[node]
        target = self.slot.level_order[node - 1]
        if target == vanilla:
            return
        if snap.next_lid == vanilla:
            # Caught the map's request: swap it.
            actions.writes[ram.NEXT_LID] = target
            actions.guards[ram.NEXT_LID] = vanilla
        elif snap.level == vanilla and snap.next_lid == ram.NO_LEVEL:
            # Missed it: the vanilla level is loading or running. Load the right one.
            actions.writes[ram.NEXT_LID] = target
            actions.guards[ram.NEXT_LID] = ram.NO_LEVEL

    def _goal_items_met(self, received: Counter[str]) -> bool:
        if self.slot.goal != Goal.option_all_gems:
            return True
        clear_gems = sum(1 for level in LEVEL_BY_NAME.values() if level.gem == Gem.CLEAR)
        return received[CLEAR_GEM] >= clear_gems and all(received[gem.item_name] for gem in COLORED_GEMS)


def _pool(snap: ram.Snapshot, pool: int) -> int:
    return snap.pool1 if pool == 1 else snap.pool2
