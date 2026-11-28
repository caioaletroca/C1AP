"""Legacy (v0.3) No Lives Trap: lives drop to 0 for one level, then come back.

Since v0.4 traps are timed (``timed.py``) and nothing arms this one any more. The client still runs ``advance`` so a
trap armed by v0.3 (state in data storage) finishes and gives the lives back. The notes below describe v0.3.

The game only takes lives into a level when it loads, and the in-level counter lives in a game object whose address
changes per level, so the client can't restore lives mid-level the way C2AP's timed trap does. Instead:

1. On the map, the trap saves the current lives and sets them to 0 (another trap before the next level is used up
   without effect).
2. The next level is played with 0 lives: one death is a game over.
3. Back on the map, the saved lives are added to whatever the player has now (lives picked up in the level count).
   A game over ends the trap without restoring: Continue reloads the save, as in the vanilla game.

The state is kept in the server's data storage so it survives a client restart. Pure logic, no I/O.
"""
from dataclasses import dataclass
from typing import Any

from . import ram


@dataclass(frozen=True)
class TrapState:
    saved: int
    """LIFE_COUNT (<< 8) before the trap"""
    played: bool = False
    """A level has been entered since the trap was applied"""

    def to_json(self) -> dict[str, Any]:
        return {"saved": self.saved, "played": self.played}

    @classmethod
    def from_json(cls, data: Any) -> "TrapState | None":
        if not isinstance(data, dict):
            return None
        return cls(int(data["saved"]), bool(data.get("played", False)))


def advance(state: TrapState | None, snap: ram.Snapshot) -> tuple[TrapState | None, int | None]:
    """Move the trap along. Returns the new state and, when the trap ends on the map, the lives to write."""
    if state is None:
        return None, None
    if snap.gamestate == ram.GAMESTATE_GAME_OVER:
        return None, None
    if not state.played and snap.gamestate == ram.GAMESTATE_PLAYING and snap.level != ram.LID_MAP:
        return TrapState(state.saved, played=True), None
    if state.played and snap.on_map and snap.gamestate == ram.GAMESTATE_MAP:
        return None, min(snap.lives + state.saved, ram.MAX_LIVES)
    return state, None


def spring(state: TrapState | None, snap: ram.Snapshot) -> tuple[TrapState, int | None]:
    """A No Lives Trap received on the map. Returns the new state and the lives to write (None: already active)."""
    if state is not None:
        return state, None
    return TrapState(snap.lives), 0
