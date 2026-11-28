"""BizHawk client for Crash Bandicoot (PS1, NTSC-U).

All game logic lives in ``watcher.py``; this module only talks to BizHawk and the server.
"""
import logging
import struct
import time
from collections import Counter
from typing import TYPE_CHECKING, Any

from NetUtils import ClientStatus
import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import filler, hook, ram, timed, trap
from .items import APPLIED_ON_MAP, GAME_NAME, item_name_to_id
from .timed import TIMED_TRAPS, TimedTraps
from .trap import TrapState
from .watcher import SlotInfo, Watcher

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

logger = logging.getLogger("Client")

ITEM_ID_TO_NAME = {item_id: name for name, item_id in item_name_to_id.items()}

SERIAL_MARKERS = (b"SCUS_949.00", b"SCUS-94900")
"""Boot executable name; the BIOS leaves SYSTEM.CNF's BOOT line in kernel RAM"""
SERIAL_KNOWN_OFFSETS = (0x928C, 0x9E19, 0xB8B7, 0x10E8A)  # OK: where the ID sat in every BizHawk test
SERIAL_SCAN_SIZE = 0x20000
SERIAL_SCAN_CHUNK = 0x4000
"""The connector returns one line per reply and asyncio caps a line at 64 KiB (base64 included), so read in chunks"""
KNOWN_HASHES: frozenset[str] = frozenset()
"""BizHawk disc hashes of verified NTSC-U dumps. Filled in as people report them."""


def contains_serial(data: bytes) -> bool:
    return any(marker in data for marker in SERIAL_MARKERS)


async def find_serial(ctx: "BizHawkClientContext") -> bool:
    """Look for the disc ID: first at the known offsets, then a chunked scan of the first 128 KiB."""
    width = max(len(marker) for marker in SERIAL_MARKERS)
    known = await bizhawk.read(ctx.bizhawk_ctx, [(address, width, ram.DOMAIN) for address in SERIAL_KNOWN_OFFSETS])
    if any(contains_serial(block) for block in known):
        return True
    for start in range(0, SERIAL_SCAN_SIZE, SERIAL_SCAN_CHUNK):
        # overlap each chunk by the marker width so an ID split across two chunks is still found
        block = (await bizhawk.read(ctx.bizhawk_ctx, [(start, SERIAL_SCAN_CHUNK + width, ram.DOMAIN)]))[0]
        if contains_serial(block):
            return True
    return False


def _filler_key(ctx: "BizHawkClientContext") -> str:
    return f"C1AP_filler_applied_{ctx.team}_{ctx.slot}"


def _trap_key(ctx: "BizHawkClientContext") -> str:
    """v0.3 No Lives Trap (one level, set on the map); only read to finish a trap started before v0.4"""
    return f"C1AP_trap_{ctx.team}_{ctx.slot}"


def _timed_key(ctx: "BizHawkClientContext") -> str:
    return f"C1AP_timed_traps_{ctx.team}_{ctx.slot}"


TRAP_SAVE_INTERVAL = 3.0
"""Seconds between saves of the trap clocks while traps run"""
MAX_TICK = 1.0
"""Longest step of the trap clock between two polls, so a stalled emulator does not use up a trap"""


async def _store(ctx: "BizHawkClientContext", key: str, value: Any) -> None:
    ctx.stored_data[key] = value  # local copy until the server echoes the update
    await ctx.send_msgs([{
        "cmd": "Set", "key": key, "default": None, "want_reply": False,
        "operations": [{"operation": "replace", "value": value}],
    }])


async def _write_word(ctx: "BizHawkClientContext", address: int, value: int, guard: int) -> bool:
    return await _write_words(ctx, {address: value}, {address: guard})


async def _write_words(ctx: "BizHawkClientContext", writes: dict[int, int], guards: dict[int, int]) -> bool:
    """Write every word only if every guard still holds (all in the same frame)"""
    return await bizhawk.guarded_write(
        ctx.bizhawk_ctx,
        [(ram.offset(address), ram.word_bytes(value), ram.DOMAIN) for address, value in writes.items()],
        [(ram.offset(address), ram.word_bytes(value), ram.DOMAIN) for address, value in guards.items()],
    )


class Crash1Client(BizHawkClient):
    game = GAME_NAME
    system = "PSX"
    patch_suffix = None

    def __init__(self) -> None:
        super().__init__()
        self.watcher: Watcher | None = None
        self.sent: set[int] = set()
        self.goal_sent = False
        self.notify_set = False
        self.crash_ptr_logged = 0
        self.unreadable_logged = -1
        self.hook_calls: dict[int, tuple[int, int]] | None = None
        """Call sites the traps hook, {address: (original jal, hooked jal)}, found once"""
        self.hook_calls_missing_logged = False
        self.last_tick: float | None = None
        self.last_trap_save = 0.0

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        try:
            rom_hash = await bizhawk.get_hash(ctx.bizhawk_ctx)
            # No caching of misses: during the BIOS intro the ID isn't in RAM yet, even for Crash.
            if rom_hash not in KNOWN_HASHES and not await find_serial(ctx):
                return False
                logger.info(f"Crash Bandicoot NTSC-U detected (disc hash {rom_hash}, not in the verified list).")
        except bizhawk.RequestFailedError:
            return False

        ctx.game = self.game
        ctx.items_handling = 0b111  # every item comes from the server, including our own
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.1   # fast enough to redirect a level load
        self.watcher = None
        self.sent.clear()
        self.goal_sent = False
        self.notify_set = False
        return True

    def on_package(self, ctx: "BizHawkClientContext", cmd: str, args: dict) -> None:
        if cmd == "Connected":
            self.watcher = None  # rebuilt from the new slot data
            self.sent.clear()
            self.goal_sent = False
            self.notify_set = False

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        if ctx.server is None or ctx.server.socket.closed or ctx.slot_data is None:
            return

        if self.watcher is None:
            self.watcher = Watcher(SlotInfo.from_slot_data(ctx.slot_data))
            await ctx.update_death_link(bool(ctx.slot_data.get("death_link", False)))
        if not self.notify_set:
            ctx.set_notify(_filler_key(ctx), _trap_key(ctx), _timed_key(ctx))
            self.notify_set = True

        try:
            blocks = await bizhawk.read(ctx.bizhawk_ctx, ram.read_requests())
            snap = ram.parse(*blocks)
            if snap.crash_readable:
                fields_block = (await bizhawk.read(ctx.bizhawk_ctx, [ram.crash_request(snap.crash_ptr)]))[0]
                snap = ram.with_crash(snap, fields_block)
                self._log_crash_object(snap)
            elif snap.gamestate == ram.GAMESTATE_PLAYING and snap.level not in (ram.LID_MAP, ram.LID_LEVEL_END):
                self._log_unreadable(snap)

            received = Counter(ITEM_ID_TO_NAME.get(item.item, "") for item in ctx.items_received)
            checked = ctx.checked_locations | self.sent
            actions = self.watcher.step(snap, received, checked)

            if actions.writes:
                await bizhawk.guarded_write(
                    ctx.bizhawk_ctx,
                    [(ram.offset(address), ram.word_bytes(value), ram.DOMAIN)
                     for address, value in actions.writes.items()],
                    [(ram.offset(address), ram.word_bytes(value), ram.DOMAIN)
                     for address, value in actions.guards.items()],
                )

            new_locations = actions.locations - checked
            if new_locations:
                self.sent |= new_locations
                await ctx.check_locations(new_locations)

            for note in actions.notes:
                logger.info(f"[C1AP verify] {note}")

            if actions.died and "DeathLink" in ctx.tags:
                await ctx.send_death(f"{ctx.player_names[ctx.slot]} lost a life.")

            if actions.goal and not self.goal_sent and not ctx.finished_game:
                await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
                self.goal_sent = True
                ctx.finished_game = True

            if await self._advance_trap(ctx, snap):
                return  # lives were just restored; filler waits for the next poll
            if await self._run_timed_traps(ctx, snap):
                return  # lives were just changed; filler waits for the next poll
            if actions.can_apply_filler or actions.can_apply_live_filler:
                await self._apply_filler(ctx, snap, on_map=actions.can_apply_filler)
        except bizhawk.RequestFailedError:
            pass  # emulator busy or disconnected; try again next poll

    # Timed traps

    async def _run_timed_traps(self, ctx: "BizHawkClientContext", snap: ram.Snapshot) -> bool:
        """Count the traps down and make the game match them. Returns True if the lives were changed."""
        key = _timed_key(ctx)
        if key not in ctx.stored_data:
            return False  # not loaded yet
        now = time.monotonic()
        elapsed = 0.0 if self.last_tick is None else min(now - self.last_tick, MAX_TICK)
        self.last_tick = now

        stored = TimedTraps.from_json(ctx.stored_data[key])
        state, ended, started = timed.tick(stored, snap, elapsed)
        for name in ended:
            if name == timed.NO_LIVES_TRAP and snap.gamestate == ram.GAMESTATE_GAME_OVER:
                logger.info("No Lives Trap over: game over, the banked lives are lost.")
            else:
                logger.info(f"{name} over.")
        for name in started:
            waiting = f" ({len(state.queue)} more waiting)" if state.queue else ""
            logger.info(f"{name}! {state.left:g} seconds.{waiting}")

        await self._find_hook_calls(ctx)
        calls = sorted(self.hook_calls or {})
        requests = [(ram.offset(hook.CAVE), hook.CAVE_SIZE, ram.DOMAIN)]
        requests += [(ram.offset(address), 4, ram.DOMAIN) for address in calls]
        blocks = await bizhawk.read(ctx.bizhawk_ctx, requests)

        out = timed.plan(state, snap)
        lives_changed = False
        if out.writes and await _write_words(ctx, out.writes, out.guards):
            state = out.state
            lives_changed = True
            for note in out.notes:
                logger.info(note)
        if calls:
            current = {address: struct.unpack_from("<I", block)[0] for address, block in zip(calls, blocks[1:])}
            await self._sync_hooks(ctx, out.flags, blocks[0], current)

        changed = bool(ended or started) or state.banked != stored.banked
        if changed or (state.busy and now - self.last_trap_save >= TRAP_SAVE_INTERVAL):
            if state.to_json() != stored.to_json():
                await _store(ctx, key, state.to_json())
            self.last_trap_save = now
        return lives_changed

    async def _find_hook_calls(self, ctx: "BizHawkClientContext") -> None:
        if self.hook_calls is not None or self.hook_calls_missing_logged:
            return
        pad, gfx = await bizhawk.read(ctx.bizhawk_ctx, [
            (ram.offset(hook.PAD_UPDATE), hook.PAD_UPDATE_SCAN, ram.DOMAIN),
            (ram.offset(hook.GFX_UPDATE_MATRICES), hook.GFX_SCAN, ram.DOMAIN),
        ])
        self.hook_calls = hook.find_calls(pad, gfx)
        if self.hook_calls is None:
            self.hook_calls_missing_logged = True
            logger.info("[C1AP verify] The calls the traps hook were not found: "
                        "Upside Down, Reverse Controls and Button Swap do nothing.")

    async def _sync_hooks(self, ctx: "BizHawkClientContext", flags: int, cave: bytes, current: dict[int, int]) -> None:
        """Point the hooked calls at the cave while a hook trap runs, and back at the game's code otherwise"""
        assert self.hook_calls is not None
        cave_flags = struct.unpack_from("<I", cave)[0]
        hooked = {address for address, word in current.items() if word == self.hook_calls[address][1]}
        if flags:
            if cave[4:] != hook.CAVE_CODE_BYTES:
                await bizhawk.write(ctx.bizhawk_ctx, [(ram.offset(hook.CODE), hook.CAVE_CODE_BYTES, ram.DOMAIN)])
                if hooked:
                    logger.info("[C1AP verify] The trap code changed while in use; rewritten.")
                return  # hooked on the next poll, once the code reads back intact
            writes: dict[int, int] = {}
            guards: dict[int, int] = {}
            if cave_flags != flags:
                writes[hook.FLAGS] = flags
            for address, (original, patched) in self.hook_calls.items():
                if current[address] == original:
                    writes[address], guards[address] = patched, original
            if writes:
                await _write_words(ctx, writes, guards)
        elif hooked:
            # Calls back first; the flags are cleared on the next poll
            await _write_words(ctx, {address: self.hook_calls[address][0] for address in hooked},
                               {address: self.hook_calls[address][1] for address in hooked})
        elif cave_flags:
            await _write_words(ctx, {hook.FLAGS: 0}, {})

    async def _advance_trap(self, ctx: "BizHawkClientContext", snap: ram.Snapshot) -> bool:
        """Track an active No Lives Trap; returns True if this poll restored the lives."""
        key = _trap_key(ctx)
        if key not in ctx.stored_data:
            return False  # not loaded yet
        state = TrapState.from_json(ctx.stored_data[key])
        new_state, restore = trap.advance(state, snap)
        if restore is not None:
            if not await _write_word(ctx, ram.LIFE_COUNT, restore, snap.lives):
                return False
            logger.info(f"No Lives Trap over: {restore // ram.UNIT} lives.")
        if new_state != state:
            await _store(ctx, key, None if new_state is None else new_state.to_json())
        return restore is not None

    def _log_unreadable(self, snap: ram.Snapshot) -> None:
        """Once per level: the pointer couldn't be followed (verification of CRASH_PTR)"""
        if snap.level == self.unreadable_logged:
            return
        self.unreadable_logged = snap.level
        logger.info(f"[C1AP verify] In level 0x{snap.level:02X} but CRASH_PTR (0x{ram.CRASH_PTR:08X}) holds "
                    f"0x{snap.crash_ptr:08X}, not a RAM pointer (player 0x{snap.player_ptr:08X}): "
                    f"in-level filler and lives are off")

    def _log_crash_object(self, snap: ram.Snapshot) -> None:
        """Once per pointer value: what the Crash object holds, to verify the field offsets in a test round"""
        if snap.crash is None or snap.crash_ptr == self.crash_ptr_logged:
            return
        self.crash_ptr_logged = snap.crash_ptr
        fields = snap.crash
        logger.info(f"[C1AP verify] Crash object 0x{snap.crash_ptr:08X} (player 0x{snap.player_ptr:08X}) "
                    f"in level 0x{snap.level:02X}: "
                    f"lives {fields.lives / ram.UNIT:g}, fruit {fields.fruit / ram.UNIT:g}, tokens "
                    f"T{fields.tawna / ram.UNIT:g} B{fields.brio / ram.UNIT:g} C{fields.cortex / ram.UNIT:g}, "
                    f"plausible {fields.plausible} (globals: lives {snap.lives / ram.UNIT:g}, "
                    f"fruit {snap.fruit / ram.UNIT:g})")

    async def _apply_filler(self, ctx: "BizHawkClientContext", snap: ram.Snapshot, on_map: bool) -> None:
        """Apply one filler item or trap not yet applied: anything on the map, lives and fruit in a level.
        Applied counts per name live in data storage so they survive restarts."""
        key = _filler_key(ctx)
        if key not in ctx.stored_data or _timed_key(ctx) not in ctx.stored_data:
            return  # not loaded yet
        fillers = [name for item in ctx.items_received
                   if (name := ITEM_ID_TO_NAME.get(item.item)) in APPLIED_ON_MAP]
        applied = filler.applied_counts(ctx.stored_data[key], fillers)

        for name in filler.pending(fillers, applied):
            if name in TIMED_TRAPS:
                seconds = int(ctx.slot_data.get("trap_duration", 20))
                state = TimedTraps.from_json(ctx.stored_data[_timed_key(ctx)]).add(name, seconds)
                await _store(ctx, _timed_key(ctx), state.to_json())
                ahead = len(state.queue) - 1 + (state.current is not None)
                logger.info(f"{name} received: it starts in a level" + (f", after {ahead} more." if ahead else "."))
            else:
                plan = filler.plan_on_map(name, snap) if on_map else filler.plan_in_level(name, snap)
                if plan is None:
                    continue  # waits for the map
                if plan.writes and not await _write_words(ctx, plan.writes, plan.guards):
                    return
                if not on_map:
                    logger.info(f"{name} applied in the level.")
            applied[name] += 1
            await _store(ctx, key, dict(applied))
            return
