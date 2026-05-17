# AGENTS.md — Project Guide for CodinGame Troll Farm Bot

This document explains the project's purpose, how everything fits together, and what each piece does. It's the orienting overview; the other docs handle the details.

## What Is This Project?

We're building a bot to compete in the **CodinGame Spring Challenge 2026 — Troll Farm**, a turn-based 2-player strategy game. Two bots face off on a procedurally generated grid map. Each player controls trolls that harvest fruit from trees, carry resources back to their shack, and convert resources into more trolls.

Current ladder status: the bot has reached **Silver** with the Bronze "pressure" variant. Latest known rank: **Silver 512/630** on May 17, 2026. Wood 1/league 2 is a 100-turn fruit-only game with no water, iron, or wood scoring. Bronze/league 3 reintroduced water, iron, chopping, mining, wood scoring, and 300 turns; Silver should be assumed to keep those mechanics and require stronger opponent-aware play.

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
| `arena_bot.py` | **Arena submission** — current Silver bot. Single-file Python 3, no dependencies. Detects Wood 1 vs Bronze/Silver from the map, uses dedicated planting/training logic, Bronze chop/mine fallbacks, and a small opponent-pressure target bonus. Submit this to CodinGame. |
| `arena_bot_base.py` | Preserved Bronze-promotion base strategy. Keep this as a comparison anchor; do not overwrite casually. |
| `arena_bot_silver_base.py` | Preserved Silver-promotion pressure strategy, rank 512/630. Use as the next long-term anchor. |
| `arena_bot_b.py` | Current working challenger copy. At the time of Silver promotion it matches the pressure variant. |
| `arena_bot_variant_*.py` | Named experiment files kept so local results and ladder results remain traceable. |
| `bot.py` | Configurable strategy bot. Supports `--config` flag for versioned JSON configs. Used for self-play iteration. |
| `self_play.py` | Tournament runner. Runs two bot versions across N seeds, reports win/loss stats. |
| `paired_self_play.py` | Paired A/B runner that swaps player order per seed and supports `--jobs` for parallel Docker matches. |
| `eval_pool.py` | Broader local pool evaluator against several non-mirror opponents; useful because mirror self-play mispredicted ladder once. |
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
| **ITERATE.md** | Config-based self-play iteration system | When improving `bot.py` configs |
| **ARENA_ITERATION.md** | Arena single-file variant history: base, pressure, rejected experiments, ladder notes | When modifying `arena_bot.py` or selecting the next ladder probe |
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
| **Opponent pressure** | Pure self-efficiency | Silver variant adds small Bronze+ bonuses for fruit trees near opponent trolls or on opponent-favored territory |

### Self-Play Results

Most recent local benchmarks:

| Bot | Opponent | League | Seeds | Result | Avg Diff |
|-----|----------|--------|-------|--------|----------|
| `arena_bot.py` | `bot.py` | 2 / Wood 1 | 50 | **48W-2L-0T** | **+18.9** |
| `arena_bot.py` pressure | local pool (`bot.py`, v001, v002, backup) | 3 / Bronze | 12 seeds × both orders × 4 opponents | **88W-8L-0T** | **+47.7** |
| `arena_bot_base.py` | same local pool | 3 / Bronze | 12 seeds × both orders × 4 opponents | 84W-11L-0T, 1 crash | +46.3 |
| `arena_bot.py` pre-pressure | `bot.py` | 3 / Bronze | 50 | **35W-12L-3T** | **+28.1** |
| `arena_bot_backup.py` | `bot.py` | 3 / Bronze | 20 | 2W-4L-14T | -0.3 |

Ladder milestones:
- Wood 1 rewrite promoted to **Bronze**.
- Bronze pressure variant promoted to **Silver**, latest known rank **512/630**.
- `arena_bot_variant_mine6.py` had positive mirror self-play but ladder dropped to **Bronze 339/529**, so mirror self-play alone is not trustworthy.

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

# Bronze/Silver rules self-play test (300-turn, wood/iron/water rules)
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --league 3

# Fair A/B against preserved Bronze base, with paired player order and parallel jobs
python3 paired_self_play.py arena_bot.py --base arena_bot_base.py --seeds 20 --start 1 --league 3 --jobs 8

# Broader local pool, useful before a ladder probe
python3 eval_pool.py arena_bot.py --opponents config config_v001 config_v002 backup --seeds 12 --start 1 --league 3 --jobs 10
```

### Editing arena_bot.py

Key sections:
- **League detection / planting spots** (`__init__`): `low_league = len(iron_cells) == 0`; Wood 1 uses close shack cells, Bronze uses water-adjacent cells.
- **Decision priority chain** (`_decide`): planter task → DROP → HARVEST → opportunistic PLANT → CHOP → MINE → target → fallback.
- **Dedicated planting** (`_planter_action`, `_assign_plant_target`, `_choose_seed_type`): Wood 1 is banana-first, max 4 plants; Bronze is apple/plum/lemon/banana, max 3 plants.
- **Target scoring** (`_best_target`): value-per-round-trip-time with bonuses; Wood 1 avoids duplicate friendly targets.
- **Pressure scoring** (`_best_target`): Bronze/Silver adds a small bonus for fruiting trees near opponent trolls or on opponent-favored territory.
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

Highest-impact Silver improvements still available:

1. **Opponent diversity in evaluation**: Keep using `eval_pool.py`; pressure reached Silver despite slightly negative mirror self-play. Do not rely only on base-vs-variant paired self-play.

2. **Better opponent modeling**: Pressure is deliberately tiny. Next work should track likely opponent targets, contest valuable fruit only when travel/carry timing makes sense, and avoid the failed over-stacking behavior.

3. **Targeted tree chopping**: Prior attempts to route choppers were negative, but the idea may need better endgame timing and tree health/value modeling.

4. **Mining and iron schedule**: `mine6` over-mined and performed badly on ladder. A separate `mine_spots` bug-fix idea found that iron cells are not walkable and mining should target adjacent grass, but local impact was neutral. Revisit only with a clearer training plan.

5. **Planting selection**: Removing Bronze planting was catastrophic; cap 2/4 were slightly worse locally. The current 3-tree water orchard remains the anchor, but seed mix and spot scoring may still be worth exploring.

## How to Use This When Coming Back

1. Read this file for orientation
2. Read STRATEGY.md for "how it decides" and "what to improve"
3. Read EVAL.md for "how to test" and ITERATE.md for "how to iterate"
4. Edit arena_bot.py, test with `./run.sh` and `self_play.py`, iterate
