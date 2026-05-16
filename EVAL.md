# Evaluation & Debugging Guide

## Running the Bot

```bash
# Arena bot vs examplebot (quick Bronze test)
./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 3

# Arena bot vs examplebot (quick Wood 1 test)
./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 2

# Arena bot vs configurable bot
./run.sh "python3 /work/arena_bot.py" "python3 /work/bot.py --config /work/versions/v001.json" 42 3

# Configurable bot vs itself
./run.sh "python3 /work/bot.py" "python3 /work/bot.py" 42

# With game replay log
LOG=logs/match.json ./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 3

# With web viewer (http://localhost:8888/test.html)
SERVER=1 LOG=logs/replay.json ./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 3

# Different seed or league
./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 99 2
./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 99 3
```

All paths inside the Docker container are relative to `/work/`, which maps to the project root. So `python3 /work/arena_bot.py` is the project's `arena_bot.py`.

**Use `arena_bot.py` for the CodinGame arena.** Use `bot.py --config` for self-play testing.

League reminders:
- League 2 / Wood 1: 100 turns, fruit-only scoring, no water/iron/wood.
- League 3 / Bronze: 300 turns, water, iron, chop/mine, wood scores 4.

## Batch Testing

```bash
# Quick win-rate test across 30 seeds
wins=0; losses=0; ties=0
for seed in $(seq 1 30); do
    result=$(./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" $seed 3 2>&1 | grep -v WARNING)
    p0=$(echo "$result" | head -1)
    p1=$(echo "$result" | head -2 | tail -1)
    if [ "$p0" -gt "$p1" ]; then wins=$((wins+1))
    elif [ "$p0" -lt "$p1" ]; then losses=$((losses+1))
    else ties=$((ties+1)); fi
done
echo "W:$wins L:$losses T:$ties"

# Crash test across 50 seeds
crashes=0
for seed in $(seq 1 50); do
    p0=$(./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" $seed 3 2>&1 | grep -v WARNING | head -1)
    [ "$p0" = "-2" ] && crashes=$((crashes+1)) && echo "CRASH seed=$seed"
done
echo "Crashes: $crashes / 50"
```

A score of `-2` means the bot crashed or timed out.

## Analyzing Game Logs

```bash
# Generate a log
LOG=logs/debug.json ./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 3

# Summarize
python3 tools/summarize_log.py logs/debug.json

# Extract game input by writing a logger bot (see tools/example_logger_bot.py)
```

### Log Format

The JSON log contains:
- `scores`: `{"0": N, "1": M}` — final scores
- `uinput`: `["seed=N\n"]` — random seed
- `errors`: per-player error messages (timeouts, invalid actions)
- `views`: render frames for the web viewer (not directly useful for bot debugging)

### Logger Bot Pattern

To capture what your bot sees each turn, write input to a file inside the Docker container:

```python
import sys
LOG = "/work/logs/bot_debug.log"
log = open(LOG, "w")

while True:
    # ... parse input ...
    log.write(f"TURN {turn}: my_resources={my_inv}\n")
    log.flush()
    print("MOVE 0 10 5")
```

The file will be at `logs/bot_debug.log` in the project root since `/work/` maps there.

## Web Viewer

Run with `SERVER=1`:

```bash
SERVER=1 LOG=logs/replay.json ./run.sh "python3 /work/arena_bot.py" "python3 /work/examplebot.py" 42 3
```

Then open **http://localhost:8888/test.html** in a browser. The game completes in ~1 second; the viewer is a replay system (not live). It provides:
- Play/pause/step controls
- Zoom and pan
- Entity tooltips (click on trolls/trees)
- Score display
- Game speed control

The viewer page loads external JS from CDN (jQuery, Angular) so it needs internet access.

## Self-Play Testing

```bash
# Arena bot vs baseline, Wood 1 rules (50 seeds)
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --league 2

# Arena bot vs baseline, Bronze rules (50 seeds)
python3 self_play.py --bot1 "python3 /work/arena_bot.py" --bot2 "python3 /work/bot.py" --seeds 50 --league 3

# Config-based A/B testing
python3 self_play.py v001 v002 --seeds 30

# Iteration workflow
python3 iterate.py status          # show champion/challenger
python3 iterate.py run --seeds 30   # run champion vs challenger
python3 iterate.py promote v002     # promote challenger
```

See **ITERATE.md** for full documentation.

## Performance

Each turn has a 50ms time limit (1000ms for the first turn). The bot's BFS caching means turn 1 is slightly slower (all BFS computations happen), but subsequent turns are fast since distance maps are cached. On a 22×11 grid, BFS is negligible.

Typical timing per turn: <1ms. No timeouts observed across 1000+ games. Zero crashes across 50 seeds tested.

## Common Issues

### Bot crashes (score = -2)

- **IndexError on `near_water`/`walkable`**: The grid is `width × height` (x first, then y). Arrays must be `[width][height]`. Common mistake: `[[False]*width for _ in range(height)]` — this is `[y][x]`, not `[x][y]`.
- **Wrong resource index**: The protocol gives `plum lemon apple banana iron wood` (6 values). Training cost is a 4-tuple `(plum, lemon, apple, iron)` — don't index with `range(6)`.
- **Wood 1 reserved fields**: In league 2, iron/wood inventory and carry fields are reserved zeros. Do not require iron to train in Wood 1.
- **Reading opponent as player 1**: In the troll input, `player=0` is always **your** trolls, `player=1` is opponent. This is true regardless of whether you're P0 or P1.
- **Same-troll double action**: The referee rejects using the same troll twice in one turn. Do not emit same-troll `MOVE;HARVEST`, `MOVE;DROP`, `MOVE;PICK`, etc.

### Bot not scoring

- **DROP requires adjacency**: Trolls must be *next to* the shack (not on it) to DROP. Trolls start on the shack cell but can't walk back onto it.
- **HARVEST requires same cell**: The troll must be on the exact same cell as the tree.
- **CHOP requires same cell and chopPower > 0**: Trolls with chopPower=0 can't chop.
- **MINE requires adjacency to iron cell**: The troll must be *next to* an `+` cell, and have chopPower > 0.

### Bot goes to wrong location

- **Shack cell is not walkable**: The `0`/`1` cells are not in `walkable`. BFS must handle this: trolls start on the shack, but their first move must go to an adjacent walkable cell.
- **Iron cells are not walkable**: `+` cells are impassable. Trolls mine from an adjacent grass cell.
