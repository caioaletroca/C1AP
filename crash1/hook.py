"""Code hooks for the Reverse Controls, Button Swap and Upside Down traps. Pure logic, no I/O.

The game reads the controller once per frame in ``Pad_Update`` (kdecomp ``src/main/engine/shutdown.c``, NTSC-U
0x800167A4) through ``jal PadRead`` and overwrites its pad state right after, so writing the pad state from outside
never sticks. Instead, that one ``jal`` is pointed at a short routine in unused kernel RAM (the cave). The routine
calls ``PadRead`` itself, then swaps bits in the result according to a flags word stored just before it:

- bit 0: left (0x8000) <-> right (0x2000)
- bit 1: X (0x40, jump) -> Square (0x80, spin); Square or Circle (0x80 / 0x20, spin) -> X (jump)

The swap happens before ``Pad_Update`` drops "right" when "left" is held, so movement stays consistent. Pad 0's buttons
are the low 16 bits of ``PadRead``'s result on NTSC-U and are active-high, as ``Pad_Update`` tests them
(``& 0x1000`` = up). With the flags at 0 the routine changes nothing; the client still puts the original ``jal`` back
whenever no control trap is active, so the game runs unpatched code outside traps.

Upside Down: the camera roll ``g_cam_rot_z`` can't simply be written, because ``Zone_PathProgressToLoc`` copies the
camera path's roll into it every frame the camera moves, before the frame is drawn. Its only reader is
``Gfx_UpdateMatrices`` (NTSC-U 0x80017A14), which starts with ``sin(-g_cam_rot_z)`` and ``cos(-g_cam_rot_z)``. Those two
calls (the first ``jal sin`` and ``jal cos`` in the function) go to wrappers that add 180 degrees to the angle when
bit 2 of the flags is set, then jump on to ``sin`` / ``cos``. Angles are 12-bit, so flipping bit 11 adds 180 degrees.

All three calls are hooked together while any of these traps runs, and put back when none does.

VERIFY: the cave (0x8000F400) is kernel RAM below the executable (loaded at 0x80010000) that the BIOS should leave
unused; tools/c1ap_trap_test.lua checks it stays zero, and the client rewrites the routine if it ever changes.
"""
import struct

PAD_UPDATE = 0x800167A4        # VERIFY: kdecomp configs/USA/sym.main.txt Pad_Update
PAD_UPDATE_SCAN = 0x200        # bytes of Pad_Update searched for the call
PAD_READ = 0x8003E460          # VERIFY: kdecomp PadRead
GFX_UPDATE_MATRICES = 0x80017A14  # VERIFY: kdecomp Gfx_UpdateMatrices
GFX_SCAN = 0x80                # bytes searched for its first jal sin / jal cos
SIN = 0x8003905C               # VERIFY: kdecomp sin
COS = 0x800390D0               # VERIFY: kdecomp cos
CAVE = 0x8000F400              # VERIFY: flags word, then the routine
FLAGS = CAVE
CODE = CAVE + 4

FLAG_REVERSE_X = 1
FLAG_SWAP_BUTTONS = 2
FLAG_UPSIDE_DOWN = 4

PAD_LEFT, PAD_RIGHT = 0x8000, 0x2000
PAD_X, PAD_SQUARE, PAD_CIRCLE = 0x40, 0x80, 0x20

# MIPS registers and encoders (only what the routine uses)
ZERO, V0, A0, T0, T1, T2, T3, SP, RA = 0, 2, 4, 8, 9, 10, 11, 29, 31


def _r(rs: int, rt: int, rd: int, shamt: int, funct: int) -> int:
    return (rs << 21) | (rt << 16) | (rd << 11) | (shamt << 6) | funct


def _i(op: int, rs: int, rt: int, imm: int) -> int:
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def jal(target: int) -> int:
    return (3 << 26) | ((target >> 2) & 0x03FFFFFF)


def j(target: int) -> int:
    return (2 << 26) | ((target >> 2) & 0x03FFFFFF)


def addiu(rt: int, rs: int, imm: int) -> int: return _i(0x09, rs, rt, imm)
def andi(rt: int, rs: int, imm: int) -> int: return _i(0x0C, rs, rt, imm)
def lui(rt: int, imm: int) -> int: return _i(0x0F, 0, rt, imm)
def lw(rt: int, imm: int, rs: int) -> int: return _i(0x23, rs, rt, imm)
def sw(rt: int, imm: int, rs: int) -> int: return _i(0x2B, rs, rt, imm)
def sll(rd: int, rt: int, sa: int) -> int: return _r(0, rt, rd, sa, 0x00)
def srl(rd: int, rt: int, sa: int) -> int: return _r(0, rt, rd, sa, 0x02)
def jr(rs: int) -> int: return _r(rs, 0, 0, 0, 0x08)
def subu(rd: int, rs: int, rt: int) -> int: return _r(rs, rt, rd, 0, 0x23)
def and_(rd: int, rs: int, rt: int) -> int: return _r(rs, rt, rd, 0, 0x24)
def or_(rd: int, rs: int, rt: int) -> int: return _r(rs, rt, rd, 0, 0x25)
def xor(rd: int, rs: int, rt: int) -> int: return _r(rs, rt, rd, 0, 0x26)
def sltu(rd: int, rs: int, rt: int) -> int: return _r(rs, rt, rd, 0, 0x2B)


NOP = 0


def _hi_lo(address: int) -> tuple[int, int]:
    """lui/lw pair for an address (the lw offset is signed)"""
    return ((address + 0x8000) >> 16) & 0xFFFF, address & 0xFFFF


def _routine() -> tuple[int, ...]:
    hi, lo = _hi_lo(FLAGS)
    return (
        addiu(SP, SP, -24),
        sw(RA, 16, SP),
        jal(PAD_READ),               # a0 (the pad index) passes through
        NOP,
        lw(RA, 16, SP),
        lui(T0, hi),
        lw(T0, lo, T0),
        NOP,                         # load delay
        # Reverse X: diff = (swapped left/right) ^ (original), applied when bit 0 is set (t1 = 0 or -1)
        andi(T1, T0, FLAG_REVERSE_X),
        subu(T1, ZERO, T1),
        andi(T2, V0, PAD_LEFT),
        srl(T2, T2, 2),
        andi(T3, V0, PAD_RIGHT),
        sll(T3, T3, 2),
        or_(T2, T2, T3),
        andi(T3, V0, PAD_LEFT | PAD_RIGHT),
        xor(T2, T2, T3),
        and_(T2, T2, T1),
        xor(V0, V0, T2),
        # Button swap: X -> Square, Square/Circle -> X, applied when bit 1 is set
        andi(T1, T0, FLAG_SWAP_BUTTONS),
        srl(T1, T1, 1),
        subu(T1, ZERO, T1),
        andi(T2, V0, PAD_X),
        sll(T2, T2, 1),
        andi(T3, V0, PAD_SQUARE | PAD_CIRCLE),
        sltu(T3, ZERO, T3),
        sll(T3, T3, 6),
        or_(T2, T2, T3),
        andi(T3, V0, PAD_X | PAD_SQUARE | PAD_CIRCLE),
        xor(T2, T2, T3),
        and_(T2, T2, T1),
        xor(V0, V0, T2),
        jr(RA),
        addiu(SP, SP, 24),           # delay slot
    )


ROUTINE: tuple[int, ...] = _routine()
"""The controller routine, at CODE"""


def _roll(target: int) -> tuple[int, ...]:
    """Wrapper for sin / cos: a0 ^= 0x800 when FLAG_UPSIDE_DOWN is set, then jump on"""
    hi, lo = _hi_lo(FLAGS)
    return (
        lui(T0, hi),
        lw(T0, lo, T0),
        NOP,                         # load delay
        andi(T0, T0, FLAG_UPSIDE_DOWN),
        sll(T0, T0, 9),              # 4 << 9 = 0x800
        j(target),
        xor(A0, A0, T0),             # delay slot
    )


ROLL_SIN = CODE + 4 * len(ROUTINE)
ROLL_COS = ROLL_SIN + 4 * len(_roll(SIN))
CAVE_CODE: tuple[int, ...] = ROUTINE + _roll(SIN) + _roll(COS)
"""Everything after the flags word: the controller routine, then the sin and cos wrappers"""
CAVE_CODE_BYTES = struct.pack(f"<{len(CAVE_CODE)}I", *CAVE_CODE)
CAVE_SIZE = 4 + len(CAVE_CODE_BYTES)
JAL_PAD_READ = jal(PAD_READ)
JAL_CAVE = jal(CODE)
JAL_SIN, JAL_ROLL_SIN = jal(SIN), jal(ROLL_SIN)
JAL_COS, JAL_ROLL_COS = jal(COS), jal(ROLL_COS)


def find_call(block: bytes, start: int = PAD_UPDATE) -> int | None:
    """Address of the ``jal`` to hook in a block read from ``start``: the original call or an already hooked one.
    None if there isn't exactly one (not NTSC-U, or not loaded yet)."""
    found = [start + index for index in range(0, len(block) - 3, 4)
             if struct.unpack_from("<I", block, index)[0] in (JAL_PAD_READ, JAL_CAVE)]
    return found[0] if len(found) == 1 else None


def find_first(block: bytes, words: tuple[int, ...], start: int = GFX_UPDATE_MATRICES) -> int | None:
    """Address of the first of ``words`` in a block read from ``start``"""
    for index in range(0, len(block) - 3, 4):
        if struct.unpack_from("<I", block, index)[0] in words:
            return start + index
    return None


def find_calls(pad_block: bytes, gfx_block: bytes) -> dict[int, tuple[int, int]] | None:
    """Every call site to hook: {address: (original jal, hooked jal)}. None unless all three are found."""
    pad = find_call(pad_block)
    sin = find_first(gfx_block, (JAL_SIN, JAL_ROLL_SIN))
    cos = find_first(gfx_block, (JAL_COS, JAL_ROLL_COS))
    if pad is None or sin is None or cos is None:
        return None
    return {pad: (JAL_PAD_READ, JAL_CAVE), sin: (JAL_SIN, JAL_ROLL_SIN), cos: (JAL_COS, JAL_ROLL_COS)}


def swap(buttons: int, flags: int) -> int:
    """What the routine does to pad 0's buttons (for tests)"""
    if flags & FLAG_REVERSE_X:
        left, right = buttons & PAD_LEFT, buttons & PAD_RIGHT
        buttons = (buttons & ~(PAD_LEFT | PAD_RIGHT)) | (left >> 2) | (right << 2)
    if flags & FLAG_SWAP_BUTTONS:
        x, spin = buttons & PAD_X, buttons & (PAD_SQUARE | PAD_CIRCLE)
        buttons = (buttons & ~(PAD_X | PAD_SQUARE | PAD_CIRCLE)) | (PAD_SQUARE if x else 0) | (PAD_X if spin else 0)
    return buttons & 0xFFFFFFFF
