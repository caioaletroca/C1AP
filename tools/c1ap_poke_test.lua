-- C1AP round 5: writes the client will make. Run alongside c1ap_ram_watch.lua.
-- On start it searches RAM for the disc ID. Then, standing on the map:
--   U  open nodes 1-5   (LEVELSUNLOCKED = 5, MAPLEVELLINKS = 0x3F)
--   L  +1 life          (LIFECOUNT += 0x100)
--   M  +1 Aku Aku mask  (HEALTH += 0x100)
--   N  +10 Wumpa fruit  (FRUITCOUNT += 0xA00)   (not F: F is BizHawk frame advance)
--   O  open every node  (LEVELSUNLOCKED = 31)
--   G  toggle Green Gem  (ITEMPOOL1 bit 12)
--   Y  toggle Yellow Gem (ITEMPOOL1 bit 29)

memory.usememorydomain("MainRAM")

local function find_id()
  for _, id in ipairs({"SCUS_949.00", "SCUS-94900", "SCUS_94900"}) do
    local first = id:byte(1)
    for addr = 0, 0x1FFFFF - #id do
      if memory.read_u8(addr) == first then
        local ok = true
        for i = 2, #id do
          if memory.read_u8(addr + i - 1) ~= id:byte(i) then ok = false break end
        end
        if ok then console.log(string.format("found %s at MainRAM 0x%06X", id, addr)) end
      end
    end
  end
  console.log("disc ID search done")
end
find_id()

local actions = {
  U = function()
    memory.write_u32_le(0x061948, 5)
    memory.write_u32_le(0x0619B0, 0x3F)
  end,
  L = function() memory.write_u32_le(0x0618EC, memory.read_u32_le(0x0618EC) + 0x100) end,
  M = function() memory.write_u32_le(0x0618F0, memory.read_u32_le(0x0618F0) + 0x100) end,
  O = function()
    memory.write_u32_le(0x061948, 31)
    memory.write_u32_le(0x0619B0, 0xFFFFFFFF)
  end,
  G = function() memory.write_u32_le(0x061988, memory.read_u32_le(0x061988) ~ (1 << 12)) end,
  Y = function() memory.write_u32_le(0x061988, memory.read_u32_le(0x061988) ~ (1 << 29)) end,
  N = function() memory.write_u32_le(0x0618F4, memory.read_u32_le(0x0618F4) + 0xA00) end,
}
local held = {}
while true do
  local keys = input.get()
  for key, action in pairs(actions) do
    if keys[key] and not held[key] then
      action()
      console.log(string.format("[%d] poke %s", emu.framecount(), key))
    end
    held[key] = keys[key] == true
  end
  emu.frameadvance()
end
