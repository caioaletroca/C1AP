-- C1AP RAM watch for BizHawk (PSX, NTSC-U SCUS-94900).
-- Tools > Lua Console > open this script. It draws the values the client relies on and logs every change,
-- so you can play through the checks in tools/VERIFY.md and compare.

local G = {
  {"LEVEL",          0x06188C},
  {"GAMESTATE",      0x0618D0},
  {"CURRENTLEVEL",   0x0618DC},
  {"LIFECOUNT",      0x0618EC},
  {"HEALTH",         0x0618F0},
  {"FRUITCOUNT",     0x0618F4},
  {"LEVELCOUNT",     0x061944},
  {"LEVELSUNLOCKED", 0x061948},
  {"ITEMPOOL1",      0x061988},
  {"ITEMPOOL2",      0x0619AC},
  {"MAPLEVELLINKS",  0x0619B0},
  {"MAPKEYLINKS",    0x0619B8},
  {"DEATHCOUNT",     0x061A3C},
  {"cur_lid",        0x056710},
  {"next_lid",       0x056714},
}

memory.usememorydomain("MainRAM")
local last = {}

while true do
  local y = 10
  for _, entry in ipairs(G) do
    local name, addr = entry[1], entry[2]
    local value = memory.read_u32_le(addr)
    gui.text(10, y, string.format("%-15s %08X", name, value))
    y = y + 14
    if last[name] ~= nil and last[name] ~= value then
      local changed = ""
      if name == "ITEMPOOL1" or name == "ITEMPOOL2" then
        local diff = last[name] ~ value
        for b = 0, 31 do
          if (diff >> b) & 1 == 1 then changed = changed .. string.format(" bit%d->%d", b, (value >> b) & 1) end
        end
      end
      console.log(string.format("[%d] %s %08X -> %08X%s", emu.framecount(), name, last[name], value, changed))
    end
    last[name] = value
  end
  emu.frameadvance()
end
