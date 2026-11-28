-- C1AP round 9: the v0.4 timed traps, triggered by keyboard (no client needed).
-- Keys are from the ones BizHawk leaves free here (B C G H J L M N O R U V):
--   H  toggle Upside Down camera  (CAM_ROT_Z = 0x800, held every frame while on)
--   J  No Lives for 20 seconds    (Crash's lives field = 0, banked and given back)
--   L  toggle Reverse Controls    (left <-> right, through the pad hook)
--   M  toggle Button Swap         (X <-> Square/Circle, through the pad hook)
--   U  undo everything
-- The on-screen text shows the camera roll, the pause object, the hook flags, the jal state and the cave.
-- tools/../crash1/test/test_hook.py checks ROUTINE and the constants below match crash1/hook.py.

memory.usememorydomain("MainRAM")

local CAVE = 0x8000F400          -- flags word, then the routine
local PAD_UPDATE = 0x800167A4
local JAL_PAD_READ = 0x0C00F918
local JAL_CAVE = 0x0C003D01
local CAM_ROT_Z = 0x80057878
local PAUSE_OBJ = 0x80061964
local CRASH_PTR = 0x800566B4
local GAMESTATE = 0x800618D0
local FIELD_LIVES = 0x160 + 4 * 1
local SCAN = 0x200
local NO_LIVES_FRAMES = 20 * 60

local ROUTINE = {
  0x27BDFFE8, 0xAFBF0010, 0x0C00F918, 0x00000000, 0x8FBF0010, 0x3C088001,
  0x8D08F400, 0x00000000, 0x31090001, 0x00094823, 0x304A8000, 0x000A5082,
  0x304B2000, 0x000B5880, 0x014B5025, 0x304BA000, 0x014B5026, 0x01495024,
  0x004A1026, 0x31090002, 0x00094842, 0x00094823, 0x304A0040, 0x000A5040,
  0x304B00A0, 0x000B582B, 0x000B5980, 0x014B5025, 0x304B00E0, 0x014B5026,
  0x01495024, 0x004A1026, 0x03E00008, 0x27BD0018,
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

local function find_call()
  local found = {}
  for address = PAD_UPDATE, PAD_UPDATE + SCAN - 4, 4 do
    local word = r32(address)
    if word == JAL_PAD_READ or word == JAL_CAVE then found[#found + 1] = address end
  end
  if #found == 1 then return found[1] end
  return nil, #found
end

local function routine_ok()
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
local call, count = find_call()
if call then
  log("jal PadRead found at 0x%08X (%s)", call, r32(call) == JAL_CAVE and "already hooked" or "original")
else
  log("VERIFY: %d matching jal in Pad_Update (want exactly 1)", count)
end

local camera_on, flags = false, 0
local no_lives_left, banked = 0, 0
local installed = false

local function sync_hook()
  call = call or find_call()
  if not call then return end
  if flags ~= 0 then
    if not routine_ok() then
      if installed then log("routine changed under us, rewriting") end
      for i, word in ipairs(ROUTINE) do w32(CODE + 4 * (i - 1), word) end
      installed = true
    end
    w32(CAVE, flags)
    if r32(call) == JAL_PAD_READ then w32(call, JAL_CAVE); log("hooked jal at 0x%08X", call) end
  else
    if r32(call) == JAL_CAVE then w32(call, JAL_PAD_READ); log("restored jal at 0x%08X", call) end
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

local actions = {
  H = function()
    camera_on = not camera_on
    if not camera_on and r32(CAM_ROT_Z) == 0x800 then w32(CAM_ROT_Z, 0) end
    log("Upside Down %s", camera_on and "on" or "off")
  end,
  J = function()
    no_lives_left = no_lives_left + NO_LIVES_FRAMES
    log("No Lives: %d frames left", no_lives_left)
  end,
  L = function() flags = flags ~ 1; log("Reverse Controls %s", flags & 1 ~= 0 and "on" or "off") end,
  M = function() flags = flags ~ 2; log("Button Swap %s", flags & 2 ~= 0 and "on" or "off") end,
  U = function()
    camera_on, flags, no_lives_left = false, 0, 0
    if r32(CAM_ROT_Z) == 0x800 then w32(CAM_ROT_Z, 0) end
    give_lives_back()
    log("all traps off")
  end,
}

local held = {}
local last_roll = nil
while true do
  local keys = input.get()
  for key, action in pairs(actions) do
    if keys[key] and not held[key] then action() end
    held[key] = keys[key] == true
  end

  local roll = r32(CAM_ROT_Z)
  if camera_on and roll ~= 0x800 then
    if last_roll == 0x800 then log("game reset the camera roll to 0x%X, flipping again", roll) end
    w32(CAM_ROT_Z, 0x800)
    roll = 0x800
  end
  last_roll = roll

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

  local hooked = call and r32(call) == JAL_CAVE
  gui.text(10, 40, string.format("roll %03X  pause %08X", roll, r32(PAUSE_OBJ)))
  gui.text(10, 55, string.format("flags %d  jal %s  cave %s", flags,
    call and (hooked and "HOOKED" or "orig") or "??", installed and (routine_ok() and "ok" or "BAD") or "empty"))
  gui.text(10, 70, string.format("no lives %.1fs  banked %d", no_lives_left / 60, banked >> 8))
  emu.frameadvance()
end
