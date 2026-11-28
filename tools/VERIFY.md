# Address verification (milestone M0)

Every address in `crash1/ram.py` marked `VERIFY` comes from the decompilation and GOOL dumps, not from a
running game. Before C1AP can be played, each item below needs a short BizHawk test. Record the result
(✅ / ❌ + what you saw) in the table and fix `ram.py` where needed.

Setup: BizHawk 2.9.1+, NTSC-U disc (SCUS-94900), `Tools > Lua Console`, open `tools/c1ap_ram_watch.lua`.
The script draws every watched word and logs each change with the frame number.

| # | Test | Expect | Result |
|---|---|---|---|
| 1 | `validate_rom`: in the Lua console run `memory.usememorydomain("MainRAM")` and search the first 128 KB for `SCUS_949.00` (Tools > Hex Editor > Find) | string found while in game | |
| 2 | Enter a level from the map | `LEVEL` and `cur_lid` become the level ID listed in `crash1/data.py`; `CURRENTLEVEL` becomes the map node | |
| 3 | On the map, freeze nothing; select node 1 and, the moment `next_lid` changes, poke `next_lid` to `0x0E` (Boulders) | Boulders loads instead of N. Sanity Beach (**this is what level shuffle needs**) | |
| 4 | Finish the level from test 3 | Map returns to node 1 (not node 4); note `CURRENTLEVEL` | |
| 5 | Poke `LEVELSUNLOCKED` to 5 on the map, leave and re-enter the map (or enter/exit a level) | nodes 1–5 reachable, 6+ not | |
| 6 | Finish a level normally | `LEVEL` goes level → (0x2D?) → 0x19 with `GAMESTATE` 0x100; no 0x200/0x300 | |
| 7 | Lose all lives in a level | `GAMESTATE` passes through 0x200/0x300 before the map | |
| 8 | Collect a clear gem | exactly one new `ITEMPOOL1`/`ITEMPOOL2` bit, logged with `bitN->1`; write down level → bit | |
| 9 | Collect the Green Gem in The Lost City | `ITEMPOOL1` bit 12; Blue in Toxic Waste: bit 21 or 23? | |
| 10 | Clear `ITEMPOOL1` bit 12 while in Jungle Rollers | green gem path platform does not appear | |
| 11 | Get the Sunset Vista key (Cortex bonus) | `ITEMPOOL2` bit 20 | |
| 12 | Die once | `DEATHCOUNT` +1 | |
| 13 | Poke `LIFECOUNT`, `HEALTH`, `FRUITCOUNT` += 0x100 | +1 life / +1 mask / +1 fruit on HUD | |
| 14 | Beat Cortex | `LEVEL` becomes 0x39 | |
| 15 | Sunset Vista is node 16 and Slippery Climb node 24 on NTSC-U | — | |
| 16 | Is there a level with no gem besides bosses? (assumed The Great Hall) | — | |

If test 3 fails (the engine already read the level ID before the client could write it), level shuffle
needs another approach (a GOOL patch of the map script) and `level_shuffle` must default to off until then.

## Results log

**Round 2 (N. Sanity Beach, new game, no death):**
- `cur_lid` is the plain level ID (`LEVEL` holds it << 8). Lives/masks/fruit are << 8 and only update at level end.
- `GAMESTATE`: 0 on the map, 0x100 in a level, **0x500 the moment the level is won**, 0x300 on the normal exit to
  the map (not a game over).
- `next_lid` is -1 when idle and holds the level ID for only ~3 frames while loading. The level end screen is 0x2D.
- `LEVELSUNLOCKED` +1 when winning the furthest level; the map rebuilds `MAPLEVELLINKS` from it on entry.
- N. Sanity Beach gem = `ITEMPOOL1` bit 1, awarded on the level end screen.

**Round 3 (shuffle):** ✅ swapping `next_lid` 09 → 0E during the map's request loads Boulders; ✅ writing
`next_lid` = 0E while idle on the map loads Boulders.

**Round 4:** ✅ late swap (asking for 0E 5 frames after N. Sanity Beach started loading) loads Boulders, no
glitches; ✅ after the shuffled level the map advances from the node that was entered; ✅ `CURRENTLEVEL` is set on
the frame the node is selected. Level won without a gem: 0x100 → **0x300** (no 0x500). Game over: **0x200** → map;
continue reloads the save (`LEVELSUNLOCKED`, `CURRENTLEVEL`, lives revert). ❌ `DEATHCOUNT` (<< 8) rose once over
several deaths and resets on exit: not usable for Death Link.

**Round 5:** ✅ `LEVELSUNLOCKED` = 5 + `MAPLEVELLINKS` = 0x3F on the map opens nodes 1–5 at once. ✅ Disc ID in
MainRAM at 0x00928C, 0x009E19, 0x00B8B7 (`SCUS_949.00`) and 0x010E8A (`SCUS-94900`), inside the client's 128 KB
scan. ❓ Poking lives +0x100, health +0x100 and fruit +0xA00 on the map, then the emulator paused: F is BizHawk's frame-advance hotkey, not a game crash (fruit moved to N).

**Round 5b:** ✅ lives +0x100, health +0x100 and fruit +0xA00 written on the map carry into the next level
(5 lives, Aku Aku, 10 fruit). Filler on the map works.

**Round 6:** ✅ `O` (`LEVELSUNLOCKED` 31, `MAPLEVELLINKS` 0xFFFFFFFF) opens every node. ✅ Green (bit 12, Jungle
Rollers path) and Yellow (bit 29, The Great Gate path) set on the map make the gem path appear. ⚠️ Setting a colored
gem bit **inside** a level does nothing until the level is reloaded: gem bits are read at level load.
✅ New `GAMESTATE` **0x400** = **quit from the pause menu** (The Great Gate, twice): 0x100 → 0x400 → map, lives/fruit
still sync. Never a completion.

**Round 7:** ✅ winning an already-unlocked level (all nodes open, N. Sanity Beach, died once, no gem): 0x100 →
0x500 → level end (0x2D) → 0x300 → map. 0x500 means "go to the level end screen", gem or not.

**First connected run:** ✅ shuffle, checks, items, key bit (`ITEMPOOL2` bit 20 + `MAPKEYLINKS`), resync after
loading an old save state, bonus round (0x24, returns through `next_lid` = -2) all work. ❌→✅ the 0x300 exit shows
with the level's ID for only 1-2 frames (missed Road to Nowhere); now also counted with the map's ID.
**Gems belong to nodes:** Toxic Waste on node 4 awarded `ITEMPOOL1` bit 4 (a clear gem), not Blue. Gem bit = node
(1-29 minus boss nodes; secret nodes 40/50 → `ITEMPOOL2` bits 8/18). Blue = bit 21 (node 21).
❓ Does a level on a boss node (no gem bit) award anything? → `c1ap_boss_node_test.lua`.
✅ **Boss node:** N. Sanity Beach on node 6 (Papu Papu's) awarded `ITEMPOOL1` bit 6 → every node has a gem slot,
bit = node. Gem levels may go on any node.

**Colored node (seed 1):** ✅ N. Sanity Beach on node 12 (Green's node), Green not owned: the game set `ITEMPOOL1`
bit 12 on the level end screen, the client sent "N. Sanity Beach - Gem" and cleared the bit 4 frames later (no Green
path without the item). Colored-node masking works live.

**Death Link:** ❌ byte search for in-level lives found only object fields (they matched lives in N. Sanity Beach
by chance, then drifted in Jungle Rollers). ✅ `RESPAWNCOUNT` 0x800618A0 (from the decompilation): Jungle Rollers,
two TNT deaths, checkpoint, two more deaths → 0 → 0x100 → 0x200 → 0x300 → 0x400. `DEATHCOUNT` stayed 0 for the first
two deaths: it counts deaths since the last checkpoint. Tools: `c1ap_lives_search.lua`, `c1ap_lives_watch.lua`.

**Round 8 (v0.3 Tier 1, one batch).** Everything below came from the decompilation and a community table, not from
the game. One seed tests it all; the client log's `[C1AP verify]` lines carry the data, so paste the whole client log.

Seed YAML: `box_checks: quarters`, `bonus_round_checks: true`, `life_count_checks: ["5", "10"]`,
`level_shuffle: false`, `starting_nodes: 10`, `trap_chance: 0`.

| # | Do | Expect |
|---|---|---|
| 8.1 | Enter N. Sanity Beach | log `Crash object 0x80...... in level 0x09: lives 4, fruit 0, ... plausible True` with lives/fruit matching the HUD |
| 8.2 | In the level, `/send <slot> Extra Life` from another client (or `!getitem Extra Life`) | HUD lives +1 right away; log `Extra Life applied in the level.` |
| 8.3 | Same with `Wumpa Fruit Bundle` (twice, then pick fruit until near 100) | fruit +10 on the HUD; crossing 100 gives a life |
| 8.4 | `!getitem Aku Aku Mask` in the level | nothing until the map; the next level starts with Aku Aku |
| 8.5 | Break 13 boxes in N. Sanity Beach (49 boxes: 13 / 25 / 37) | `25% Boxes` check at the 13th box, then 50% and 75% |
| 8.6 | Finish N. Sanity Beach with every box | log `Boxes: N. Sanity Beach won with BOX_COUNT 49 (table total 49 ...)` |
| 8.7 | Get 3 Tawna tokens in Jungle Rollers | `Jungle Rollers - Tawna Bonus` on entering the bonus; log line with the bonus level ID and tokens |
| 8.8 | Rolling Stones: get the 3 Brio tokens (and Tawna's if you can) | `Rolling Stones - Brio Bonus` (and Tawna) checks; note the level IDs in the log |
| 8.9 | Reach 5, then 10 lives (in a level and on the map) | `Reach 5 Lives` / `Reach 10 Lives` when the HUD shows it |
| 8.10 | Die in a level after 8.2 | lives drop by one as usual (the field is the real counter) |

Results (BizHawk 2.9.1, NymaShock, from the S1 save state):

> Save states mislead the client: it only sees what happens while it watches. S2 (inside Rolling Stones' Brio
> bonus, which opens at the end of the level) gave `won with up to 5 boxes` for a level whose earlier boxes the
> client never saw. Box totals in the log are only data from runs played straight from the level start.

- ✅ 8.1 Crash object 0x8009E3D4 in N. Sanity Beach (player 0x80090150), counters match the HUD. Each level and each
  bonus round has its own object; CRASH_PTR reads 0 for a moment while a bonus round loads.
- ✅ 8.2 Extra Life in a level. ✅ 8.3 Wumpa Fruit Bundle in a level, also past 100 (life +1, fruit wraps).
- ✅ 8.4 Aku Aku Mask waits for the map. ✅ 8.5 25/50/75% boxes (N. Sanity Beach, Jungle Rollers, Rolling Stones).
- ✅ 8.6 N. Sanity Beach: 49 boxes with the gem, as in the table. The won state (0x500) can be missed with lag, so the
  note also fires on the 0x300 exit.
- ✅ 8.7 Jungle Rollers Tawna bonus: level ID 0x24, tokens Tawna 3.
- ✅ 8.8 Rolling Stones: Tawna bonus 0x33 (tokens Tawna 3, Brio 2), Brio bonus 0x25. Fixed: the second bonus round
  of a level visit was ignored.
- ✅ 8.11 Bonus round cleared (new seed `bonus_round_checks: reach_and_clear`, S2 = inside Rolling Stones' Brio
  bonus): dying → "left without clearing it", no check; finishing → `Rolling Stones - Brio Bonus Cleared`, and no
  Complete. The 0x300 was first seen with the level's ID (0x15), after the load back.
- ✅ 8.12 Jungle Rollers Tawna bonus, same seed from S1: dying → "left without clearing it"; finishing (after the
  save card) → `Tawna Bonus Cleared`, 0x300 first seen with the level's ID (0x0C); Complete only at the real end.
- ✅ 8.13 Client restarted in a level after an in-level Extra Life and Wumpa bundle: nothing applied twice (per-name
  applied counts). An Aku Aku Mask received in the level then waited for the map and gave the second mask.
- ✅ 8.14 Level shuffle (seed `round8c`, from S1): Jungle Rollers' node loaded Temple Ruins (0x1C) and its box
  check was `Temple Ruins - 25% Boxes`; Hog Wild's node loaded Boulders (0x0E); Upstream's node loaded Jungle Rollers
  (0x0C): its boxes, Tawna Bonus, Tawna Bonus Cleared and Complete all counted for Jungle Rollers.
- ✅ 8.15 Sunset Vista Cortex bonus (seed `round8d`, start_inventory 6 Map Progress, from S1): level ID 0x34
  (`counted as Cortex`); dying → "left without clearing it"; the key check `Sunset Vista - Key` was sent on picking up
  the key inside the bonus; finishing → "cleared (Cortex)" with no extra check and no false Complete.
- ✅ 8.16 The Lost City with the gem (seed `round8d`): `won with up to 26 boxes`, then `The Lost City - Gem`. The game's
  table (26) is right; the wikis' 31 is not the counter. Also: Brio bonus then Tawna bonus in one visit, both
  counted (Brio cleared, Tawna left without clearing).
- ✅ 8.9 Reach 5 / 10 Lives in a level. ✅ 8.10 dying takes a life as usual.
- Fixed: leaving a bonus round shows 0x300/0x500 with the level's own ID before play resumes, which sent the level's
  Complete. Wins now count only after play resumes in the level.

**No Lives Trap (trap test seed):** ✅ `/send Crash No Lives Trap` on the map → lives 0 for the next level
(N. Sanity Beach), back on the map → "No Lives Trap over: 4 lives". A second trap armed again right after.
✅ Game over with the second trap armed: died once with 0 lives → Game Over → Continue → 4 lives (vanilla), trap
cleared without restoring.

**Round 9 (v0.4 timed traps).** New addresses from kdecomp, not yet seen in a running game:
`CAM_ROT_Z` 0x80057878, `Pad_Update` 0x800167A4 with one `jal PadRead` (0x0C00F918), the cave at 0x8000F400
(kernel RAM, assumed unused) and the pause object 0x80061964.

Part A, no client: `tools/c1ap_trap_test.lua` in the Lua Console (keys H J L M U, all free in BizHawk here).

| # | Test | Expect | Result |
|---|---|---|---|
| 9.1 | Load the script | console: `cave survey (start): all zero` and `jal PadRead found at 0x8001xxxx (original)` | |
| 9.2 | H in a level, walk around, die, enter a bonus | camera upside down; note if `game reset the camera roll` is logged (and when) | |
| 9.3 | H on the map | map upside down too (the client only flips in levels) | |
| 9.4 | L in a level | left walks right and right walks left; text shows `jal HOOKED`, `cave ok` | |
| 9.5 | M in a level | X spins, Square and Circle jump; L+M together both apply | |
| 9.6 | U | everything normal; `restored jal`; no crash or freeze | |
| 9.7 | J in a level with lives | lives 0 on the HUD for 20 s, `banked N lives`, then `N lives back` | |
| 9.8 | J, then die | game over (lives were 0) | |
| 9.9 | Pause during any trap | write down `pause` value paused and unpaused (for pause detection) | |
| 9.10 | Leave the script running 5+ minutes untouched | no `cave survey (periodic)` line (cave stays zero) | |

Part B, with the client (seed with `trap_chance` > 0): `!getitem <trap>` in the client for each trap.

| # | Test | Expect | Result |
|---|---|---|---|
| 9.11 | `Upside Down Trap` on the map, then enter a level | normal map; flipped in the level; normal again after 20 s of play | |
| 9.12 | `Reverse Controls Trap` and `Button Swap Trap` in a level | both apply; each ends after its time; `restored` the game | |
| 9.13 | `No Lives Trap` in a level | lives 0; back when it ends: `No Lives Trap over: N lives back.` | |
| 9.14 | Same trap twice | time adds up (40 s) | |
| 9.15 | Restart the client mid-trap | the trap goes on with the time left; no lives lost or doubled | |
