-- C1AP round 9: the v0.4 timed traps, triggered by keyboard (no client needed).
-- Keys are from the ones BizHawk leaves free here (B C G H J L M N O R U V):
--   H  toggle Upside Down        (sin/cos of the camera roll, through the hook)
--   J  No Lives for 20 seconds   (Crash's lives field = 0, banked and given back)
--   L  toggle Reverse Controls   (left <-> right, through the hook)
--   M  toggle Button Swap        (X <-> Square/Circle, through the hook)
--   U  undo everything
-- The hook: Pad_Update's jal PadRead and Gfx_UpdateMatrices' first jal sin / jal cos go to code in the cave
-- while any flag is set, and back to the game's code when none is.
-- crash1/test/test_hook.py checks ROUTINE and the constants below match crash1/hook.py.

memory.usememorydomain("MainRAM")

local CAVE = 0x8000F400          -- flags word, then ROUTINE
local PAD_UPDATE = 0x800167A4
local JAL_PAD_READ = 0x0C00F918
local JAL_CAVE = 0x0C003D01
local GFX_UPDATE_MATRICES = 0x80017A14
local JAL_SIN = 0x0C00E417
local JAL_ROLL_SIN = 0x0C003D23
local JAL_COS = 0x0C00E434
local JAL_ROLL_COS = 0x0C003D2A
local CAM_ROT_Z = 0x80057878
local PAUSE_OBJ = 0x80061964
local CRASH_PTR = 0x800566B4
local GAMESTATE = 0x800618D0
local FIELD_LIVES = 0x160 + 4 * 1
local PAD_SCAN, GFX_SCAN = 0x200, 0x80
local NO_LIVES_FRAMES = 20 * 60

local ROUTINE = {
  0x27BDFFE8, 0xAFBF0010, 0x0C00F918, 0x00000000, 0x8FBF0010, 0x3C088001,
  0x8D08F400, 0x00000000, 0x31090001, 0x00094823, 0x304A8000, 0x000A5082,
  0x304B2000, 0x000B5880, 0x014B5025, 0x304BA000, 0x014B5026, 0x01495024,
  0x004A1026, 0x31090002, 0x00094842, 0x00094823, 0x304A0040, 0x000A5040,
  0x304B00A0, 0x000B582B, 0x000B5980, 0x014B5025, 0x304B00E0, 0x014B5026,
  0x01495024, 0x004A1026, 0x03E00008, 0x27BD0018, 0x3C088001, 0x8D08F400,
  0x00000000, 0x31080004, 0x00084240, 0x0800E417, 0x00882026, 0x3C088001,
  0x8D08F400, 0x00000000, 0x31080004, 0x00084240, 0x0800E434, 0x00882026,
}

local function off(address) return address & 0x1FFFFF end
local function r32(address) return memory.read_u32_le(off(address)) end
local function w32(address, value) memory.write_u32_le(off(address), value & 0xFFFFFFFF) end
local function log(fmt, ...) console.log(string.format("[%d] " .. fmt, emu.framecount(), ...)) end

local CODE = CAVE + 4
local CAVE_WORDS = 1 + #ROUTINE

-- Survey: the cave and 0x100 bytes around it should be zero before we touch anything
local function survey(tag)
  local nonzero = {}
  for address = CAVE - 0x100, CAVE + 4 * CAVE_WORDS + 0x100 - 4, 4 do
    local value = r32(address)
    if value ~= 0 then nonzero[#nonzero + 1] = string.format("%08X=%08X", address, value) end
  end
  if #nonzero == 0 then
    if tag == "periodic" then return end
    log("cave survey (%s): all zero around 0x%08X", tag, CAVE)
  else
    log("cave survey (%s): %d non-zero words: %s", tag, #nonzero, table.concat(nonzero, " ", 1, math.min(#nonzero, 12)))
  end
end

-- Call sites: {address, original, hooked, name}
local function find(start, size, words, only_one)
  local found = {}
  for address = start, start + size - 4, 4 do
    local word = r32(address)
    for _, w in ipairs(words) do
      if word == w then found[#found + 1] = address end
    end
  end
  if only_one and #found ~= 1 then return nil, #found end
  return found[1], #found
end

local function find_calls()
  local pad, n = find(PAD_UPDATE, PAD_SCAN, {JAL_PAD_READ, JAL_CAVE}, true)
  local sin = find(GFX_UPDATE_MATRICES, GFX_SCAN, {JAL_SIN, JAL_ROLL_SIN}, false)
  local cos = find(GFX_UPDATE_MATRICES, GFX_SCAN, {JAL_COS, JAL_ROLL_COS}, false)
  log("calls: PadRead %s (%d found), sin %s, cos %s",
    pad and string.format("0x%08X", pad) or "MISSING", n,
    sin and string.format("0x%08X", sin) or "MISSING", cos and string.format("0x%08X", cos) or "MISSING")
  if not (pad and sin and cos) then return nil end
  return {
    {pad, JAL_PAD_READ, JAL_CAVE, "pad"},
    {sin, JAL_SIN, JAL_ROLL_SIN, "sin"},
    {cos, JAL_COS, JAL_ROLL_COS, "cos"},
  }
end

local function code_ok()
  for i, word in ipairs(ROUTINE) do
    if r32(CODE + 4 * (i - 1)) ~= word then return false end
  end
  return true
end

local function crash_lives_address()
  local ptr = r32(CRASH_PTR)
  if ptr < 0x80000000 or ptr >= 0x80200000 then return nil end
  return ptr + FIELD_LIVES
end

survey("start")
local calls = find_calls()

local flags = 0
local no_lives_left, banked = 0, 0
local installed = false

local function sync_hook()
  if not calls then return end
  if flags ~= 0 then
    if not code_ok() then
      if installed then log("cave code changed under us, rewriting") end
      for i, word in ipairs(ROUTINE) do w32(CODE + 4 * (i - 1), word) end
      installed = true
    end
    w32(CAVE, flags)
    for _, c in ipairs(calls) do
      if r32(c[1]) == c[2] then w32(c[1], c[3]); log("hooked %s at 0x%08X", c[4], c[1]) end
    end
  else
    for _, c in ipairs(calls) do
      if r32(c[1]) == c[3] then w32(c[1], c[2]); log("restored %s at 0x%08X", c[4], c[1]) end
    end
    if r32(CAVE) ~= 0 then w32(CAVE, 0) end
  end
end

local function give_lives_back()
  local address = crash_lives_address()
  if banked > 0 and address then
    w32(address, math.min(r32(address) + banked, 99 << 8))
    log("No Lives over: %d lives back", banked >> 8)
    banked = 0
  end
end

local function toggle(bit, name)
  flags = flags ~ bit
  log("%s %s", name, flags & bit ~= 0 and "on" or "off")
end

local actions = {
  H = function() toggle(4, "Upside Down") end,
  J = function()
    no_lives_left = no_lives_left + NO_LIVES_FRAMES
    log("No Lives: %d frames left", no_lives_left)
  end,
  L = function() toggle(1, "Reverse Controls") end,
  M = function() toggle(2, "Button Swap") end,
  U = function()
    flags, no_lives_left = 0, 0
    give_lives_back()
    log("all traps off")
  end,
}

local held = {}
while true do
  local keys = input.get()
  for key, action in pairs(actions) do
    if keys[key] and not held[key] then action() end
    held[key] = keys[key] == true
  end

  if no_lives_left > 0 then
    local address = crash_lives_address()
    if address and r32(GAMESTATE) == 0x100 then
      local lives = r32(address)
      if lives > 0 then banked = banked + lives; w32(address, 0); log("banked %d lives", lives >> 8) end
      no_lives_left = no_lives_left - 1
      if no_lives_left == 0 then give_lives_back() end
    elseif r32(GAMESTATE) == 0x200 and banked > 0 then
      log("game over during No Lives: %d banked lives lost", banked >> 8)
      no_lives_left, banked = 0, 0
    end
  end

  sync_hook()
  if emu.framecount() % 600 == 0 and flags == 0 and not installed then survey("periodic") end

  local hooked = 0
  if calls then
    for _, c in ipairs(calls) do
      if r32(c[1]) == c[3] then hooked = hooked + 1 end
    end
  end
  gui.text(10, 40, string.format("roll %03X  pause %08X", r32(CAM_ROT_Z) & 0xFFFF, r32(PAUSE_OBJ)))
  gui.text(10, 55, string.format("flags %d  hooked %s  cave %s", flags, calls and (hooked .. "/3") or "??",
    installed and (code_ok() and "ok" or "BAD") or "empty"))
  gui.text(10, 70, string.format("no lives %.1fs  banked %d", no_lives_left / 60, banked >> 8))
  emu.frameadvance()
end
