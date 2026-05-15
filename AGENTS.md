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
   ┌──────────┐                     ┌──────────┐
   │  bot.py  │                     │ opponent │
   │  (ours)  │                     │  (any)   │
   └──────────┘                     └──────────┘
```

### File Map

| File | Role |
|------|------|
| `bot.py` | **Our bot** — the only file we're actively developing. Single-file Python 3, no dependencies. ~420 lines. |
| `examplebot.py` | CodinGame's starter template. Does `MOVE 0 7 7` every turn (useless). Used as a baseline opponent. |
| `run.sh` | Shell script that runs a match inside Docker. Handles the Java/Docker setup so we just say `./run.sh "python3 /work/bot.py" "python3 /work/examplebot.py" 42`. |
| `Troll-Farm/troll-farm-1.0-SNAPSHOT.jar` | The game referee (closed-source binary from CodinGame). Validates moves, simulates the game, outputs scores. |
| `tools/run_match.sh` | Lower-level Docker wrapper called by `run.sh`. Most of the time you don't call this directly. |
| `tools/Dockerfile.trollfarm-runner` | Docker image: JRE 17 + Python 3. Auto-built by `run.sh` if missing. |
| `tools/summarize_log.py` | Reads a JSON game log, prints scores, errors, and referee messages. |

### Documentation Map

| Doc | What it covers | When to read it |
|-----|----------------|-----------------|
| **NOTES.md** | Raw game rules, I/O protocol, constants from source code | Once, to understand what the game sends/receives |
| **STRATEGY.md** | How our bot decides things: decision flow, scoring formula, training configs, what we don't do yet, source-code quirks we found | When modifying `bot.py` or planning improvements |
| **EVAL.md** | How to run matches, batch-test, debug, use the web viewer, common bugs | When testing changes or investigating crashes |
| **This file** | You're reading it | Right now, or when coming back to the project |

## How Our Bot Works (Conceptual)

The bot is a single `Bot` class that lives for the whole game:

1. **`__init__`** — Reads the map once. Precomputes walkability grid, water adjacency, shack neighbor cells. Sets up BFS cache.

2. **`turn()`** — Called 300 times. Reads current state (inventories, trees, trolls). For each troll we own, decides an action. Then optionally trains a new troll.

Per-troll decision is a **fixed priority chain**:

```
DROP → HARVEST → CHOP → MINE → (return to shack if carrying) → find best target → fallback center
```

Target selection uses a **scoring function** that estimates value-per-round-trip-time for each fruit tree on the map, with bonuses for proximity, water adjacency, and opponent avoidance. The "best target" is the highest-scoring tree (or iron cell if we need iron).

Training tries **hardcoded config lists** in order until it finds one we can afford. Configs are phase-dependent (early game favors cheap trolls; late game includes chopPower).

## How to Make Changes

### The edit/test cycle

```bash
# 1. Edit bot.py
# 2. Quick test (one seed)
./run.sh "python3 /work/bot.py" "python3 /work/examplebot.py" 42

# 3. Broader test (10 seeds)
for s in $(seq 1 10); do
    ./run.sh "python3 /work/bot.py" "python3 /work/examplebot.py" $s 2>&1 | grep -v WARNING | head -2 | paste -sd' '
done

# 4. Watch a replay
SERVER=1 LOG=logs/replay.json ./run.sh "python3 /work/bot.py" "python3 /work/examplebot.py" 42
# Open http://localhost:8888/test.html
```

### Key parameters to tweak

| What | Where in `bot.py` | Effect |
|------|-------------------|--------|
| Training configs | `_consider_training()` lines ~360-415 | Which troll stats to try, in what order, by game phase |
| Target scoring weights | `_best_target()` lines ~254-355 | Bonuses for reachability, proximity, water, opponent distance, spread penalty |
| Chop threshold | `_decide()` line `turn > 200` | When to start chopping trees for wood |
| Iron mining threshold | `_decide()` line `my_inv[IRON] < max(3, ...)` | When trolls should go mine iron |
| Max trolls | `_consider_training()` line `n >= 8` | Hard cap on troll count |
| Spread penalty multiplier | `_best_target()` line `score *= 0.7` | How much to penalize trees already targeted |

### Adding a new action

The game supports: MOVE, HARVEST, DROP, PICK, PLANT, CHOP, MINE, TRAIN, WAIT, MSG.

Currently unused: **PLANT** (plant a tree) and **PICK** (take item from shack).

To add PLANT support:
1. In `_decide()`, add a PLANT decision after MINE/HARVEST checks
2. Troll must be on an empty grass cell and carry at least 1 fruit of that type
3. Add fruit-to-tree-type mapping (`PLUM→PLUM`, `LEMON→LEMON`, `APPLE→APPLE`, `BANANA→BANANA`)
4. In `_best_target()`, consider moving toward strategically good empty cells near our shack/water

To add PICK support:
1. In `_decide()`, add a PICK decision when troll is near shack and we want to ferry a specific item
2. Format: `PICK <id> <TYPE>` e.g., `PICK 3 PLUM`
3. Useful for: carrying seeds to good planting locations, carrying iron from shack to a new troll location

## What the Game Engine Does (That You Can't See From I/O)

Details confirmed by reading the Java referee source at `/tmp/pi-github-repos/eulerscheZahl/Troll-Farm/`:

- **Turn order matters**: Move → Harvest → Plant → Chop → Pick → Train → Drop → Mine → Grow. You can issue `MOVE 0 5 3;HARVEST 0` and both execute in the same turn (move first, then harvest at the new location).
- **Movement collision**: If two same-team trolls move to the same cell, only one succeeds. The engine resolves this deterministically (higher ID wins for same-target moves, circular swaps for swaps).
- **Harvest/Chop sharing**: When two trolls (even opposing) harvest/chop the same tree simultaneously, they alternate taking items. The last item can **duplicate** — both trolls get it. Contesting a tree is actually beneficial.
- **Training requires an empty shack cell**: If a troll is still standing on the shack, TRAIN fails.
- **Shack is special**: Trolls spawn there but can't walk back onto it. DROP works from orthogonally adjacent cells.
- **Early game end**: Game ends after 10 consecutive turns with zero trees, or if both players are stuck (no resources to harvest and nothing in shack to pick).
- **Initial resources**: Each player starts with 2-10 of each fruit type and 2-10 iron (randomized per seed). Initial troll has stats (1,1,1,1).

## What to Work On Next

The STRATEGY.md "What We Don't Do Yet" section lists 11 concrete improvements, ranked by likely impact. The top three:

1. **Plant trees** — We never plant. A single fruit invested near our shack + water can produce 3 fruits every 3-8 turns indefinitely. This is likely the single biggest improvement available.

2. **Predict tree growth** — We don't use the `cooldown` field at all. Trees with `cd=1` next to our troll will produce fruit next turn — we should walk toward those instead of trees with `cd=6`.

3. **Targeted tree chopping** — A size-4 tree chopped for wood yields 4×4=16 points. Currently we only chop opportunistically after turn 200. We should compute whether chopping a specific tree is worth more than letting it keep producing fruit, and send chop-capable trolls to valuable targets.

## How to Use This When Coming Back

1. Read this file for orientation
2. Read STRATEGY.md for "how it decides" and "what to improve"
3. Read EVAL.md for "how to test"
4. Read NOTES.md if you need the raw I/O protocol or game constants
5. Edit bot.py, test with `./run.sh`, iterate