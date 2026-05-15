# CodinGame Troll Farm Bot

Bot for the [CodinGame Spring Challenge 2026 — Troll Farm](https://www.codingame.com/contests/spring-challenge-2026-troller-farm).

## Quick Start

```bash
# Run a match against the example bot
./run.sh "python3 /work/bot.py" "python3 /work/examplebot.py" 42

# Watch the replay (open http://localhost:8888/test.html)
SERVER=1 ./run.sh "python3 /work/bot.py" "python3 /work/examplebot.py" 42

# Save a game log for analysis
LOG=logs/match.json ./run.sh "python3 /work/bot.py" "python3 /work/examplebot.py" 42
python3 tools/summarize_log.py logs/match.json
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

- **30W-0L** vs examplebot across 50 seeds (avg margin +83), 0 crashes
- Strategy: greedy target scoring + aggressive training + late-game chopping
- Major gaps: no PLANT, no PICK, no opponent modeling, no cooldown prediction

## Project Structure

```
.
├── AGENTS.md             # **Start here** — project overview, architecture, how to modify bot
├── bot.py               # Our bot (Python 3, no dependencies)
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