"""Filler items: which one to apply next, and the RAM writes that apply it. Pure logic, no I/O.

On the map the counters are the GOOL globals (LIFE_COUNT, HEALTH, FRUIT_COUNT), which the next level copies in. In a
level the live counters are fields of the Crash object (see ``ram.CRASH_PTR``), so Extra Life and Wumpa Fruit Bundle
are applied there right away. Aku Aku Mask stays on the map: the mask count lives in the Aku Aku object, whose state
machine reacts to it. No Lives Trap is handled by ``trap.py``, also on the map.

Applied counts are kept per item name in the server's data storage, so items applied out of order (a life in a level
while a mask waits for the map) are never applied twice.
"""
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from . import ram

EXTRA_LIFE = "Extra Life"
AKU_AKU_MASK = "Aku Aku Mask"
WUMPA_BUNDLE = "Wumpa Fruit Bundle"
BUNDLE_FRUIT = 10

LIVE_FILLER = frozenset({EXTRA_LIFE, WUMPA_BUNDLE})
"""Applied in a level as well as on the map"""


@dataclass
class Plan:
    name: str
    writes: dict[int, int] = field(default_factory=dict)
    guards: dict[int, int] = field(default_factory=dict)
    note: str = ""


def applied_counts(stored: Any, received: list[str]) -> Counter[str]:
    """Per-name applied counts from data storage. Version 0.2 stored one number, the count of fillers applied in the
    order received; it is converted by counting that many from the start of the list."""
    if isinstance(stored, dict):
        return Counter({str(name): int(count) for name, count in stored.items()})
    if isinstance(stored, int):
        return Counter(received[:stored])
    return Counter()


def pending(received: Iterable[str], applied: Counter[str]) -> list[str]:
    """Received fillers not applied yet, in the order received"""
    seen: Counter[str] = Counter()
    out: list[str] = []
    for name in received:
        seen[name] += 1
        if seen[name] > applied[name]:
            out.append(name)
    return out


def plan_on_map(name: str, snap: ram.Snapshot) -> Plan | None:
    if name == EXTRA_LIFE:
        return _single(name, ram.LIFE_COUNT, snap.lives, min(snap.lives + ram.UNIT, ram.MAX_LIVES))
    if name == AKU_AKU_MASK:
        return _single(name, ram.HEALTH, snap.health, min(snap.health + ram.UNIT, ram.MAX_HEALTH))
    if name == WUMPA_BUNDLE:
        return _single(name, ram.FRUIT_COUNT, snap.fruit, min(snap.fruit + BUNDLE_FRUIT * ram.UNIT, ram.MAX_FRUIT))
    return None


def plan_in_level(name: str, snap: ram.Snapshot) -> Plan | None:
    """Write into the Crash object. Every write is guarded by the pointer and the field's current value."""
    live = snap.live
    if live is None or name not in LIVE_FILLER:
        return None
    lives, fruit = live.lives, live.fruit
    if name == EXTRA_LIFE:
        lives = min(lives + ram.UNIT, ram.MAX_LIVES)
    else:
        fruit += BUNDLE_FRUIT * ram.UNIT
        if fruit >= 100 * ram.UNIT:  # as in the game: 100 fruit become a life
            fruit -= 100 * ram.UNIT
            lives = min(lives + ram.UNIT, ram.MAX_LIVES)
    plan = Plan(name, guards={ram.CRASH_PTR: snap.crash_ptr}, note="in level")
    if lives != live.lives:
        address = ram.field_address(snap.crash_ptr, ram.FIELD_LIVES)
        plan.writes[address], plan.guards[address] = lives, live.lives
    if fruit != live.fruit:
        address = ram.field_address(snap.crash_ptr, ram.FIELD_FRUIT)
        plan.writes[address], plan.guards[address] = fruit, live.fruit
    return plan


def _single(name: str, address: int, current: int, value: int) -> Plan:
    return Plan(name, writes={address: value}, guards={address: current}, note="on map")
