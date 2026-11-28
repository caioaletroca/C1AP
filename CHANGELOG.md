# Changelog

# [0.3.0](https://github.com/caioaletroca/C1AP/compare/v0.2.0...v0.3.0) (2026-11-28)


### Bug Fixes

* Crash object pointer and bonus round exits (round 8) ([973d77a](https://github.com/caioaletroca/C1AP/commit/973d77af467374c94ecf91c9655fbb0d312b0a1b))
* The Lost City has 26 boxes (the game's own table) ([3c3ae7a](https://github.com/caioaletroca/C1AP/commit/3c3ae7ab51c969a4e6b7a48ff3bc3545a1c83185))


### Features

* bonus round cleared checks ([1b4b729](https://github.com/caioaletroca/C1AP/commit/1b4b729f9b92c7eb0e2980ab7a0ebccc354d262d))
* in-level filler, bonus round, box and life count checks ([e688dee](https://github.com/caioaletroca/C1AP/commit/e688dee17c0addc99671e9412def9fbdd3524db8))

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
