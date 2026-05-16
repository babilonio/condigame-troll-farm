"""
Troll Farm Bot v4 - Configurable competitive strategy

Supports --config <path> to load strategy parameters from a JSON file.
Without --config, uses built-in defaults (matching v001-baseline).

Core strategy:
1. Train cheap trolls aggressively (growth is exponential)
2. Each troll does: go to tree → harvest → go to shack → drop → repeat
3. Coordinate: spread trolls across different trees
4. Chop trees late game for wood value (4pts)
5. Mine iron when needed for training
"""

import sys
import json
import os
from collections import deque

PLUM, LEMON, APPLE, BANANA, IRON, WOOD = 0, 1, 2, 3, 4, 5
TREE_TO_ITEM = {"PLUM": 0, "LEMON": 1, "APPLE": 2, "BANANA": 3}
DX = [0, 1, 0, -1]
DY = [1, 0, -1, 0]
PLANT_COOLDOWN = [8, 8, 9, 6]
PLANT_WATER_BOOST = [5, 5, 7, 2]

DEFAULT_CONFIG = {
    "name": "default",
    "training": {
        "max_trolls": 8,
        "phase_thresholds": [20, 80],
        "early_configs": [
            [1, 1, 1, 0], [2, 1, 1, 0], [1, 2, 1, 0],
            [1, 1, 2, 0], [1, 1, 1, 1], [2, 2, 1, 0],
            [1, 2, 2, 0], [2, 1, 2, 0]
        ],
        "mid_configs": [
            [2, 2, 1, 0], [2, 1, 2, 0], [1, 2, 2, 0],
            [2, 2, 2, 0], [2, 1, 1, 0], [1, 1, 1, 0],
            [2, 2, 1, 1], [2, 1, 2, 1], [1, 2, 2, 1]
        ],
        "late_configs": [
            [2, 2, 2, 1], [2, 2, 1, 1], [2, 1, 2, 1],
            [1, 2, 2, 1], [2, 2, 2, 0], [3, 2, 1, 0],
            [2, 3, 2, 0]
        ]
    },
    "scoring": {
        "reach_bonus": 2.0,
        "closer_bonus": 0.2,
        "water_bonus": 0.1,
        "spread_penalty": 0.7,
        "iron_base_score": 3.0,
        "iron_threshold": 4,
        "future_fruit_cd_threshold": 2,
        "future_fruit_large_tree": 1.0,
        "future_fruit_medium_tree": 0.3
    },
    "chop": {
        "start_turn": 200,
        "wood_value": 4,
        "wood_vs_fruit_ratio": 1.0
    },
    "mining": {
        "iron_threshold_base": 3
    }
}


class Bot:
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        self.scor = self.config["scoring"]
        self.chopc = self.config["chop"]
        self.minec = self.config["mining"]
        self.trainc = self.config["training"]

        self.width, self.height = map(int, input().split())
        self.grid = []
        for _ in range(self.height):
            self.grid.append(input())

        self.my_shack = None
        self.opp_shack = None
        self.walkable = [[False] * self.height for _ in range(self.width)]
        self.iron_cells = set()
        self.near_water = [[False] * self.height for _ in range(self.width)]
        self._bfs_cache = {}

        for x in range(self.width):
            for y in range(self.height):
                ch = self.grid[y][x]
                if ch == '.':
                    self.walkable[x][y] = True
                elif ch == '0':
                    self.my_shack = (x, y)
                elif ch == '1':
                    self.opp_shack = (x, y)
                elif ch == '+':
                    self.iron_cells.add((x, y))

        for x in range(self.width):
            for y in range(self.height):
                for d in range(4):
                    nx, ny = x + DX[d], y + DY[d]
                    if 0 <= nx < self.width and 0 <= ny < self.height and self.grid[ny][nx] == '~':
                        self.near_water[x][y] = True

        sx, sy = self.my_shack
        self.shack_nbrs = []
        for d in range(4):
            nx, ny = sx + DX[d], sy + DY[d]
            if 0 <= nx < self.width and 0 <= ny < self.height and self.walkable[nx][ny]:
                self.shack_nbrs.append((nx, ny))

        ox, oy = self.opp_shack
        self.opp_shack_nbrs = []
        for d in range(4):
            nx, ny = ox + DX[d], oy + DY[d]
            if 0 <= nx < self.width and 0 <= ny < self.height and self.walkable[nx][ny]:
                self.opp_shack_nbrs.append((nx, ny))

    def bfs(self, sx, sy, is_shack=False, shack_nbrs=None):
        key = (sx, sy)
        if key in self._bfs_cache:
            return self._bfs_cache[key]

        dist = [[-1] * self.height for _ in range(self.width)]
        queue = deque()

        if self.walkable[sx][sy]:
            dist[sx][sy] = 0
            queue.append((sx, sy))
        elif is_shack and shack_nbrs:
            for nx, ny in shack_nbrs:
                if dist[nx][ny] == -1:
                    dist[nx][ny] = 1
                    queue.append((nx, ny))

        while queue:
            x, y = queue.popleft()
            for d in range(4):
                nx, ny = x + DX[d], y + DY[d]
                if 0 <= nx < self.width and 0 <= ny < self.height and dist[nx][ny] == -1 and self.walkable[nx][ny]:
                    dist[nx][ny] = dist[x][y] + 1
                    queue.append((nx, ny))

        self._bfs_cache[key] = dist
        return dist

    def dist(self, d, x, y):
        if 0 <= x < self.width and 0 <= y < self.height and d[x][y] >= 0:
            return d[x][y]
        return 9999

    def turn(self, turn_num):
        my_inv = list(map(int, input().split()))
        opp_inv = list(map(int, input().split()))

        tree_count = int(input())
        trees = []
        for _ in range(tree_count):
            parts = input().split()
            trees.append({
                'type': parts[0], 'ti': TREE_TO_ITEM[parts[0]],
                'x': int(parts[1]), 'y': int(parts[2]),
                'size': int(parts[3]), 'health': int(parts[4]),
                'fruits': int(parts[5]), 'cd': int(parts[6]),
            })

        troll_count = int(input())
        my_trolls = []
        all_trolls = []
        for _ in range(troll_count):
            p = list(map(int, input().split()))
            troll = {
                'id': p[0], 'player': p[1],
                'x': p[2], 'y': p[3],
                'speed': p[4], 'carry_cap': p[5],
                'harvest': p[6], 'chop': p[7],
                'carry': list(p[8:14]),
                'carry_total': sum(p[8:14]),
                'free_carry': p[5] - sum(p[8:14]),
            }
            all_trolls.append(troll)
            if troll['player'] == 0:
                my_trolls.append(troll)

        actions = []
        sx, sy = self.my_shack
        shack_dist = self.bfs(sx, sy, True, self.shack_nbrs)
        targeted_trees = {}

        for troll in my_trolls:
            action = self._decide(troll, trees, my_inv, all_trolls, shack_dist, turn_num, targeted_trees)
            if action:
                actions.append(action)
                if action.startswith("MOVE"):
                    parts = action.split()
                    if len(parts) >= 4:
                        try:
                            tx, ty = int(parts[2]), int(parts[3])
                            targeted_trees[(tx, ty)] = targeted_trees.get((tx, ty), 0) + 1
                        except:
                            pass

        train = self._consider_training(my_inv, my_trolls, turn_num)
        if train:
            actions.append(train)

        print(";".join(actions) if actions else "WAIT")
        sys.stdout.flush()

    def _near_shack(self, x, y):
        sx, sy = self.my_shack
        return abs(x - sx) + abs(y - sy) <= 1

    def _on_shack(self, x, y):
        return (x, y) == self.my_shack

    def _decide(self, troll, trees, my_inv, all_trolls, shack_dist, turn, targeted):
        tid = troll['id']
        tx, ty = troll['x'], troll['y']
        free = troll['free_carry']
        harvest = troll['harvest']
        chop = troll['chop']
        speed = troll['speed']
        ct = troll['carry_total']
        sx, sy = self.my_shack

        # 1. DROP if carrying and near shack
        if ct > 0 and self._near_shack(tx, ty):
            return f"DROP {tid}"

        # 2. HARVEST if on tree with fruits and have capacity
        if free > 0 and harvest > 0:
            for tree in trees:
                if tree['x'] == tx and tree['y'] == ty and tree['fruits'] > 0:
                    return f"HARVEST {tid}"

        # 3. CHOP if on a tree and late game
        if chop > 0 and turn > self.chopc['start_turn']:
            for tree in trees:
                if tree['x'] == tx and tree['y'] == ty and tree['health'] > 0:
                    wood_gain = min(tree['size'], free)
                    if wood_gain > 0:
                        remaining_fruit = tree['fruits']
                        if wood_gain * self.chopc['wood_value'] > remaining_fruit * self.chopc['wood_vs_fruit_ratio']:
                            return f"CHOP {tid}"

        # 4. MINE if near iron and need it
        n_trolls = len([t for t in all_trolls if t['player'] == 0])
        if chop > 0 and free > 0 and my_inv[IRON] < max(self.minec['iron_threshold_base'], n_trolls):
            for ix, iy in self.iron_cells:
                if abs(tx - ix) + abs(ty - iy) <= 1:
                    return f"MINE {tid}"

        # 5. If carrying items, return to shack
        if ct > 0:
            return self._move_toward(tid, tx, ty, sx, sy, shack_dist)

        # 6. Find best target
        target = self._best_target(troll, trees, my_inv, all_trolls, shack_dist, turn, targeted)
        if target:
            bx, by = target
            return f"MOVE {tid} {bx} {by}"

        # 7. Fallback
        return f"MOVE {tid} {self.width // 2} {self.height // 2}"

    def _move_toward(self, tid, tx, ty, gx, gy, shack_dist):
        sx, sy = self.my_shack
        if (gx, gy) == (sx, sy) or self._near_shack(gx, gy):
            best_nbr = None
            best_d = 9999
            troll_dist = self.bfs(tx, ty)
            for nx, ny in self.shack_nbrs:
                d = self.dist(troll_dist, nx, ny)
                if d < best_d:
                    best_d = d
                    best_nbr = (nx, ny)
            if best_nbr and best_d < 9999:
                return f"MOVE {tid} {best_nbr[0]} {best_nbr[1]}"

        return f"MOVE {tid} {gx} {gy}"

    def _best_target(self, troll, trees, my_inv, all_trolls, shack_dist, turn, targeted):
        tx, ty = troll['x'], troll['y']
        free = troll['free_carry']
        harvest = troll['harvest']
        speed = troll['speed']
        sc = self.scor

        on_shack = (tx, ty) == self.my_shack
        if on_shack:
            troll_dist = shack_dist
        else:
            troll_dist = self.bfs(tx, ty)

        def d_to(x, y):
            if on_shack:
                return self.dist(shack_dist, x, y) + 1
            return self.dist(troll_dist, x, y)

        best_score = -9999
        best_pos = None

        for tree in trees:
            tree_x, tree_y = tree['x'], tree['y']
            d_t = d_to(tree_x, tree_y)
            d_s = self.dist(shack_dist, tree_x, tree_y)

            if d_t >= 9999 or d_s >= 9999:
                continue

            harvestable = min(tree['fruits'], free, harvest) if free > 0 and harvest > 0 else 0

            future_fruits = 0
            if harvestable == 0 and free > 0 and harvest > 0 and tree['size'] >= 2:
                eff_speed = max(speed, 1)
                turns_to_reach = max(1, d_t // eff_speed)
                if tree['cd'] > 0 and tree['cd'] <= turns_to_reach + sc['future_fruit_cd_threshold']:
                    if tree['size'] >= 4:
                        future_fruits = sc['future_fruit_large_tree']
                    elif tree['size'] >= 2:
                        future_fruits = sc['future_fruit_medium_tree']

            total_value = harvestable + future_fruits
            if total_value <= 0 and tree['fruits'] <= 0:
                continue

            eff_speed = max(speed, 1)
            travel_to = max(1, d_t / eff_speed)
            travel_back = max(1, d_s / eff_speed)
            total_time = travel_to + travel_back + 2

            score = total_value / max(total_time, 1)

            if d_t <= speed:
                score += sc['reach_bonus']

            key = (tree_x, tree_y)
            trolls_on = targeted.get(key, 0)
            if trolls_on > 0:
                score *= sc['spread_penalty']

            opp_dist = abs(tree_x - self.opp_shack[0]) + abs(tree_y - self.opp_shack[1])
            my_dist = d_t
            if my_dist < opp_dist:
                score += sc['closer_bonus']

            if self.near_water[tree_x][tree_y]:
                score += sc['water_bonus']

            if score > best_score:
                best_score = score
                best_pos = (tree_x, tree_y)

        # Consider iron if we need it
        if troll['chop'] > 0 and free > 0 and my_inv[IRON] < sc['iron_threshold']:
            for ix, iy in self.iron_cells:
                d = d_to(ix, iy)
                if d < 9999:
                    iron_score = sc['iron_base_score'] / max(d / max(speed, 1), 1)
                    if iron_score > best_score:
                        best_score = iron_score
                        best_pos = (ix, iy)

        return best_pos

    def _training_cost(self, n, m, c, h, ch):
        base = n
        return (base + m * m, base + c * c, base + h * h, base + ch * ch)

    def _consider_training(self, inv, trolls, turn):
        n = len(trolls)
        if n >= self.trainc['max_trolls']:
            return None

        thresholds = self.trainc['phase_thresholds']
        if turn <= thresholds[0]:
            configs = self.trainc['early_configs']
        elif turn <= thresholds[1]:
            configs = self.trainc['mid_configs']
        else:
            configs = self.trainc['late_configs']

        for config in configs:
            m, c, h, ch = config
            cost = self._training_cost(n, m, c, h, ch)
            can_afford = (inv[PLUM] >= cost[0] and inv[LEMON] >= cost[1] and
                         inv[APPLE] >= cost[2] and inv[IRON] >= cost[3])
            if can_afford:
                return f"TRAIN {m} {c} {h} {ch}"

        return None


def load_config(path):
    with open(path, 'r') as f:
        cfg = json.load(f)
    # Merge with defaults so partial configs work
    merged = {}
    for section in DEFAULT_CONFIG:
        if section == 'name':
            merged[section] = cfg.get(section, DEFAULT_CONFIG[section])
        elif isinstance(DEFAULT_CONFIG[section], dict):
            merged[section] = dict(DEFAULT_CONFIG[section])
            merged[section].update(cfg.get(section, {}))
            # Special handling for training configs (lists of lists)
            for key in ['early_configs', 'mid_configs', 'late_configs']:
                if key in cfg.get(section, {}):
                    merged[section][key] = cfg[section][key]
    return merged


def main():
    config = None
    if '--config' in sys.argv:
        idx = sys.argv.index('--config')
        if idx + 1 < len(sys.argv):
            config_path = sys.argv[idx + 1]
            config = load_config(config_path)

    bot = Bot(config)
    turn = 0
    while True:
        turn += 1
        bot.turn(turn)


if __name__ == "__main__":
    main()