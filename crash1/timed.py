"""Timed traps: each one lasts ``trap_duration`` seconds of play in a level, then the game goes back to normal.
Pure logic, no I/O.

- No Lives Trap: lives are 0 while it lasts, so one death is a game over. Lives you have (and pick up meanwhile) are
  banked and given back when it ends, or on the map, where lives show normally until the next level. A game over
  ends the trap and the banked lives are lost, as with any game over.
- Upside Down Trap: the camera rolls 180 degrees (``hook``). The HUD stays upright and the controls are not flipped
  with the view.
- Reverse Controls Trap: left and right are swapped (``hook``).
- Button Swap Trap: jump is on Square/Circle and spin on X (``hook``).

Received traps wait in a queue and run one at a time, oldest first. A trap only starts while a level (or bonus round)
is being played, ``START_DELAY`` seconds into it, and the next one waits ``TRAP_GAP`` seconds after the previous ends.
All clocks only run in a level, so the map and loading screens freeze them, and effects are removed everywhere
else, so the map always plays normally. The state lives in the server's data storage, so a client restart picks the
queue back up, and the client takes the hooks out when no trap is running, also right after connecting.
"""
from dataclasses import dataclass, field, replace
from typing import Any

from . import hook, ram

NO_LIVES_TRAP = "No Lives Trap"
UPSIDE_DOWN_TRAP = "Upside Down Trap"
REVERSE_CONTROLS_TRAP = "Reverse Controls Trap"
BUTTON_SWAP_TRAP = "Button Swap Trap"
TIMED_TRAPS: tuple[str, ...] = (NO_LIVES_TRAP, UPSIDE_DOWN_TRAP, REVERSE_CONTROLS_TRAP, BUTTON_SWAP_TRAP)

START_DELAY = 3.0
"""Seconds of play in a level before a waiting trap starts"""
TRAP_GAP = 5.0
"""Seconds of play between one trap ending and the next starting"""


@dataclass(frozen=True)
class TimedTraps:
    queue: tuple[tuple[str, float], ...] = ()
    """Traps waiting to start, oldest first: (name, seconds)"""
    current: str | None = None
    """The trap running now"""
    left: float = 0.0
    """Seconds of play left for ``current``"""
    wait: float = 0.0
    """Seconds of play before the next trap may start"""
    banked: int = 0
    """Lives (<< 8) held back by the No Lives Trap"""

    def active(self, name: str) -> bool:
        return self.current == name

    @property
    def busy(self) -> bool:
        """A trap runs or waits"""
        return self.current is not None or bool(self.queue)

    def add(self, name: str, seconds: float) -> "TimedTraps":
        return replace(self, queue=(*self.queue, (name, float(seconds))))

    def to_json(self) -> dict[str, Any]:
        return {"queue": [[name, round(seconds, 1)] for name, seconds in self.queue],
                "current": self.current, "left": round(self.left, 1), "wait": round(self.wait, 1),
                "banked": self.banked}

    @classmethod
    def from_json(cls, data: Any) -> "TimedTraps":
        if not isinstance(data, dict):
            return cls()
        queue = tuple((str(entry[0]), float(entry[1])) for entry in data.get("queue") or ()
                      if isinstance(entry, (list, tuple)) and len(entry) == 2 and entry[0] in TIMED_TRAPS
                      and float(entry[1]) > 0)
        current = data.get("current")
        left = float(data.get("left", 0))
        if current not in TIMED_TRAPS or left <= 0:
            current, left = None, 0.0
        return cls(queue, current, left, max(float(data.get("wait", 0)), 0.0), int(data.get("banked", 0)))


def in_level(snap: ram.Snapshot) -> bool:
    """A level or bonus round is being played (not the map, the end screen or a transition)"""
    return snap.gamestate == ram.GAMESTATE_PLAYING and snap.level not in (ram.LID_MAP, ram.LID_LEVEL_END)


def tick(state: TimedTraps, snap: ram.Snapshot, seconds: float) -> tuple[TimedTraps, list[str], list[str]]:
    """Run the clocks while a level is played. Returns the new state, the trap that just ended and the one that
    just started (each list holds at most one name)."""
    if snap.gamestate == ram.GAMESTATE_GAME_OVER and state.active(NO_LIVES_TRAP):
        return replace(state, current=None, left=0.0, wait=TRAP_GAP, banked=0), [NO_LIVES_TRAP], []
    if not in_level(snap):
        if state.current is None and state.queue and state.wait < START_DELAY:
            state = replace(state, wait=START_DELAY)  # a level must be underway before the next trap
        return state, [], []
    if seconds <= 0:
        return state, [], []
    if state.current is not None:
        left = state.left - seconds
        if left > 0:
            return replace(state, left=left), [], []
        return replace(state, current=None, left=0.0, wait=TRAP_GAP), [state.current], []
    if state.wait > 0:
        return replace(state, wait=max(state.wait - seconds, 0.0)), [], []
    if state.queue:
        (name, duration), *rest = state.queue
        return replace(state, queue=tuple(rest), current=name, left=duration), [], [name]
    return state, [], []


@dataclass
class Plan:
    state: TimedTraps
    writes: dict[int, int] = field(default_factory=dict)
    guards: dict[int, int] = field(default_factory=dict)
    flags: int = 0
    """Controller hook flags wanted now"""
    notes: list[str] = field(default_factory=list)


def plan(state: TimedTraps, snap: ram.Snapshot) -> Plan:
    """RAM writes that make the game match the active traps. The new state only holds if the writes succeed."""
    out = Plan(state)
    playing = in_level(snap)

    if playing:
        out.flags = ((hook.FLAG_REVERSE_X if state.active(REVERSE_CONTROLS_TRAP) else 0)
                     | (hook.FLAG_SWAP_BUTTONS if state.active(BUTTON_SWAP_TRAP) else 0)
                     | (hook.FLAG_UPSIDE_DOWN if state.active(UPSIDE_DOWN_TRAP) else 0))

    # No Lives: bank whatever the Crash object holds while active; give it back when over or on the map
    live = snap.live
    if live is not None:
        address = ram.field_address(snap.crash_ptr, ram.FIELD_LIVES)
        if state.active(NO_LIVES_TRAP) and live.lives > 0:
            out.writes[address], out.guards[address] = 0, live.lives
            out.guards[ram.CRASH_PTR] = snap.crash_ptr
            out.state = replace(state, banked=min(state.banked + live.lives, ram.MAX_LIVES))
        elif not state.active(NO_LIVES_TRAP) and state.banked:
            out.writes[address], out.guards[address] = min(live.lives + state.banked, ram.MAX_LIVES), live.lives
            out.guards[ram.CRASH_PTR] = snap.crash_ptr
            out.state = replace(state, banked=0)
            out.notes.append(f"No Lives Trap over: {state.banked // ram.UNIT} lives back.")
    elif snap.on_map and snap.gamestate == ram.GAMESTATE_MAP and state.banked:
        out.writes[ram.LIFE_COUNT] = min(snap.lives + state.banked, ram.MAX_LIVES)
        out.guards[ram.LIFE_COUNT] = snap.lives
        out.state = replace(state, banked=0)
    return out
