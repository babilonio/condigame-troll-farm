# Bot Strategy Deep-Dive

## Two Bot Versions

| File | Purpose | When to use |
|------|---------|-------------|
| `arena_bot.py` | **Arena submission** — our best bot | CodinGame arena, competitive play |
| `bot.py` | Configurable bot with `--config` flag | Self-play A/B testing, parameter tuning |

Both share the same core logic. `arena_bot.py` has additional features (combo actions, planting) and is the one to submit. `bot.py` reads parameters from JSON configs for iteration.

## Arena Bot Decision Flow (arena_bot.py)

Per troll, priority chain:

```
1. DROP               carrying AND near shack → DROP
   MOVE+DROP combo    carrying AND can reach shack neighbor this turn → MOVE+DROP
2. HARVEST            on tree with fruits AND have capacity → HARVEST
   MOVE+HARVEST combo have capacity AND can reach fruitful tree this turn → MOVE+HARVEST
3. PLANT              on grass+water cell near shack, carrying fruit, turn ≤ 80, planted < 2 → PLANT
4. CHOP               on tree, turn > 180, wood value exceeds remaining fruit potential
   CHOP aggressive    on tree, turn > 220, wood value > fruit count
5. MINE               adjacent to iron, need iron, have chopPower → MINE
6. FIND TARGET        scoring function picks best tree/iron → MOVE
7. FALLBACK           MOVE toward center of map
```

After all trolls get actions, `_consider_training()` checks if we can afford a new troll.

## Key Strategy Improvements (arena_bot.py vs baseline)

### 1. Combo Actions (MOVE+DROP, MOVE+HARVEST)

The game engine processes actions in order: Move → Harvest → Drop. By issuing `MOVE 0 5 3;DROP 0` in one turn, the troll moves to a shack neighbor AND drops items in the same turn. This saves ~1 turn per delivery cycle.

Similarly, `MOVE 0 8 4;HARVEST 0` moves to a tree and harvests it in one turn, saving 1 turn per harvest cycle.

Impact: ~1 turn saved per harvest-drop round trip. Over 300 turns with multiple trolls, this adds up to significant score gains.

### 2. Opportunistic Planting (PLANT)

If a troll carrying fruit happens to be on a grass+water cell near our shack that doesn't already have a tree, it plants (up to 2 trees max). Trees near water grow faster (reduced cooldown), creating long-term fruit factories.

Currently limited: only plants when a troll happens to be on a good spot. A full planting strategy would use PICK to ferry fruits from shack to planting locations.

### 3. Value-Based Chopping

Instead of always chopping after turn 200, the arena bot:
- After turn 180: only chops if the tree has no fruits (avoid destroying productive trees)
- After turn 220: chops if wood value (size × 4) > remaining fruits

### 4. Growth Prediction

Trees with `cd > 0` will produce fruit in `cd` turns. The bot estimates future fruit value based on whether the troll will arrive in time to harvest the upcoming fruit. Trees with `cd=0` and no fruits are estimated to produce soon.

### 5. Training Improvements

- Troll cap raised from 8 to 10
- Always tries cheapest affordable config first
- Ensures at least 2 trolls have chopPower by mid-game
- Skips non-chop configs in mid-game if we need chop trolls and can afford them

## Target Scoring

Each troll without a current task scores all fruit trees:

```
score = (harvestable_fruits + future_fruit_value) / round_trip_time

Bonuses:
  +2.0  if reachable this turn (may get combo harvest)
  +0.2  if closer to us than opponent shack (manhattan)
  +0.1  if tree is near water (faster growth)

Penalties:
  ×0.7  per troll already targeting this tree (spread factor)
```

Round-trip time = `(distance_to_tree / speed) + 1 + (distance_to_shack / speed) + 1`

Iron cells scored as `3.0 / (distance / speed)` when iron inventory < max(3, trollCount).

## Training Logic

### Arena Bot (v5)

Tries configs in order until one is affordable. Cheapest first within each phase:

| Phase | Turns | Config priorities | Rationale |
|-------|-------|-------------------|-----------|
| Early | 1-20 | (1,1,1,0), (1,2,1,0), (2,1,1,0), (1,1,2,0), (1,1,1,1), ... | More trolls = more actions; carry=2 is very efficient |
| Mid | 21-80 | (1,1,1,0), (1,2,1,0), (2,1,1,0), (1,1,2,0), ..., (1,2,1,1), (2,2,1,1) | Balanced; start including chopPower |
| Late | 81+ | (1,1,1,0), (1,2,1,0), (2,2,1,0), ..., (2,2,1,1), (2,2,2,1) | ChopPower for late-game wood |

Hard cap: 10 trolls. Iron check skips chopPower configs when iron is insufficient.

## Pathfinding

BFS is cached per cell. Shack cells are non-walkable but handled: trolls on the shack can pathfind to its walkable neighbors with distance=1. Distance maps computed lazily and cached.

## Performance

Each turn: <1ms. No timeouts across 1000+ games. BFS caching means turn 1 is slightly slower (all distance maps computed), subsequent turns are fast.

## Score Benchmarks

| Opponent | Win Rate | Avg Margin |
|----------|----------|------------|
| examplebot | 100% (50/50) | +80 points |
| v001 baseline (self-play) | 30% W / 26% L / 44% T | +0.7 points avg |
| Mirror match (self) | ~5% W / 25% L / 70% T | -0.9 points (P2 advantage) |

## What We Don't Do Yet

1. **Dedicated planting strategy**: Only plants opportunistically. Full strategy: PICK fruit from shack, carry to good spot, PLANT, then harvest the new tree.

2. **PICK action**: Never used. Could ferry iron/fruit from shack to strategic locations.

3. **Targeted tree chopping**: Don't send trolls specifically to chop valuable trees. Only chop when already on a tree.

4. **Opponent modeling**: Don't track opponent troll positions or predict which trees they'll contest. Don't exploit fruit duplication mechanic deliberately.

5. **Coordinated multi-troll harvesting**: Only apply 0.7 spread penalty, don't model the benefit of sharing trees (duplication).

6. **Steal-from-opponent strategies**: Don't deliberately contest opponent's trees (even though duplication makes this beneficial).

7. **Iron-dependent training optimization**: Don't optimally schedule iron mining for upcoming training needs.

8. **Map-specific adaptation**: Don't adjust strategy based on map topology (clustered vs spread trees, iron positions relative to shack).