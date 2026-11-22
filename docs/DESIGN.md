# C1AP — Crash Bandicoot (PS1) Archipelago design

Status: **draft v0.1**, 2026-11-21. No code yet. This moves into the `C1AP` repo when it's created.
Related: [CRASH1_RAM_NOTES.md](CRASH1_RAM_NOTES.md) (addresses), [AP_DEV_RESEARCH.md](AP_DEV_RESEARCH.md)
(standards, tooling).

Legend: ✅ decided · 🔧 implementation detail (can change) · ❓ game fact to verify in BizHawk / goocdump

## 1. Identity and platform

| | |
|---|---|
| Repo | `C1AP` (user's GitHub), MIT |
| AP game name | `Crash Bandicoot` |
| Package / file | `crash1` / `crash1.apworld` |
| Game version | NTSC-U **SCUS-94900** only. The client refuses anything else |
| Emulator | **BizHawk**, PSX core NymaShock. Target 2.9.1+, tested on 2.11.x |
| Client | Python `BizHawkClient` in the apworld (`system = "PSX"`) |
| Archipelago | `minimum_ap_version: "0.6.8"` |
| Game modification | RAM reads/writes only. No disc patch, no ROM needed to generate |

## 2. Scope

**v0.1 (MVP):** everything in this document.

**Deferred** (not designed here):
- Wumpa and life checks (C2AP style).
- Gating levels by clear-gem count; it needs an in-game way to show the player the requirement.
- Traps.
- A DuckStation client.
- PopTracker pack.
- PAL/NTSC-J.

## 3. Game structure (what we're randomizing)

Crash 1's progression is **linear**:
- A single counter, `LEVELSUNLOCKED`, decides how far along the 3-island map you can walk.
- Bosses sit between stretches of levels.
- Colored gems open **gem paths** inside other levels, needed for some box/gem routes.
- 2 keys, won in Cortex bonus rounds, open the 2 **secret levels**.

### Level list (map order)

**Sources:**
- Node order: the map script `IsldC.gooc` (`MapSetLevelParams`, nodes 1–31) in
  [goocdump](https://github.com/ManDude/goocdump). That dump is **NTSC-J**.
- Level codes: `goolstdlib.gooc` (`LEVEL_*`). These are the game's own NSF level codes; the
  numeric IDs are still to confirm against the cbhacks table.
- ⚠️ NTSC-J **swaps Sunset Vista and Slippery Climb** (J: node 16 = Slippery Climb, node 24 =
  Sunset Vista). The US order below puts them back. Confirm on first boot ❓.
  goolstdlib's note that NTSC-J swaps gems 13 and 22 fits a two-level swap.
- `goolstdlib` also defines **Stormy Ascent** (`L'y'`), a cut level with no map node.
  Exclude it.

| Node | Island | Level | Code | Type |
|---|---|---|---|---|
| 1 | 1 | N. Sanity Beach | `9` | level (start) |
| 2 | 1 | Jungle Rollers | `c` | level |
| 3 | 1 | The Great Gate | `i` | level |
| 4 | 1 | Boulders | `e` | level |
| 5 | 1 | Upstream | `f` | level |
| 6 | 1 | Papu Papu | `a` | **boss** |
| 7 | 1 | Rolling Stones | `l` | level |
| 8 | 1 | Hog Wild | `h` | level |
| 9 | 1 | Native Fortress | `q` | level |
| 10 | 2 | Up the Creek | `o` | level |
| 11 | 2 | Ripper Roo | `n` | **boss** |
| 12 | 2 | The Lost City | `w` | level |
| 13 | 2 | Temple Ruins | `s` | level |
| 14 | 2 | Road to Nowhere | `k` | level |
| 15 | 2 | Boulder Dash | `j` | level (**Whole Hog branch, Key 2**) |
| 16 | 2 | Sunset Vista (US) ❓ | `z` | level |
| 17 | 2 | Koala Kong | `x` | **boss** |
| 18 | 3 | Heavy Machinery | `6` | level |
| 19 | 3 | Cortex Power | `3` | level |
| 20 | 3 | Generator Room | `5` | level |
| 21 | 3 | Toxic Waste | `7` | level |
| 22 | 3 | Pinstripe | `8` | **boss** |
| 23 | 3 | The High Road | `m` | level |
| 24 | 3 | Slippery Climb (US) ❓ | `K` | level |
| 25 | 3 | Lights Out | `E` | level (**Fumbling branch, Key 1**) |
| 26 | 3 | Jaws of Darkness | `t` | level |
| 27 | 3 | Castle Machinery | `T` | level |
| 28 | 3 | Dr. N. Brio | `r` | **boss** |
| 29 | 3 | The Lab | `F` | level |
| 30 | 3 | The Great Hall | `I` | level |
| 31 | 3 | Dr. N. Cortex | `v` | **final boss** |
| 50 | (from 15) | Whole Hog | `u` | **secret**: needs **Key 2** |
| 40 | (from 25) | Fumbling in the Dark | `G` | **secret**: needs **Key 1** |

Totals: 31 nodes = **25 levels + 6 bosses**, plus **2 secret levels**.

### Keys and secret levels (from the `IsldC.gooc` map input code)
- At node **15 (Boulder Dash)**, pressing up goes to node 50, **Whole Hog**, but only
  `if (ITEM_KEY2)`. `ITEM_KEY2` = `ITEMPOOL2` bit 20, which goolstdlib comments as the
  "sunset vista key".
- At node **25 (Lights Out)**, pressing up goes to node 40, **Fumbling in the Dark**, but only
  `if (ITEM_KEY1)`. `ITEM_KEY1` = `ITEMPOOL2` bit 10, the "jaws of darkness key".
- So in vanilla, **Key 2 comes from Sunset Vista's Cortex bonus round** and **Key 1 from
  Jaws of Darkness's** ❓. That comes from the comments; confirm in game.
- Normal map movement is blocked while on a branch path (`IslandTargetPath != 21/31`). Each
  secret level only connects back to its parent node.
- Confirming a node runs `CURRENTLEVEL = IslandProgress; loadlevel(IslandLevel)`. That's the
  exact place the level shuffle has to intercept (§7).

### Colored gems
**Sources:**
- Where each gem is earned: [The Escapist](https://www.escapistmagazine.com/where-to-find-every-crash-bandicoot-1-gem-color-in-the-n-sane-trilogy/)
  (N. Sane Trilogy, which keeps the US layout).
- Which levels have each gem's path: Nintendo Life's
  [coloured gems guide](https://www.nintendolife.com/news/2018/07/guide_crash_bandicoot_n_sane_trilogy_-_coloured_gems_secret_warps_coco_and_keys_walkthrough)
  table, as quoted in search results (the page blocks direct fetches).
- Bits: goolstdlib's NTSC-U/PAL aliases.

⚠️ These are N. Sane Trilogy sources. The remake changed how *clear* gems are earned, but it
is not known to have moved colored gems. Confirm both columns on PS1 ❓.

| Gem | Earned in (node) | Its path appears in | `ITEMPOOL1` bit (US) |
|---|---|---|---|
| Green | The Lost City (12) | Jungle Rollers, Castle Machinery | 12 |
| Orange | Generator Room (20) | Upstream | 20 |
| Blue | Toxic Waste (21) | Rolling Stones, Cortex Power, Jaws of Darkness | 21 ❓ (the debug cheat in `IsldC` sets bit 23 instead) |
| Red | Slippery Climb (24) | Native Fortress, Road to Nowhere | 24 |
| Purple | Lights Out (25) | Boulder Dash | 25 |
| Yellow | The Lab (29) | The Great Gate, Lights Out (the "alternate exit" route) | 29 |

- Colored gems are won by **finishing the level without dying**, plus all boxes on PS1 ❓.
- Clear gems: 20 of them. That's one per remaining non-boss level, but 27 non-boss levels
  minus 6 colored-gem levels = 21, so **one level has no gem** (likely The Great Hall) ❓.
  The bit → level mapping for clear gems is still to confirm in game.

## 4. Locations (checks)

| Group | Count | Detected by (client) | Notes |
|---|---|---|---|
| **Level complete: `<level>`** | **32** = 30 nodes (25 levels + 5 bosses, not Cortex) + 2 secrets | `LEVELCOUNT`/progress rising, or a level → map transition after a win ❓ | Bosses included ✅ |
| **Gem: `<level>`** | 26 (clear + colored) | a new bit in `ITEMPOOL1`/`ITEMPOOL2` | **Option** `gem_checks` on/off ✅ |
| **Key: `<level>` Cortex Bonus** | 2 | `ITEMPOOL2` bits 10 and 20 | Always on ✅ |
| *Event:* Defeat Cortex | 1 (locked "Victory") | Cortex level won, or the ending state ❓ | Goal, not a check |

🔧 Location IDs: start at a base ID with one range per group (levels `+0..99`, gems
`+100..199`, keys `+200..209`). IDs are **fixed forever** once released.

## 5. Items

| Item | Class | Count | Effect in game |
|---|---|---|---|
| **Map Progress** | progression (progressive) | enough to reach node 31; see §5.1 | Client sets `LEVELSUNLOCKED` = starting value + number received |
| **Blue/Green/Orange/Red/Yellow/Purple Gem** ❓ colors | progression | 6 (only when `gem_checks` is on; otherwise filler or left out) | Client sets that gem's bit → the gem path opens |
| **Key 1, Key 2** (named by the secret level each opens) | progression | 2 | Client sets the `ITEMPOOL2` key bit → the secret level opens |
| **Clear Gem** | filler (useful) | the rest of the 26 when gem checks are on | Client sets the next unowned clear-gem bit (counts toward 100% and health bonus) |
| **Extra Life / Aku Aku Mask / Wumpa** | filler | padding | `LIFECOUNT` +1 / `HEALTH` +1 (capped) / `FRUITCOUNT` +10 |

### 5.1 Pool math and the restrictive start (important)

- With gem checks **off**: about 32 level checks plus 2 key checks, against about 30 Map
  Progress items plus 2 keys. The pool fits, but **sphere 1 would be a single check**
  (finish node 1). That causes fill failures in solo seeds and dead time in multiworlds.
- **Fix ✅ (proposed): option `starting_map_progress`** (default 3, range 1–10). You start
  with nodes 1..N open, and the Map Progress items in the pool shrink to match.
- Also **never put a boss in nodes 1..N** (see §7).
- Filler makes up any gap between items and locations. If items outnumber locations
  (very small option sets), we cut filler first, never progression.

## 6. Logic

### 6.1 Regions (🔧 rule builder)
- `Menu` → `Map` → one region per **map node** k (1..31) with rule `Has("Map Progress", k − start)`.
- Each node region holds the checks of the **level assigned to that node** after the shuffle.
  **Logic follows the level, not the node.**
- Secret level regions:
  - Whole Hog = reach **node 15** and `Has("Key 2")`.
  - Fumbling in the Dark = reach **node 25** and `Has("Key 1")`.
  - The branch belongs to the **node**, not the level (the map script checks `IslandProgress`),
    so it doesn't move with the shuffle. Secret levels aren't shuffled in v0.1.
- Cortex node 31 → event location "Defeat Cortex" holding the locked `Victory`.

### 6.2 Level and key checks
- "Level complete": reach the node. No extra items needed in v0.1.
- "Key": reach the level that holds that Cortex bonus round ❓. If those bonus tokens only
  appear on a gem path, the key also needs that colored gem ❓.

### 6.3 Gem checks (only when `gem_checks` is on)
Rule: a level's gem check needs its node reached, **plus every colored gem whose path is in
that level**. In Crash 1, the boxes on a gem path count toward "all boxes" ❓ (confirm per
level).

| Level | Gem it gives | Extra items needed |
|---|---|---|
| Jungle Rollers | clear | **Green** |
| The Great Gate | clear | **Yellow** |
| Upstream | clear | **Orange** |
| Rolling Stones | clear | **Blue** |
| Native Fortress | clear | **Red** |
| Road to Nowhere | clear | **Red** |
| Boulder Dash | clear | **Purple** |
| Cortex Power | clear | **Blue** |
| Jaws of Darkness | clear | **Blue** |
| Castle Machinery | clear | **Green** |
| Lights Out | **Purple** (colored) | **Yellow** ❓ (Yellow path = alternate exit; may not be needed for the gem) |
| The Lost City | **Green** (colored) | — |
| Generator Room | **Orange** (colored) | — |
| Toxic Waste | **Blue** (colored) | — |
| Slippery Climb | **Red** (colored) | — |
| The Lab | **Yellow** (colored) | — |
| every other non-boss level (incl. Whole Hog, Fumbling) | clear | — (one level gives none ❓) |

Colored gems come late (most are on island 3) while their paths are on island 1. That
creates natural long-range dependencies, which make good Archipelago material.

The "all boxes without dying" difficulty isn't a logic item. It's player skill, which is
why the whole group can be turned off.

### 6.4 Goal options ✅
- `goal: cortex` (default): defeat Cortex.
- `goal: all_gems`: defeat Cortex **and** hold all 26 gems. Needs `gem_checks: on`;
  otherwise raise an `OptionError`.

## 7. Level-order shuffle ✅

**Option `level_shuffle`: off / on (default on).**

Rules:
1. **Dr. N. Cortex stays at node 31.**
2. Every other level **and boss** (Brio included) is shuffled across nodes 1–30.
3. **No two bosses on adjacent nodes**: at least one normal level between them.
4. **No boss inside the starting nodes** (1..`starting_map_progress`).
5. Secret levels keep their vanilla attachment (Whole Hog at node 15, Fumbling at node 25);
   they aren't shuffled in v0.1.

🔧 Algorithm: done by hand in `generate_early`, using `self.random`:
- Shuffle the 25 normal levels, then put the 5 non-Cortex bosses into gaps that satisfy
  rules 3–4. This works first time, with no retry loop.
- 25 levels give 24 inner gaps plus the end, which is plenty for 5 bosses, so it can't fail.
- The result goes into **slot data** as `level_order: [level_id × 31]`.

Client side:
- When the game is about to load the level at node k (`next_lid` = vanilla level of
  node k), rewrite `next_lid` to `level_order[k]` (Ape Escape style).
- On exit, make sure Crash is back on **node k** of the map, not at the vanilla node of
  the level just played ❓ (may need to fix `CURRENTLEVEL`/`PREVLEVEL`).

**Known UX gap:** the map still shows vanilla level names. v0.1 accepts this, and the client
shows "Node 7 → Hog Wild" in its text log. Fixing the names in-game is deferred.

## 8. Options (YAML)

| Option | Type | Default | |
|---|---|---|---|
| `goal` | choice: cortex / all_gems | cortex | §6.4 |
| `level_shuffle` | toggle | on | §7 |
| `gem_checks` | toggle | on | §4 |
| `starting_map_progress` | range 1–10 | 3 | §5.1 |
| `death_link` | DeathLink | off | §9.5 |
| `filler_weights` (later) | — | — | lives / masks / wumpa mix |

🔧 Ship option groups plus 2 presets: "Casual" (no gems, start 5) and "Full" (gems on, start 3).

## 9. Client behavior

### 9.1 Connection and game check
- `validate_rom`: read the boot ID string in RAM and accept only `SCUS-94900` ❓ (find its
  address, as Spyro 1 does with `BASCUS-94228SPYRO`).
- Wait until the game is in a safe state (`GAMESTATE` = playing or map) before writing anything.

### 9.2 Who owns which RAM
The client is the **authority** for progress values. Every poll, it rewrites them from
what AP says:
- `LEVELSUNLOCKED` (and `LEVELCOUNT` ❓) = start + Map Progress received.
- `ITEMPOOL1`/`ITEMPOOL2` (and their `SAVED…` copies) = gem and key bits **received as
  items**, plus nothing else.

### 9.3 Detecting checks without granting the item
1. Read the pools. Any bit set that we didn't grant = the player just earned that
   gem or key → **send the check**.
2. Immediately **clear that bit** again unless we've received it as an item (as C2AP and S2AP do).
3. For level completes: record the check on the transition, then restore `LEVELSUNLOCKED`
   to the item-driven value.

⚠️ The game may **recompute GEMCOUNT/KEYCOUNT and health bonus** from the pools at load
time, and its gem "award" cutscene state (`GAMESTATE 0x500`) may fight our writes.
Only use guarded writes, and write only during gameplay or map states ❓.

### 9.4 Resync and save states
- On connect, send every check the RAM shows. Most aren't visible after our writes, so
  we also keep the sent-checks list from the server (`checked_locations`).
- Store **"last received item index"** in free RAM ❓ (find an unused area; Spyro 1 uses
  `0x0F000`) so loading an old save state doesn't double-grant filler.
- The memory card or password save is irrelevant. The AP state is rebuilt from the server.

### 9.5 Death link
- **Send:** `RESPAWNCOUNT` (0x800618A0, +0x100 per respawn, 0 at level start) goes up within a level → send a
  death. (`DEATHCOUNT` resets at every checkpoint: it's the Aku Aku pity-mask counter.) ✅ verified in BizHawk.
- **Receive:** kill Crash. The method is ❓ (setting health/state, or a game event). If we
  can't make it reliable, v0.1 sends deaths only and says so in the docs.

### 9.6 Goal
On the Cortex win (state ❓), send `CLIENT_GOAL`.

## 10. Slot data
`{ "level_order": [...31 level ids], "starting_nodes": n, "gem_checks": 0|1, "goal": 0|1,
"death_link": 0|1, "world_version": "x.y.z" }`. This includes everything Universal Tracker
needs (`interpret_slot_data`).

## 11. Tests (CI)
- `WorldTestBase` defaults for: default options, every goal, gems off, shuffle off,
  start 1 and 10.
- Shuffle invariants over many seeds (unittest + `test.param`, not pytest marks):
  - Cortex is at node 31.
  - No adjacent bosses.
  - No boss in the starting nodes.
  - Every level appears exactly once.
- Logic: `assertAccessDependency` for gems behind colored-gem paths and secret levels behind keys.
- Before each release: fuzzer run with a failure rate under 1%.

## 12. Address checklist for BizHawk (priority order)

| # | What | Candidate | Status |
|---|---|---|---|
| 1 | Level about to load: rewriting it loads a different level | `next_lid` 0x80056714 | ❓ **blocks the shuffle** |
| 2 | Map unlock counter: writing it opens or closes nodes cleanly | `LEVELSUNLOCKED` 0x80061948 | GameShark-verified; behavior ❓ |
| 3 | Reliable "level won" signal | `LEVELCOUNT` 0x80061944 / transitions | ❓ |
| 4 | Gem/key bits and their exact bit → level mapping | `ITEMPOOL1/2` 0x80061988 / 0x800619AC | from goolstdlib; confirm |
| 5 | Return-to-map node after a shuffled level | `CURRENTLEVEL` 0x800618DC / `PREVLEVEL` 0x800619A8 | ❓ |
| 6 | Game state / safe-to-write states | `GAMESTATE` 0x800618D0 | values listed; confirm |
| 7 | Boot ID string for `validate_rom` | — | ❓ |
| 8 | Free RAM for client state | — | ❓ |
| 9 | Death detection, and a way to kill Crash | `RESPAWNCOUNT` 0x800618A0 ✅ / kill ❓ | ❓ |
| 10 | Confirm the US Sunset Vista/Slippery Climb order, colored gem table (§3), clear-gem bit → level map, which level has no gem | playtest + `GemsC.gooc` | tables filled from sources; confirm |

## 13. Milestones

| M | Deliverable | Done when |
|---|---|---|
| M0 | Address verification (§12 items 1–6) | Each has a short BizHawk test note in `tools/` |
| M1 | Repo scaffold plus a world that generates (no shuffle) | AP tests pass on Python 3.11–3.13 in CI |
| M2 | Client: checks + items + resync | A solo seed is playable from start to Cortex |
| M3 | Level shuffle (world + client) | Shuffle tests pass; a playthrough has no wrong map node |
| M4 | Death link, presets, docs, UT check, fuzzer | `v0.1.0` release on GitHub with `crash1.apworld` |

## 14. Open questions
1. The exact item counts follow from the ❓ level list; we'll fix them after M0.
2. Should colored gems also gate **level completes** (e.g. a level that needs a gem path
   to reach its exit)? Probably not in Crash 1 ❓.
3. Bonus rounds (Tawna/Brio) as checks? Not in v0.1; easy to add later (detect via `BONUSROUND`).
