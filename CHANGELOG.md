# Changelog

# [0.2.0](https://github.com/caioaletroca/C1AP/compare/v0.1.0...v0.2.0) (2026-11-22)


### Features

* Death Link sends every death, add No Lives Trap ([a8306d8](https://github.com/caioaletroca/C1AP/commit/a8306d84a0c6c1b24673c6c9fe138889919b8cdf))

## 0.1.0 (2026-11-22)

- World: level completes, gems and keys as checks; Map Progress, colored gems, keys, clear gems and filler as items.
- Options: goal (cortex / all_gems), level shuffle, gem checks, starting nodes, death link (not reliable yet).
- BizHawk client: level shuffle, checks, items, map progress, keys and filler, all verified live in BizHawk
  (see `tools/VERIFY.md`).
- Gems follow map nodes: the check counts for the level played; colored-node bits are held until their check.
- Universal Tracker support through slot data.
