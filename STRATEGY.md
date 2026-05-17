# Bot Strategy Deep-Dive

## Current State

`arena_bot.py` is the submission bot. It was retuned for Wood 1 and promoted the account to **Bronze**, then the small Bronze "pressure" target-scoring variant promoted it to **Silver**. Latest known ladder status: **Silver 512/630** on May 17, 2026. It now keeps two strategy modes in one file:

| Mode | Detection | Rules Shape | Current Plan |
|------|-----------|-------------|--------------|
| Wood 1 / league 2 | no iron cells on map | 100 turns, fruit-only scoring, no water/iron/wood | close shack orchard, banana-first planting, no chop training |
| Bronze/Silver / league 3+ | iron cells exist | 300 turns, water boosts, iron, chop/mine, wood scores 4 | water-adjacent orchard, normal harvesting, tiny opponent-pressure bonus, late chop/mine logic |

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
8. FIND TARGET          score trees/iron/opponent pressure -> MOVE
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

## Bronze/Silver Strategy

Bronze adds water, iron, chopping, mining, wood score, and 300 turns. The current Silver bot is still mostly the Bronze bot, with one successful ladder-facing addition: a small target bonus for opponent pressure.

Bronze/Silver behavior today:

- Plant up to 3 water-adjacent trees near the shack (`shack_dist <= 5`).
- Seed priority is `APPLE`, `PLUM`, `LEMON`, then `BANANA`.
- Apple is preferred near water because cooldown is very low in Bronze rules.
- Training cap is 10 trolls.
- Training includes chopPower configs after early game, subject to iron affordability.
- Mine iron when iron inventory is below `max(3, troll_count)`.
- Chop late: starts after turn 180 on unproductive trees, with an aggressive value fallback after turn 220.
- Target scoring adds a small pressure bonus when a fruiting tree is near an opponent troll or lies on opponent-favored territory.

Important ladder history:

- `arena_bot_base.py` is the preserved Bronze-promotion base.
- `arena_bot_variant_pressure.py` was copied to `arena_bot.py` and promoted to Silver, rank 512/630.
- `arena_bot_variant_mine6.py` had positive paired mirror score but dropped ladder rank to Bronze 339/529. Treat mirror self-play as only one signal.

Useful local benchmark for the Silver pressure variant:

```bash
python3 eval_pool.py arena_bot.py --opponents config config_v001 config_v002 backup --seeds 12 --start 1 --league 3 --jobs 10
```

Pressure result: **88W-8L**, average diff **+47.72**. Base on the same pool: **84W-11L**, average diff **+46.31**, with one crash. In mirror paired self-play, pressure was slightly negative (`-1.08` avg paired diff over 12 seeds), so the pool result and ladder promotion mattered more.

## Target Scoring

Each idle troll scores trees roughly as:

```
score = (harvestable_fruits + future_fruit_value) / round_trip_time
```

Bonuses:

- `+2.0` if the tree is reachable this turn.
- `+0.2` if closer to our current path than the opponent shack by Manhattan proxy.
- `+0.1` if the tree is near water.
- Bronze/Silver pressure bonus:
  - up to `+0.18` for a fruiting tree with an opponent troll within Manhattan distance 2.
  - `+0.08` for a fruiting tree with an opponent troll within distance 4.
  - up to `+0.12` for trees clearly closer to the opponent shack than ours.

Penalties / filters:

- Bronze: multiply by `0.7` if another troll is already targeting the tree.
- Wood 1: skip trees already targeted by a friendly troll.
- Wood 1: skip fruit trees already occupied by an empty friendly troll.

Iron cells are currently scored as `3.0 / (distance / speed)` when a chop-capable troll has capacity and iron inventory is low. Caveat: iron cells themselves are not walkable; `arena_bot_variant_mine_spots.py` tested targeting adjacent grass cells and was nearly neutral locally. Revisit this only with a stronger mining/training plan.

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

## Variant Lessons From Bronze To Silver

Preserve these lessons so we do not rediscover them tomorrow:

- **Pressure worked on ladder**: small opponent-aware target bonuses promoted to Silver.
- **Mirror self-play can mislead**: `mine6` looked positive locally but dropped ladder rank; pressure looked slightly negative in mirror but climbed.
- **Bronze planting is essential**: disabling Bronze planting was catastrophic (`-80.67` avg paired diff over 12 seeds).
- **Plant cap changes were not enough**: 2 and 4 plant caps were slightly worse than the 3-tree anchor.
- **Naive stacking is bad**: forcing/encouraging a second troll to the same tree lost heavily despite harvest duplication existing in the referee.
- **Resource-balance chasing was bad**: over-weighting scarce training fruit caused long trips and score collapses.
- **Fruit-only Bronze was close but negative**: removing chop training/wood behavior was not a clear improvement.
- **Endgame cash-in gating was negative**: simple "skip if cannot bank by turn 300" hurt more than it helped.

## Next Silver Work

1. Build stronger local opponent pool entries:
   - fast-train swarm
   - orchard-heavy bot
   - pressure/disruptor bot
   - wood-focused endgame bot

2. Improve opponent modeling:
   - predict which trees opponent trolls can reach this turn.
   - contest only when we can harvest/drop efficiently.
   - avoid the failed crowding behavior from `stack2`.

3. Revisit chopping/mining with intent:
   - route to adjacent mining spots, not iron cells.
   - mine only when it unlocks a planned training config.
   - chop only when wood can be returned and the lost fruit production is acceptable.

4. Improve evaluation:
   - use both `paired_self_play.py` and `eval_pool.py`.
   - treat ladder rank as the final arbiter when local signals conflict.

## Files

| File | Purpose |
|------|---------|
| `arena_bot.py` | Submission bot; current best |
| `arena_bot_base.py` | Preserved Bronze-promotion base strategy |
| `arena_bot_silver_base.py` | Preserved Silver-promotion pressure strategy |
| `bot.py` | Older configurable baseline; useful as a sparring partner, not proof of ladder strength |
| `self_play.py` | Batch runner |
| `paired_self_play.py` | Fair paired A/B runner with parallel jobs |
| `eval_pool.py` | Broader local opponent-pool evaluator |
| `arena_bot_backup.py` | Old pre-rewrite arena bot |
