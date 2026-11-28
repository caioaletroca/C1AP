"""Timed traps: each one lasts ``trap_duration`` seconds of play in a level, then the game goes back to normal.
Pure logic, no I/O.

- No Lives Trap: lives are 0 while it lasts, so one death is a game over. Lives you have (and pick up meanwhile) are
  banked and given back when it ends, or on the map, where lives show normally until the next level. A game over
  ends the trap and the banked lives are lost, as with any game over.
- Upside Down Trap: the camera rolls 180 degrees (``ram.CAM_ROT_Z``). The HUD stays upright and the controls are not
  flipped with the view.
- Reverse Controls Trap: left and right are swapped (``hook``).
- Button Swap Trap: jump is on Square/Circle and spin on X (``hook``).

The clock only runs while a level (or bonus round) is being played, so the map and loading screens freeze it. The
same trap received again adds its duration. Effects are only applied in a level and removed everywhere else, so the
map always plays normally. The state lives in the server's data storage, so a client restart picks the traps back
up, and the client clears leftover effects (camera roll, hook) on connect when no trap is active.
"""
from dataclasses import dataclass, field, replace
from typing import Any

from . import hook, ram

NO_LIVES_TRAP = "No Lives Trap"
UPSIDE_DOWN_TRAP = "Upside Down Trap"
REVERSE_CONTROLS_TRAP = "Reverse Controls Trap"
BUTTON_SWAP_TRAP = "Button Swap Trap"
TIMED_TRAPS: tuple[str, ...] = (NO_LIVES_TRAP, UPSIDE_DOWN_TRAP, REVERSE_CONTROLS_TRAP, BUTTON_SWAP_TRAP)


@dataclass(frozen=True)
class TimedTraps:
    remaining: dict[str, float] = field(default_factory=dict)
    """Seconds of play left per active trap"""
    banked: int = 0
    """Lives (<< 8) held back by the No Lives Trap"""

    def active(self, name: str) -> bool:
        return self.remaining.get(name, 0) > 0

    @property
    def any_active(self) -> bool:
        return any(seconds > 0 for seconds in self.remaining.values())

    def add(self, name: str, seconds: float) -> "TimedTraps":
        remaining = dict(self.remaining)
        remaining[name] = remaining.get(name, 0) + seconds
        return replace(self, remaining=remaining)

    def to_json(self) -> dict[str, Any]:
        return {"remaining": {name: round(seconds, 1) for name, seconds in self.remaining.items() if seconds > 0},
                "banked": self.banked}

    @classmethod
    def from_json(cls, data: Any) -> "TimedTraps":
        if not isinstance(data, dict):
            return cls()
        remaining = {str(name): float(seconds) for name, seconds in dict(data.get("remaining") or {}).items()
                     if name in TIMED_TRAPS and float(seconds) > 0}
        return cls(remaining, int(data.get("banked", 0)))


def in_level(snap: ram.Snapshot) -> bool:
    """A level or bonus round is being played (not the map, the end screen or a transition)"""
    return snap.gamestate == ram.GAMESTATE_PLAYING and snap.level not in (ram.LID_MAP, ram.LID_LEVEL_END)


def tick(state: TimedTraps, snap: ram.Snapshot, seconds: float) -> tuple[TimedTraps, list[str]]:
    """Count down while a level is played. Returns the new state and the traps that just ended."""
    if snap.gamestate == ram.GAMESTATE_GAME_OVER and state.active(NO_LIVES_TRAP):
        remaining = {name: left for name, left in state.remaining.items() if name != NO_LIVES_TRAP}
        return TimedTraps(remaining, 0), [NO_LIVES_TRAP]
    if not in_level(snap) or seconds <= 0 or not state.any_active:
        return state, []
    remaining: dict[str, float] = {}
    ended: list[str] = []
    for name, left in state.remaining.items():
        left -= seconds
        if left > 0:
            remaining[name] = left
        else:
            ended.append(name)
    return replace(state, remaining=remaining), ended


@dataclass
class Plan:
    state: TimedTraps
    writes: dict[int, int] = field(default_factory=dict)
    guards: dict[int, int] = field(default_factory=dict)
    flags: int = 0
    """Controller hook flags wanted now"""
    notes: list[str] = field(default_factory=list)


def plan(state: TimedTraps, snap: ram.Snapshot, cam_rot_z: int) -> Plan:
    """RAM writes that make the game match the active traps. The new state only holds if the writes succeed."""
    out = Plan(state)
    playing = in_level(snap)

    # Camera: only ever undo a roll we set
    want = ram.CAM_ROLL_FLIPPED if playing and state.active(UPSIDE_DOWN_TRAP) else 0
    if cam_rot_z != want and (want or cam_rot_z == ram.CAM_ROLL_FLIPPED):
        out.writes[ram.CAM_ROT_Z], out.guards[ram.CAM_ROT_Z] = want, cam_rot_z

    if playing:
        out.flags = ((hook.FLAG_REVERSE_X if state.active(REVERSE_CONTROLS_TRAP) else 0)
                     | (hook.FLAG_SWAP_BUTTONS if state.active(BUTTON_SWAP_TRAP) else 0))

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
