# AGENTS.md — Project Guide for CodinGame Troll Farm Bot

This document explains the project's purpose, how everything fits together, and what each piece does. It's the orienting overview; the other docs handle the details.

## What Is This Project?

We're building a bot to compete in the **CodinGame Spring Challenge 2026 — Troll Farm**, a turn-based 2-player strategy game. Two bots face off on a procedurally generated grid map. Each player controls trolls that harvest fruit from trees, carry resources back to their shack, and convert resources into more trolls.

Current ladder status: the bot has reached **Bronze** after a Wood 1-focused rewrite. Wood 1/league 2 is a 100-turn fruit-only game with no water, iron, or wood scoring. Bronze/league 3 reintroduces water, iron, chopping, mining, wood scoring, and 300 turns.

This is a competitive programming project. The bot needs to make smart decisions under a 50ms-per-turn time limit.

## How the Pieces Fit Together

```
┌──────────────────────────────────────────────────────────────┐
│  CodinGame Platform / Local Testing                          │
│                                                              │
│  The game engine (referee) runs in a Java JAR. It:          │
│  1. Generates the map                                        │
│  2. Sends game state to both bots via stdout                  │
│  3. Reads actions from both bots via stdin                    │
│  4. Simulates one turn                                       │
│  5. Repeats for 300 turns                                   │
│  6. Outputs final scores                                     │
└──────────────────────────────────────────────────────────────┘
         │ stdin/stdout                    │ stdin/stdout
         ▼                                 ▼
   ┌──────────────┐                ┌──────────┐
   │ arena_bot.py │                │ opponent │
   │  (our best)  │                │  (any)   │
   └──────────────┘                └──────────┘
         │ configurable variants
         ▼
   ┌──────────┐
   │  bot.py  │  ← --config flag loads JSON from versions/
   └──────────┘
```

### File Map

| File | Role |
|------|------|
| `arena_bot.py` | **Arena submission** — our best bot. Single-file Python 3, no dependencies. Detects Wood 1 vs Bronze from the map, uses dedicated planting/training logic, and has Bronze chop/mine fallbacks. Submit this to CodinGame. |
| `bot.py` | Configurable strategy bot. Supports `--config` flag for versioned JSON configs. Used for self-play iteration. |
| `self_play.py` | Tournament runner. Runs two bot versions across N seeds, reports win/loss stats. |
| `iterate.py` | Cycle manager. Tracks champion/challenger versions, runs matches, records history. |
| `versions/` | Directory of versioned JSON config files (v001.json, v002.json). Each config controls bot strategy parameters. |
| `ITERATE.md` | Documentation for the self-play iteration system. |
| `examplebot.py` | CodinGame's starter template. Does `MOVE 0 7 7` every turn. Used as baseline opponent. |
| `run.sh` | Shell script that runs a match inside Docker. |
| `Troll-Farm/troll-farm-1.0-SNAPSHOT.jar` | The game referee. |
| `tools/summarize_log.py` | Reads a JSON game log, prints scores and errors. |

### Documentation Map

| Doc | What it covers | When to read it |
|-----|----------------|-----------------|
| **NOTES.md** | Raw game rules, I/O protocol, constants from source code | Once, to understand what the game sends/receives |
| **STRATEGY.md** | How our bot decides things: decision flow, scoring formula, training configs | When modifying `arena_bot.py` or planning improvements |
| **EVAL.md** | How to run matches, batch-test, debug, use the web viewer | When testing changes or investigating crashes |
| **ITERATE.md** | Self-play iteration system: versioned configs, A/B testing, champion/challenger cycle | When improving the bot through competitive iteration |
| **This file** | You're reading it | Right now, or when coming back to the project |

## How arena_bot.py Works (Our Best Bot)

The bot is a single `Bot` class that lives for the whole game:

1. **`__init__`** — Reads the map once. Precomputes walkability grid, water adjacency, shack neighbor cells, BFS cache, and planting spots. If no iron cells exist, sets `low_league=True` and switches to Wood 1 assumptions.

2. **`turn()`** — Called every turn. Reads current state. For each troll, decides an action. Then optionally trains a new troll.

Per-troll decision is a **fixed priority chain**:

```
dedicated PLANT plan → DROP → HARVEST → opportunistic PLANT → CHOP → MINE → find best target → fallback
```

### Key Improvements Over Baseline (bot.py v4)

| Feature | Baseline | arena_bot.py |
|---------|----------|--------------|
| **Referee legality** | Old notes assumed same-troll combos | One action per troll per turn; no `MOVE;HARVEST`/`MOVE;DROP` on same troll |
| **Wood 1 adaptation** | Bronze assumptions leak into Wood 1 | Detects no-iron map, ignores iron costs, uses 100-turn fruit-only plan |
| **Planting** | None/opportunistic only | Dedicated `PICK -> MOVE -> PLANT` flow |
| **Wood 1 orchard** | None | Up to 4 close banana-first planted trees near shack |
| **Bronze planting** | None | Up to 3 water-adjacent planted trees near shack |
| **Target coordination** | Multiple trolls may crowd one target | Wood 1 deconflicts tree targets and avoids friendly-occupied fruit trees |
| **Chopping/mining** | Late or absent | Bronze value-based chopping and iron mining still present |
| **Training** | Phase-based, fixed lists | Wood 1 has no chop/iron training; Bronze includes chopPower configs |
| **Growth prediction** | Basic cd threshold | Also considers cd=0 trees about to produce |

### Self-Play Results

Most recent local benchmarks:

| Bot | Opponent | League | Seeds | Result | Avg Diff |
|-----|----------|--------|-------|--------|----------|
| `arena_bot.py` | `bot.py` | 2 / Wood 1 | 50 | **48W-2L-0T** | **+18.9** |
| `arena_bot.py` | `bot.py` | 3 / Bronze | 50 | **35W-12L-3T** | **+28.1** |
| `arena_bot_backup.py` | `bot.py` | 3 / Bronze | 20 | 2W-4L-14T | -0.3 |

Wood 1 ladder result after the rewrite: promoted to **Bronze**. The next work should optimize for Bronze, not Wood 1.

## Self-Play Iteration System

The project uses a **versioned config system** for iterative improvement:

1. **`bot.py --config /work/versions/vXXX.json`** loads a JSON config overriding strategy parameters
2. **`self_play.py`** runs two versions against each other across N seeds
3. **`iterate.py`** manages the champion/challenger cycle

```bash
python3 iterate.py new-challenger   # create challenger from champion
python3 self_play.py v001 v002 --seeds 50  # test
python3 iterate.py promote v002     # if challenger wins
```

See **ITERATE.md** for full documentation.

## How to Make Changes

### Quick test cycle

```bash
# Quick test (one seed)
./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42

# Broader test (10 seeds)
for s in $(seq 1 10); do
    ./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" $s 2>&1 | grep -v WARNING | head -2 | paste -sd' '
done

# Wood 1 / league 2 self-play test (100-turn fruit-only rules)
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --league 2

# Bronze / league 3 self-play test (300-turn, wood/iron/water rules)
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --league 3
```

### Editing arena_bot.py

Key sections:
- **League detection / planting spots** (`__init__`): `low_league = len(iron_cells) == 0`; Wood 1 uses close shack cells, Bronze uses water-adjacent cells.
- **Decision priority chain** (`_decide`): planter task → DROP → HARVEST → opportunistic PLANT → CHOP → MINE → target → fallback.
- **Dedicated planting** (`_planter_action`, `_assign_plant_target`, `_choose_seed_type`): Wood 1 is banana-first, max 4 plants; Bronze is apple/plum/lemon/banana, max 3 plants.
- **Target scoring** (`_best_target`): value-per-round-trip-time with bonuses; Wood 1 avoids duplicate friendly targets.
- **Training** (`_consider_training`): Wood 1 ignores iron/chop and caps at 7 trolls; Bronze caps at 10 and includes chopPower.

### Editing bot.py (configurable version)

Same logic as arena_bot.py but reads parameters from a JSON config file. Used for self-play A/B testing where you tweak parameters without code changes.

## What the Game Engine Does (Key Details)

- **Turn order**: Move → Harvest → Plant → Chop → Pick → Train → Drop → Mine → Grow.
- **One action per troll**: The referee rejects using the same troll twice in one turn. Do not output same-troll `MOVE;HARVEST`, `MOVE;DROP`, etc. Earlier docs and comments were wrong about this.
- **Harvest/Chop sharing**: When two trolls (even opposing) harvest/chop the same tree, the last item can **duplicate**. Contesting a tree is beneficial.
- **Shack is special**: Trolls spawn there but can't walk back onto it. DROP works from orthogonally adjacent cells.
- **Training requires empty shack**: If a troll is on the shack, TRAIN fails.
- **Planting**: Costs 1 fruit. Tree must be on empty grass cell (no existing tree).
- **Initial troll**: Stats (1,1,1,1). Initial resources: 2-10 of each fruit, 2-10 iron.
- **Wood 1 differences**: No water/iron/wood, 100 turns, fruit-only scoring, last inventory/carry fields are reserved zeros. Training cost effectively uses only plum/lemon/apple.

## What to Work On Next

Highest-impact Bronze improvements still available:

1. **Bronze retuning after promotion**: The current bot includes Bronze logic, but the latest ladder push was optimized for Wood 1. Re-test with `--league 3` and tune specifically for 300 turns with wood/iron/water.

2. **Targeted tree chopping**: Send chop-capable trolls specifically to high-value trees rather than chopping opportunistically when standing on one.

3. **Opponent modeling / contesting**: Track opponent troll positions to contest productive trees and exploit duplication.

4. **Bronze training/mining schedule**: Mine iron based on upcoming training costs, not just current iron threshold.

5. **Bronze planting selection**: Confirm whether apple-first water orchards remain best now that games last 300 turns; test 2/3/4 plant caps again in league 3.

## How to Use This When Coming Back

1. Read this file for orientation
2. Read STRATEGY.md for "how it decides" and "what to improve"
3. Read EVAL.md for "how to test" and ITERATE.md for "how to iterate"
4. Edit arena_bot.py, test with `./run.sh` and `self_play.py`, iterate
