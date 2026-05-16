# Bot Strategy Deep-Dive

## Current State

`arena_bot.py` is the submission bot. It was retuned for Wood 1 and promoted the account to **Bronze**. It now keeps two strategy modes in one file:

| Mode | Detection | Rules Shape | Current Plan |
|------|-----------|-------------|--------------|
| Wood 1 / league 2 | no iron cells on map | 100 turns, fruit-only scoring, no water/iron/wood | close shack orchard, banana-first planting, no chop training |
| Bronze / league 3 | iron cells exist | 300 turns, water boosts, iron, chop/mine, wood scores 4 | water-adjacent orchard, normal harvesting, late chop/mine logic |

Important referee correction: each troll can only perform one action per turn. Do not output same-troll `MOVE;HARVEST`, `MOVE;DROP`, etc. The old combo strategy was based on a bad reading of turn order.

## Decision Flow

Per troll, `arena_bot.py` currently uses:

```
1. DEDICATED PLANTING   assigned PICK -> MOVE -> PLANT job
2. DROP                 carrying AND near shack -> DROP
3. RETURN               carrying AND not near shack -> MOVE to shack neighbor
4. HARVEST              on fruiting tree with capacity -> HARVEST
5. OPPORTUNISTIC PLANT  on valid plant spot carrying a seed -> PLANT
6. CHOP                 Bronze only, on tree, late/value-based
7. MINE                 Bronze only, adjacent iron and iron is low
8. FIND TARGET          score trees/iron -> MOVE
9. FALLBACK             MOVE toward map center
```

After all troll actions are chosen, `_consider_training()` may append a `TRAIN` action.

## Wood 1 Strategy

Wood 1 has no water, no iron, no wood score, and only 100 turns. The bot uses a short-horizon fruit economy:

- Detect Wood 1 with `self.low_league = len(self.iron_cells) == 0`.
- Plant up to 4 trees near the shack (`shack_dist <= 4`).
- Prefer `BANANA` seeds for planting because bananas are not used for training and grow fastest.
- Reserve plum/lemon/apple for training; use them as seeds only when inventory is high.
- Ignore iron cost in training affordability.
- Train only `chopPower=0` trolls and cap at 7 trolls.
- Stop assigning new planting jobs after turn 30 and abandon unfinished planting jobs after turn 45.
- Deconflict tree targets: in Wood 1, avoid sending multiple friendly trolls to the same target tree and avoid friendly-occupied fruit trees.

Latest Wood 1 benchmark:

```bash
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --start 1 --league 2
```

Result: **48W-2L-0T**, average diff **+18.9**.

Variant notes from the Wood 1 tuning pass:

| Variant | 30-seed Result vs `bot.py` | Avg Diff | Takeaway |
|---------|----------------------------|----------|----------|
| 4 close planted trees | 29W-1L | +20.9 | Best tested cap |
| 5 close planted trees | 28W-2L | +19.3 | Slight overcommit |
| 6 close planted trees | 29W-1L | +17.7 | Overplants |
| 7 close planted trees | 30W-0L | +18.3 | Wins sample but lower average |

## Bronze Strategy

Bronze adds water, iron, chopping, mining, wood score, and 300 turns. The current bot has Bronze support, but it has not yet been retuned after promotion.

Bronze behavior today:

- Plant up to 3 water-adjacent trees near the shack (`shack_dist <= 5`).
- Seed priority is `APPLE`, `PLUM`, `LEMON`, then `BANANA`.
- Apple is preferred near water because cooldown is very low in Bronze rules.
- Training cap is 10 trolls.
- Training includes chopPower configs after early game, subject to iron affordability.
- Mine iron when iron inventory is below `max(3, troll_count)`.
- Chop late: starts after turn 180 on unproductive trees, with an aggressive value fallback after turn 220.

Latest Bronze benchmark before the Wood 1-specific cleanup:

```bash
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --start 1 --league 3
```

Result from the earlier pass: **35W-12L-3T**, average diff **+28.1**.

Re-run this before making Bronze decisions, because the current file has since received target deconfliction and low-league branching changes.

## Target Scoring

Each idle troll scores trees roughly as:

```
score = (harvestable_fruits + future_fruit_value) / round_trip_time
```

Bonuses:

- `+2.0` if the tree is reachable this turn.
- `+0.2` if closer to our current path than the opponent shack by Manhattan proxy.
- `+0.1` if the tree is near water.

Penalties / filters:

- Bronze: multiply by `0.7` if another troll is already targeting the tree.
- Wood 1: skip trees already targeted by a friendly troll.
- Wood 1: skip fruit trees already occupied by an empty friendly troll.

Iron cells are scored as `3.0 / (distance / speed)` when a chop-capable troll has capacity and iron inventory is low.

## Training

Training cost is `existing_trolls + stat^2` for each stat. In Wood 1, the fourth cost is reserved/unavailable, so the bot ignores iron affordability and only trains `chopPower=0`.

Wood 1:

| Phase | Turns | Configs |
|-------|-------|---------|
| Early | 1-25 | `(1,1,1,0)`, `(2,1,1,0)`, `(1,2,1,0)`, `(1,1,2,0)`, then 2-stat variants |
| Mid | 26-65 | Prefer `(2,2,1,0)`, `(2,1,2,0)`, `(1,2,2,0)`, `(2,2,2,0)` |
| Late | 66+ | No training |

Bronze:

| Phase | Turns | Intent |
|-------|-------|--------|
| Early | 1-20 | Cheap growth, mostly no chop |
| Mid | 21-80 | Balanced workers, start adding chopPower |
| Late | 81+ | Include chopPower for wood and iron access |

## Next Bronze Work

1. Re-run league 3 baseline after the latest docs/code state:

```bash
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --start 1 --league 3
```

2. Build a few local opponents so we are not only beating our old baseline:

- Greedy no-plant harvester.
- Fast-train swarm with minimal planting.
- Heavy planting bot.
- Wood-focused chop bot for Bronze.

3. Improve Bronze specifically:

- Targeted chopping: send chop-capable trolls to high-value trees before they happen to stand on them.
- Smarter mining: mine iron based on next desired `TRAIN`, not a static threshold.
- Opponent contesting: deliberately share/contest high-yield trees to exploit duplication.
- Bronze plant cap/type tuning: retest 2/3/4 water-adjacent plants and seed order.

## Files

| File | Purpose |
|------|---------|
| `arena_bot.py` | Submission bot; current best |
| `bot.py` | Older configurable baseline; useful as a sparring partner, not proof of ladder strength |
| `self_play.py` | Batch runner |
| `arena_bot_backup.py` | Old pre-rewrite arena bot |
