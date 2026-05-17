# CodinGame Troll Farm Bot

Bot for the [CodinGame Spring Challenge 2026 — Troll Farm](https://www.codingame.com/contests/spring-challenge-2026-troller-farm).

Current ladder status: promoted to **Silver**, latest known rank **512/630**. The current submission file is `arena_bot.py`.

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

# Batch-test Bronze/Silver rules
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --league 3

# Fair arena A/B against the preserved Bronze base
python3 paired_self_play.py arena_bot.py --base arena_bot_base.py --seeds 20 --start 1 --league 3 --jobs 8

# Broader ladder-proxy pool eval
python3 eval_pool.py arena_bot.py --opponents config config_v001 config_v002 backup --seeds 12 --start 1 --league 3 --jobs 10
```

Output: two lines with player scores, then `seed=N`. A score of `-2` means that player's bot crashed.

## Documentation

| File | Contents |
|------|----------|
| [AGENTS.md](AGENTS.md) | **Start here** — project overview, how pieces fit together, how to make changes, what to work on next |
| [NOTES.md](NOTES.md) | Game rules, I/O protocol, constants — everything the game gives you |
| [STRATEGY.md](STRATEGY.md) | Bot strategy deep-dive: decision flow, scoring, training logic, what we don't do yet, referee-source implications |
| [EVAL.md](EVAL.md) | How to run, batch-test, debug, and use the web viewer. Common pitfalls. |
| [ARENA_ITERATION.md](ARENA_ITERATION.md) | Single-file arena variant history, ladder notes, and promotion/rejection decisions |
| [run.sh](run.sh) | Docker-based match runner (all flags documented inside) |
| [bot.py](bot.py) | The bot itself |
| [examplebot.py](examplebot.py) | CodinGame's starter bot (MOVE 0 7 7 every turn) |

## Current Status

- `arena_bot.py` is the arena/submission bot.
- Reached **Silver** with the Bronze pressure variant.
- `arena_bot_base.py` preserves the Bronze-promotion baseline; do not overwrite it casually.
- `arena_bot_silver_base.py` preserves the Silver-promotion pressure bot; use it as the next anchor.
- Wood 1 local benchmark: `arena_bot.py` vs `bot.py`, league 2, 50 seeds: **48W-2L-0T**, avg diff **+18.9**.
- Pressure pool benchmark: `arena_bot.py` vs config/v001/v002/backup pool, league 3, 12 seeds in both orders: **88W-8L**, avg diff **+47.7**.
- Strategy: league detection, dedicated early planting, target deconfliction, aggressive but league-aware training, Bronze/Silver chop/mine fallback, modest opponent-pressure target scoring.
- Major Silver gaps: stronger opponent modeling, better local opponent pool, purposeful mining/chopping schedules.

## Project Structure

```
.
├── AGENTS.md             # **Start here** — project overview, architecture, how to modify bot
├── arena_bot.py         # Current arena submission bot
├── arena_bot_base.py    # Preserved Bronze-promotion base strategy
├── arena_bot_silver_base.py # Preserved Silver-promotion pressure strategy
├── arena_bot_variant_*.py # Named experiments and rejected/proven variants
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
├── ARENA_ITERATION.md   # Arena variant history and ladder notes
└── EVAL.md              # Running, testing, debugging guide
```
