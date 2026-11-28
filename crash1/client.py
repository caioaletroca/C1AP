"""BizHawk client for Crash Bandicoot (PS1, NTSC-U).

All game logic lives in ``watcher.py``; this module only talks to BizHawk and the server.
"""
import logging
from collections import Counter
from typing import TYPE_CHECKING, Any

from NetUtils import ClientStatus
import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import filler, ram, trap
from .items import APPLIED_ON_MAP, GAME_NAME, NO_LIVES_TRAP, item_name_to_id
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
    return f"C1AP_trap_{ctx.team}_{ctx.slot}"


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
            ctx.set_notify(_filler_key(ctx), _trap_key(ctx))
            self.notify_set = True

        try:
            globals_block, lid_block, crash_ptr_block = await bizhawk.read(ctx.bizhawk_ctx, ram.read_requests())
            snap = ram.parse(globals_block, lid_block, crash_ptr_block)
            if snap.crash_readable:
                fields_block = (await bizhawk.read(ctx.bizhawk_ctx, [ram.crash_request(snap.crash_ptr)]))[0]
                snap = ram.with_crash(snap, fields_block)
                self._log_crash_object(snap)

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
            if actions.can_apply_filler or actions.can_apply_live_filler:
                await self._apply_filler(ctx, snap, on_map=actions.can_apply_filler)
        except bizhawk.RequestFailedError:
            pass  # emulator busy or disconnected; try again next poll

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

    def _log_crash_object(self, snap: ram.Snapshot) -> None:
        """Once per pointer value: what the Crash object holds, to verify the field offsets in a test round"""
        if snap.crash is None or snap.crash_ptr == self.crash_ptr_logged:
            return
        self.crash_ptr_logged = snap.crash_ptr
        fields = snap.crash
        logger.info(f"[C1AP verify] Crash object 0x{snap.crash_ptr:08X} in level 0x{snap.level:02X}: "
                    f"lives {fields.lives / ram.UNIT:g}, fruit {fields.fruit / ram.UNIT:g}, tokens "
                    f"T{fields.tawna / ram.UNIT:g} B{fields.brio / ram.UNIT:g} C{fields.cortex / ram.UNIT:g}, "
                    f"plausible {fields.plausible} (globals: lives {snap.lives / ram.UNIT:g}, "
                    f"fruit {snap.fruit / ram.UNIT:g})")

    async def _apply_filler(self, ctx: "BizHawkClientContext", snap: ram.Snapshot, on_map: bool) -> None:
        """Apply one filler item or trap not yet applied: anything on the map, lives and fruit in a level.
        Applied counts per name live in data storage so they survive restarts."""
        key = _filler_key(ctx)
        if key not in ctx.stored_data or _trap_key(ctx) not in ctx.stored_data:
            return  # not loaded yet
        fillers = [name for item in ctx.items_received
                   if (name := ITEM_ID_TO_NAME.get(item.item)) in APPLIED_ON_MAP]
        applied = filler.applied_counts(ctx.stored_data[key], fillers)

        for name in filler.pending(fillers, applied):
            if name == NO_LIVES_TRAP:
                if not on_map:
                    continue
                state, lives = trap.spring(TrapState.from_json(ctx.stored_data[_trap_key(ctx)]), snap)
                if lives is not None:
                    if not await _write_word(ctx, ram.LIFE_COUNT, lives, snap.lives):
                        return
                    await _store(ctx, _trap_key(ctx), state.to_json())
                    logger.info("No Lives Trap! 0 lives for the next level.")
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
