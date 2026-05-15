# Bot Strategy Deep-Dive

## Architecture

`bot.py` is a single-file Python 3 bot with no external dependencies. It runs in the CodinGame I/O loop: read stdin, compute, print stdout.

The `Bot` class initializes once (parsing the map), then `turn()` is called each of the 300 game turns.

## Decision Flow (per troll, per turn)

```
1. DROP?          carrying items AND adjacent to own shack → DROP
2. HARVEST?       on a tree with fruits AND have capacity → HARVEST
3. CHOP?          on tree, late game (turn>200), wood value > fruit value → CHOP
4. MINE?          adjacent to iron cell, need iron, have chopPower → MINE
5. CARRYING?      carrying items, not near shack → MOVE toward shack
6. FIND TARGET    scoring function picks best tree/iron → MOVE toward it
7. FALLBACK       MOVE toward center of map
```

After all trolls get actions, `_consider_training()` checks if we can afford a new troll.

## Target Scoring

Each troll without a current task scores all fruit trees:

```
score = (harvestable_fruits + future_fruit_estimate) / round_trip_time

Bonuses:
  +2.0  if reachable this turn (distance ≤ speed)
  +0.2  if closer to us than opponent (manhattan)
  +0.1  if tree is near water (faster growth)
  ×0.7  per troll already targeting this tree (spread factor)
```

Round-trip time = `(distance_to_tree / speed) + 1 + (distance_to_shack / speed) + 1`

Iron cells scored as `3.0 / (distance / speed)` when iron inventory < 4.

## Training Logic

Tries configs in order until one is affordable. Configs differ by game phase:

| Phase | Turns | Config priorities | Rationale |
|-------|-------|-------------------|-----------|
| Early | 1-20 | (1,1,1,0), (2,1,1,0), (1,2,1,0), (1,1,2,0), (1,1,1,1) | Maximize troll count; chopPower only if iron available |
| Mid | 21-80 | (2,2,1,0), (2,1,2,0), (1,2,2,0), (2,2,2,0) | Balanced stats for efficient harvesting loops |
| Late | 81+ | (2,2,2,1), (2,2,1,1), (2,1,2,1), (1,2,2,1) | Include chopPower for late-game wood chopping |

Training cost formula: `base + stat²` for each of (PLUM→moveSpeed, LEMON→carryCapacity, APPLE→harvestPower, IRON→chopPower), where `base` = number of existing trolls.

Hard cap: no more than 8 trolls.

## Pathfinding

BFS is cached per cell. Shack cells are non-walkable but handled: trolls on the shack can pathfind to its walkable neighbors with distance=1.

Distance maps are computed lazily and cached in `_bfs_cache` for the entire game.

Shack neighbor cells are precomputed at init — these are the cells where `DROP` is valid (orthogonally adjacent to shack).

## Key Game Mechanics Used

- **DROP** requires being *adjacent* to shack (not on it). Trolls start on shack but can't walk back onto it.
- **HARVEST** on same cell as tree. Both players can harvest the same tree simultaneously; last fruit can duplicate.
- **CHOP** on same cell as tree. Deal `chopPower` damage to health. At health=0, tree yields `size` wood (capped by carry capacity). Wood = 4 points each.
- **MINE** from orthogonal adjacency to iron cell. Yields `chopPower` iron (capped by carry capacity). Iron = 0 points, only used for training.
- **TRAIN** spawns troll on shack cell. Cannot train if shack cell is occupied by another troll.
- **PLANT** costs 1 fruit of that type, must be on grass with no existing tree.
- Turn order: Move → Harvest → Plant → Chop → Pick → Train → Drop → Mine → Grow. This means you can MOVE then HARVEST in same turn with `;` separator.

## What We Don't Do (Yet)

These are known gaps — prime improvement areas:

1. **PLANT**: Never plants new trees. Early fruit investment → long-term fruit production is likely worth it on empty good cells near our shack.

2. **PICK**: Never picks items from shack. Useful for ferrying seeds (fruits) to strategic planting locations.

3. **No simulation/prediction**: We don't predict what trees will look like in N turns (cooldown tracking). A tree with `cd=1` near our troll might produce fruit right as we arrive — should factor into target scores.

4. **Opponent modeling**: We track opponent distance only via manhattan from their shack, not their actual troll positions. We don't predict which trees they'll contest.

5. **No coordinated multi-troll harvesting**: When two trolls target the same tree, we only apply a 0.7 penalty, but we don't model the actual benefit of duplicate harvesting (the "last fruit duplicates" mechanic).

6. **Late-game chopping is primitive**: We only chop after turn 200, and only when on a tree. We don't send trolls specifically to chop valuable trees. Chopping a size-4 tree yields 4 wood = 16 points, which is massive.

7. **Iron mining threshold is static**: We mine when iron < 4 regardless of whether we actually have the other resources to train.

8. **Training configs are hardcoded**: We try configs in order, not based on what resources we have. Should optimize config selection based on current inventory.

9. **Movement target is just coordinate, not actual path**: We pass `(x, y)` to `MOVE` and let the engine pathfind. This means we can't specify optimal intermediate waypoints for multi-cell moves with speed > 1.

10. **No awareness of map terrain for target selection**: We use BFS distances but don't account for water adjacency making trees more valuable (only a 0.1 score bonus instead of modeling actual growth rates).

## Score Analysis

Against the example bot (`MOVE 0 7 7` every turn):

| Metric | Value |
|--------|-------|
| Win rate | 100% (50 seeds tested) |
| Avg margin | ~83 points |
| Crashes | 0 |
| Typical score | 50-170 depending on seed |

Against itself (mirror match):
- P1 usually wins due to map asymmetry advantages (different initial fruit distribution near each shack)
- Scores typically 65-120

## Referee Source → Bot Implications

Key details confirmed from reading the Java source at `Troll-Farm/` and `/tmp/pi-github-repos/eulerscheZahl/Troll-Farm/`:

- **Map generation**: Symmetric (mirrored). Player 0 shack in left half, Player 1 in right half. Map is validated so both shacks are reachable and not too far apart.
- **Stall detection**: Game ends early if no trees exist for 10 consecutive turns, or if both players are stuck (no carryable resources and no items in shack).
- **Movement collision**: Same-team trolls can't overlap. Movement is processed simultaneously — the engine resolves collisions by checking frequency of target cells and circular swaps.
- **Harvest sharing**: When two trolls (even opposing) harvest the same tree, they alternate taking 1 fruit at a time. The last fruit can be **duplicated**, so both trolls get it. This means contested trees are actually beneficial!
- **Chop sharing**: Same as harvest — both trolls chop simultaneously, and the last unit of wood can duplicate.
- **Training cost**: `base = number_of_existing_trolls`. First troll costs (0+1, 0+1, 0+1, 0+0) = (1, 1, 1, 0) because you start with 1 troll and hire costs are `existing + stat²`.
- **Initial troll**: Starts with stats (1, 1, 1, 1) in league 3 — that's speed=1, carry=1, harvest=1, chop=1.
- **Initial resources**: Random 2-10 of each fruit type per player, plus 2-10 iron in league 3.
- **Shack cell**: Trolls spawn there but can't walk back onto it after leaving. DROP works when orthogonally adjacent.