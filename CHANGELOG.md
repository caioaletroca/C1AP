# Changelog

## Unreleased

- New *No Lives Trap* (like C2AP's) and *Trap Chance* option (0-100, default 0): the next level is played with 0
  lives, then the lives come back on the map (a game over forfeits them).
- Death Link now sends every death: it watches the game's respawn counter (`0x800618A0`) instead of
  `DEATHCOUNT`, which resets at every checkpoint. Receiving deaths is still not supported.

## 0.1.0 (2026-11-22)

- World: level completes, gems and keys as checks; Map Progress, colored gems, keys, clear gems and filler as items.
- Options: goal (cortex / all_gems), level shuffle, gem checks, starting nodes, death link (not reliable yet).
- BizHawk client: level shuffle, checks, items, map progress, keys and filler, all verified live in BizHawk
  (see `tools/VERIFY.md`).
- Gems follow map nodes: the check counts for the level played; colored-node bits are held until their check.
- Universal Tracker support through slot data.
