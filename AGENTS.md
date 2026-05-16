# AGENTS.md — Project Guide for CodinGame Troll Farm Bot

This document explains the project's purpose, how everything fits together, and what each piece does. It's the orienting overview; the other docs handle the details.

## What Is This Project?

We're building a bot to compete in the **CodinGame Spring Challenge 2026 — Troll Farm**, a turn-based 2-player strategy game. Two bots face off on a procedurally generated grid map. Each player controls trolls that harvest fruit from trees, carry resources back to their shack, and convert resources into more trolls. The player with more points (fruits=1pt, wood=4pt) after 300 turns wins.

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
| `arena_bot.py` | **Arena submission** — our best bot. Single-file Python 3, no dependencies. Has combo actions, planting, value-based chopping. Submit this to CodinGame. |
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

1. **`__init__`** — Reads the map once. Precomputes walkability grid, water adjacency, shack neighbor cells, BFS cache, and planting spots (grass+water cells near shack).

2. **`turn()`** — Called 300 times. Reads current state. For each troll, decides an action. Then optionally trains a new troll.

Per-troll decision is a **fixed priority chain**:

```
DROP (or MOVE+DROP combo) → HARVEST (or MOVE+HARVEST combo) → PLANT (opportunistic) → CHOP (value-based) → MINE → find best target → fallback
```

### Key Improvements Over Baseline (bot.py v4)

| Feature | Baseline | arena_bot.py |
|---------|----------|--------------|
| **Combo actions** | Separate turns for move+action | MOVE+DROP and MOVE+HARVEST in same turn |
| **Planting** | None | Opportunistic PLANT on grass+water cells near shack (up to 2) |
| **Chopping** | After turn 200, always if wood > fruit | Value-based after turn 180; skip productive trees; aggressive after 220 |
| **Training cap** | 8 trolls | 10 trolls |
| **Training order** | Phase-based, fixed lists | Cheapest first; ensures chopPower trolls exist by mid-game |
| **Growth prediction** | Basic cd threshold | Also considers cd=0 trees about to produce |

### Self-Play Results

arena_bot.py vs baseline (bot.py v4 v001): **15 wins, 13 losses, 22 ties** across 50 seeds (avg score +0.7).

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

# Self-play test (vs baseline, 50 seeds)
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50
```

### Editing arena_bot.py

Key sections:
- **Decision priority chain** (`_decide` method, ~line 180): DROP → HARVEST → MOVE+HARVEST → PLANT → CHOP → MINE → target → fallback
- **Combo actions**: MOVE+DROP at line ~195, MOVE+HARVEST at line ~205
- **Target scoring** (`_best_target` method, ~line 330): value-per-round-trip-time with bonuses
- **Training** (`_consider_training`, ~line 405): phase-based configs, cheapest first

### Editing bot.py (configurable version)

Same logic as arena_bot.py but reads parameters from a JSON config file. Used for self-play A/B testing where you tweak parameters without code changes.

## What the Game Engine Does (Key Details)

- **Turn order**: Move → Harvest → Plant → Chop → Pick → Train → Drop → Mine → Grow. Combo actions like `MOVE 0 5 3;HARVEST 0` execute both in the same turn.
- **Harvest/Chop sharing**: When two trolls (even opposing) harvest/chop the same tree, the last item can **duplicate**. Contesting a tree is beneficial.
- **Shack is special**: Trolls spawn there but can't walk back onto it. DROP works from orthogonally adjacent cells.
- **Training requires empty shack**: If a troll is on the shack, TRAIN fails.
- **Planting**: Costs 1 fruit. Tree must be on empty grass cell (no existing tree).
- **Initial troll**: Stats (1,1,1,1). Initial resources: 2-10 of each fruit, 2-10 iron.

## What to Work On Next

Highest-impact improvements still available:

1. **Smarter planting**: Currently only plants opportunistically (2 trees max, if troll happens to be on a good spot). A dedicated planting strategy — PICK a fruit from shack, carry it to a grass+water cell, PLANT it, then harvest — would create ongoing fruit factories near our shack.

2. **PICK action**: Never used. Can ferry specific items (fruits for planting, iron for training) from the shack to strategic locations.

3. **Targeted tree chopping**: Send chop-capable trolls specifically to high-value trees rather than chopping opportunistically when standing on one.

4. **Opponent modeling**: Track opponent troll positions to contest or avoid specific trees, and exploit the fruit duplication mechanic when contesting.

5. **Coordinated multi-troll harvesting**: Model the benefit of sharing a tree (duplication mechanics) rather than just penalizing overlap.

## How to Use This When Coming Back

1. Read this file for orientation
2. Read STRATEGY.md for "how it decides" and "what to improve"
3. Read EVAL.md for "how to test" and ITERATE.md for "how to iterate"
4. Edit arena_bot.py, test with `./run.sh` and `self_play.py`, iterate