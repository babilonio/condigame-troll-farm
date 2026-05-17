# CodinGame Troll Farm - Bot Project

## Game Overview

Troll Farm is a 2-player turn-based strategy game from the CodinGame Spring Challenge 2026.

**Objective:** Collect more resources than your opponent. Each fruit in your shack = 1 point. Wood = 4 points. Iron = 0 points.

**Map:** A grid (width = 2×height, height 8-11) with cells: `.` grass, `~` water, `#` rock, `+` iron ore, `0`/`1` player shacks. Map is horizontally symmetric (mirrored).

**Entities:** Trolls (units) and Trees (PLUM, LEMON, APPLE, BANANA).

### Actions (semicolon-separated; each troll at most once per turn)
| Action | Description |
|--------|-------------|
| `MOVE id x y` | Move troll toward cell (x,y), up to movementSpeed cells |
| `HARVEST id` | Pick fruits from a tree on the same cell |
| `DROP id` | Drop all carried items at adjacent shack |
| `PICK id type` | Pick 1 item of type from shack |
| `TRAIN move carry harvest chop` | Spend resources to train a new troll |
| `PLANT id type` | Plant a tree on current cell (costs 1 fruit of that type) |
| `CHOP id` | Chop tree on same cell (deals chopPower damage, get wood) |
| `MINE id` | Mine iron from adjacent iron cell |
| `WAIT` | Do nothing |
| `MSG text` | Display message in replay |

### Turn Order
1. Move → 2. Harvest → 3. Plant → 4. Chop → 5. Pick → 6. Train → 7. Drop → 8. Mine → 9. Grow trees

### Trees
- Types: PLUM, LEMON, APPLE, BANANA
- Grow through sizes 1→2→3→4 (max). When at max size + cooldown=0, produce fruits (up to 3).
- Trees grow faster near water (reduced cooldown).
- Chop reduces health by chopPower. Health 0 → tree destroyed, yields size×wood.

### Training Trolls
Cost per attribute = (existing_trolls + attribute²). Resources: PLUM=movementSpeed, LEMON=carryCapacity, APPLE=harvestPower, IRON=chopPower.

### Game Length
300 turns (league 3+), or early end if no trees for 10 turns or winner is clear.

## Running the Game

```bash
# Quick test run (uses Docker)
./run.sh "python3 /work/my_bot.py" "python3 /work/examplebot.py" 42

# With game log (JSON replay)
LOG=logs/match.json ./run.sh "python3 /work/my_bot.py" "python3 /work/examplebot.py" 42

# With web viewer (port 8888)
SERVER=1 ./run.sh "python3 /work/my_bot.py" "python3 /work/examplebot.py" 42

# Summarize a game log
python3 tools/summarize_log.py logs/match.json
```

The game outputs two lines to stdout: player0_score and player1_score, then "seed=N".

## Bot I/O Protocol

### Initialization
```
width height
<height lines of map>
```
Map characters: `.`=grass, `~`=water, `#`=rock, `+`=iron, `0`=your shack, `1`=opponent shack.

### Each Turn
```
<your_resources: plum lemon apple banana iron wood>
<opponent_resources: plum lemon apple banana iron wood>
<treeCount>
<treeCount lines: type x y size health fruits cooldown>
<trollsCount>
<trollsCount lines: id player x y movementSpeed carryCapacity harvestPower chopPower carryPlum carryLemon carryApple carryBanana carryIron carryWood>
```

### Output
One line per turn. Multiple commands separated by `;`.
Example: `MOVE 0 5 3;HARVEST 1;TRAIN 2 3 1 0`

Important: the referee rejects using the same troll twice in one turn. `MOVE 0 5 3;HARVEST 0` and `MOVE 0 5 3;DROP 0` are invalid for troll 0 even though move/harvest/drop resolve in different phases.

### League Notes

- **Wood 1 / league 2**: 100 turns, height 8, no water/iron/wood, fruit-only score. Inventory/carry fields for iron and wood are reserved zeros. Training effectively costs only plum/lemon/apple because chopPower is unavailable.
- **Bronze/Silver / league 3+**: 300 turns, water, iron, chopping, mining, and wood scoring are active.

## Key Game Constants (from source)
- PLANT_COOLDOWN = [8, 8, 9, 6] (PLUM, LEMON, APPLE, BANANA)
- PLANT_WATER_COOLDOWN_BOOST = [5, 5, 7, 2] (water reduces cooldown by this)
- PLANT_MAX_SIZE = 4, PLANT_MAX_RESOURCES = 3
- PLANT_FINAL_HEALTH = [12, 12, 20, 6]
- PLANT_DELTA_HEALTH = [2, 2, 3, 1] (health gained per growth)
- WOOD_POINTS = 4, iron scores 0
- Game is 300 turns, stalls end after 10 turns with no trees
- Time limit: 1000ms first turn, 50ms per turn (3 strikes allowed)

## Project Ladder Notes

- The Wood 1 rewrite promoted the account to Bronze.
- The Bronze "pressure" variant promoted the account to Silver on May 17, 2026; latest known rank: **Silver 512/630**.
- The pressure variant is small: in Bronze/Silver target scoring, it adds modest bonuses for fruiting trees near opponent trolls and trees closer to the opponent shack. It did not change Wood 1 logic.
- `arena_bot_base.py` preserves the Bronze-promotion base. `arena_bot_silver_base.py` preserves the Silver-promotion pressure bot. Current `arena_bot.py` is the Silver pressure bot.
- `arena_bot_variant_mine6.py` is a cautionary result: local paired score looked positive, but ladder rank fell to Bronze 339/529. Do not trust mirror self-play alone.

## Iteration Lessons

- Use `paired_self_play.py` to compare variants fairly across both player orders.
- Use `eval_pool.py` before ladder probes; the Silver pressure variant looked better there even though mirror self-play was slightly negative.
- Removing Bronze planting was catastrophic locally; keep water-adjacent orchard behavior as an anchor.
- Naive stacking/contesting was bad despite harvest duplication existing in the referee.
- Iron cells are not walkable; mining requires standing on adjacent grass. The current bot can still improve here, but the tested `mine_spots` variant was locally neutral.
