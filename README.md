# CodinGame Troll Farm Bot

Bot for the [CodinGame Spring Challenge 2026 — Troll Farm](https://www.codingame.com/contests/spring-challenge-2026-troller-farm).

Current ladder status: promoted from **Wood 1** to **Bronze**. The current submission file is `arena_bot.py`.

## Quick Start

```bash
# Run a match against the example bot in Bronze rules
./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 3

# Watch the replay (open http://localhost:8888/test.html)
SERVER=1 ./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 3

# Save a game log for analysis
LOG=logs/match.json ./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 3
python3 tools/summarize_log.py logs/match.json

# Batch-test Wood 1 rules
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --league 2

# Batch-test Bronze rules
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --league 3
```

Output: two lines with player scores, then `seed=N`. A score of `-2` means that player's bot crashed.

## Documentation

| File | Contents |
|------|----------|
| [AGENTS.md](AGENTS.md) | **Start here** — project overview, how pieces fit together, how to make changes, what to work on next |
| [NOTES.md](NOTES.md) | Game rules, I/O protocol, constants — everything the game gives you |
| [STRATEGY.md](STRATEGY.md) | Bot strategy deep-dive: decision flow, scoring, training logic, what we don't do yet, referee-source implications |
| [EVAL.md](EVAL.md) | How to run, batch-test, debug, and use the web viewer. Common pitfalls. |
| [run.sh](run.sh) | Docker-based match runner (all flags documented inside) |
| [bot.py](bot.py) | The bot itself |
| [examplebot.py](examplebot.py) | CodinGame's starter bot (MOVE 0 7 7 every turn) |

## Current Status

- `arena_bot.py` is the arena/submission bot.
- Reached **Bronze** after a Wood 1 rewrite.
- Wood 1 local benchmark: `arena_bot.py` vs `bot.py`, league 2, 50 seeds: **48W-2L-0T**, avg diff **+18.9**.
- Bronze local benchmark from the prior pass: `arena_bot.py` vs `bot.py`, league 3, 50 seeds: **35W-12L-3T**, avg diff **+28.1**. Re-run after current changes before relying on it.
- Strategy: league detection, dedicated early planting, target deconfliction, aggressive but league-aware training, Bronze chop/mine fallback.
- Major Bronze gaps: targeted chopping, mining based on future training, opponent contesting, richer local opponents for testing.

## Project Structure

```
.
├── AGENTS.md             # **Start here** — project overview, architecture, how to modify bot
├── arena_bot.py         # Current arena submission bot
├── bot.py               # Older configurable baseline / sparring partner
├── examplebot.py        # CodinGame starter bot
├── run.sh               # Docker-based match runner
├── tools/
│   ├── run_match.sh     # Lower-level wrapper (called by run.sh)
│   ├── summarize_log.py # Summarize JSON game log
│   └── Dockerfile.trollfarm-runner  # JRE + Python3 for Docker
├── Troll-Farm/
│   └── troll-farm-1.0-SNAPSHOT.jar  # The game referee
├── logs/                # Game logs (gitignored)
├── NOTES.md             # Game rules & protocol
├── STRATEGY.md          # Bot strategy & improvement ideas
└── EVAL.md              # Running, testing, debugging guide
```
