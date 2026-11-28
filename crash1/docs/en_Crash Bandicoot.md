# Crash Bandicoot

## What does randomization do to this game?

- **Map progress** is an item. You start with a few map nodes open; every *Map Progress* item opens the next one.
- **Level shuffle** (on by default) changes which level each map node leads to. Dr. N. Cortex always stays at the
  end, two bosses are never next to each other, and no boss sits on a node that is open from the start.
- **Colored gems** (Green, Orange, Blue, Red, Purple, Yellow) are items. Their gem paths only appear once you
  receive them, wherever they were found.
- **Keys** to *Whole Hog* and *Fumbling in the Dark* are items.
- Leftover slots are filled with extra lives, Aku Aku masks and Wumpa fruit. Extra lives and Wumpa fruit arrive
  right away, even in the middle of a level; Aku Aku masks wait until you are back on the map. With *Trap Chance*, some of them are
  *No Lives Traps* instead: you play your next level with 0 lives (one death is a game over). Back on the map you
  get your lives back, plus any you picked up; a game over ends the trap without giving them back.

## What is the goal?

Defeat Dr. N. Cortex (`cortex`), or defeat him while holding all 26 gems (`all_gems`).

## What are the locations?

- Finishing each level and defeating each boss.
- Each level's gem (20 clear, 6 colored), when *Gem Checks* is on.
- Each of the two keys (the Cortex bonus rounds in Jaws of Darkness and Sunset Vista).
- With *Bonus Round Checks* (on by default): reaching each Tawna and Brio bonus round, by collecting the three tokens
  of that kind in a level (19 checks).
- With *Box Checks*: breaking 25%, 50% and 75% (`quarters`) or 50% (`half`) of each level's boxes. Boxes count only in
  the level you break them in, and dying takes back the ones broken since the last checkpoint, as in the game. The 75%
  milestone of a level with a gem path may need that path's colored gem.
- With *Life Count Checks*: reaching each chosen number of lives (extra lives from the multiworld count). A higher
  count is expected later in the game: about one more map node for every 3 lives.

## What does another world's item look like in Crash Bandicoot?

The game shows nothing special. The item is sent as soon as the client sees the check.

## When the player receives an item, what happens?

Colored gems and keys appear in your inventory right away; a gem path shows up the next time you enter the
level (the game only checks gems when a level loads). Map progress takes effect the next time you are on
the map. Extra lives and Wumpa fruit are added right away, in a level too (10 fruit at a time; reaching 100 gives a
life, as in the game). Aku Aku masks and traps are applied the next time you are on the map and carry into the next
level.

## Known limitations (v0.1)

- NTSC-U (SCUS-94900) only.
- Death Link only sends deaths: every time you die, the others die too. Received deaths are not applied yet.
- Gems belong to map nodes: the end screen shows the gem of the node you entered from, but the check counts for the
  level you played.
- The game itself does not show which shuffled level a node leads to until you enter it.
