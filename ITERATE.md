# Self-Play Iteration Guide

## Overview

The self-play system lets you evolve the bot through competitive iteration:

1. Create a **champion** version (current best strategy as a config)
2. Create a **challenger** version (a copy you modify with new parameters)
3. **Test** the challenger against the champion across many seeds
4. If the challenger wins → **promote** it to champion, create a new challenger
5. Repeat

## Files

| File | Purpose |
|------|---------|
| `arena_bot.py` | **Arena submission** — our best standalone bot (no config needed) |
| `bot.py` | Configurable bot with `--config` flag for A/B testing |
| `self_play.py` | Tournament runner. Runs two versions against each other across N seeds. |
| `iterate.py` | Cycle manager. Initializes versions, tracks champion, creates challengers, records history. |
| `versions/` | Directory of versioned JSON config files (v001.json, v002.json, ...). |
| `versions/champion.txt` | Points to the current champion version. |
| `versions/history.json` | Record of all champion/challenger matches. |

## Current State

- **Champion**: v001 (baseline, matches original hardcoded strategy)
- **Arena bot**: `arena_bot.py` (has combo actions, planting, value-based chopping — beats baseline by +0.7 avg score)
- **Challenger**: v002 (early-chop variant — lost to v001, 14% win rate)

### Arena Bot vs Baseline (50 seeds)

| Metric | arena_bot.py | v001 baseline |
|--------|-------------|---------------|
| Wins | 15 (30%) | 13 (26%) |
| Ties | 22 (44%) | 22 (44%) |
| Avg score | 104.3 | 103.5 |
| Avg diff | +0.7 | — |

The arena bot is our best submission. It's a superset of the baseline with combo actions and opportunistic planting.

## Quick Start

```bash
# Run the arena bot against examplebot
./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42

# Self-play: arena bot vs baseline
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50

# Config-based self-play (for parameter tuning)
python3 self_play.py v001 v002 --seeds 30

# Iteration workflow
python3 iterate.py init          # Initialize (already done)
python3 iterate.py status        # Show champion/challenger
python3 iterate.py new-challenger  # Create challenger from champion
python3 iterate.py run --seeds 30   # Test champion vs challenger
python3 iterate.py promote v002      # Promote challenger to champion
python3 iterate.py diff             # Show config differences
```

## Config Parameters

Each version's JSON config controls `bot.py` strategy (NOT `arena_bot.py`):

### Training (`training`)
| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `max_trolls` | int | 8 | Maximum trolls to train |
| `phase_thresholds` | [int, int] | [20, 80] | Turn thresholds for early/mid/late configs |
| `early_configs` | [[m,c,h,ch],...] | see v001 | Training stat configs for turns 1-20 |
| `mid_configs` | [[m,c,h,ch],...] | see v001 | Training stat configs for turns 21-80 |
| `late_configs` | [[m,c,h,ch],...] | see v001 | Training stat configs for turns 81+ |

### Target Scoring (`scoring`)
| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `reach_bonus` | float | 2.0 | Bonus for trees reachable this turn |
| `closer_bonus` | float | 0.2 | Bonus for trees closer to us than opponent |
| `water_bonus` | float | 0.1 | Bonus for trees near water |
| `spread_penalty` | float | 0.7 | Multiplier per troll already targeting same tree |
| `iron_base_score` | float | 3.0 | Base score for mining iron cells |
| `iron_threshold` | int | 4 | Mine iron when inventory < this |
| `future_fruit_cd_threshold` | int | 2 | How many turns ahead to predict fruit growth |
| `future_fruit_large_tree` | float | 1.0 | Predicted fruit value for size≥4 trees |
| `future_fruit_medium_tree` | float | 0.3 | Predicted fruit value for size≥2 trees |

### Chopping (`chop`) and Mining (`mining`)
| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `chop.start_turn` | int | 200 | Turn after which trolls start chopping |
| `chop.wood_value` | int | 4 | Point value per wood |
| `chop.wood_vs_fruit_ratio` | float | 1.0 | Chop when `wood_gain × wood_value > fruit × ratio` |
| `mining.iron_threshold_base` | int | 3 | Mine iron when inventory < max(this, trollCount) |

## Strategy Tips

**Note**: Config parameters only affect `bot.py` (used for A/B testing). `arena_bot.py` has its own hardcoded values that incorporate the best parameters found so far.

For **config-only** improvements to test via self-play:
- `training.max_trolls` — Higher limits (10) seem slightly better
- `scoring.spread_penalty` — Lower = more aggressive tree sharing (benefits from duplication)
- `chop.start_turn` — Earlier chopping (150) was tested in v002 and lost; current 200 seems better
- `scoring.water_bonus` — Higher = prioritize near-water trees

For **code changes** (affects arena_bot.py), the highest-impact improvements:
1. **Dedicated planting**: Use PICK → carry → PLANT → harvest cycle
2. **Targeted chopping**: Send trolls to chop specific high-value trees
3. **Opponent modeling**: Track opponent positions, contest their trees for duplication benefit