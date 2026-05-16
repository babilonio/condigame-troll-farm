"""
Troll Farm Bot v5 — Arena competitive strategy

Built on proven v4 baseline with improvements:
1. Combo actions: MOVE+DROP, MOVE+HARVEST (halves round-trip time)
2. Opportunistic PLANT on good spots (grass+water near shack)
3. Growth-aware target scoring using tree cooldown
4. Smarter training: always try cheapest first, ensure chopPower trolls exist
5. Value-based chopping: only chop when wood exceeds remaining fruit potential
6. Troll cap raised to 10
"""

import sys
from collections import deque

PLUM, LEMON, APPLE, BANANA, IRON, WOOD = 0, 1, 2, 3, 4, 5
TREE_TO_ITEM = {"PLUM": 0, "LEMON": 1, "APPLE": 2, "BANANA": 3}
ITEM_TO_TREE = {0: "PLUM", 1: "LEMON", 2: "APPLE", 3: "BANANA"}
DX = [0, 1, 0, -1]
DY = [1, 0, -1, 0]


class Bot:
    def __init__(self):
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
        self.tree_cells = set()

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

        self.shack_dist = self.bfs(sx, sy, True, self.shack_nbrs)

        # Good planting spots: grass near water, close to shack
        self.plant_spots = []
        for x in range(self.width):
            for y in range(self.height):
                if (self.walkable[x][y] and self.near_water[x][y]
                        and self.dist(self.shack_dist, x, y) > 0
                        and self.dist(self.shack_dist, x, y) <= 5):
                    self.plant_spots.append((x, y))
        self.planted_cells = set()
        self.max_plants = 2

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
        self.tree_cells = set()
        for _ in range(tree_count):
            parts = input().split()
            t = {
                'type': parts[0], 'ti': TREE_TO_ITEM[parts[0]],
                'x': int(parts[1]), 'y': int(parts[2]),
                'size': int(parts[3]), 'health': int(parts[4]),
                'fruits': int(parts[5]), 'cd': int(parts[6]),
            }
            trees.append(t)
            self.tree_cells.add((t['x'], t['y']))

        troll_count = int(input())
        my_trolls = []
        opp_trolls = []
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
            else:
                opp_trolls.append(troll)

        actions = []
        sx, sy = self.my_shack
        shack_dist = self.bfs(sx, sy, True, self.shack_nbrs)
        targeted_trees = {}

        for troll in my_trolls:
            action = self._decide(troll, trees, my_inv, all_trolls, opp_trolls,
                                  shack_dist, turn_num, targeted_trees)
            if action:
                actions.append(action)
                for part in action.split(';'):
                    cmd = part.strip().split()
                    if len(cmd) >= 4 and cmd[0] == 'MOVE':
                        try:
                            mx, my_ = int(cmd[2]), int(cmd[3])
                            targeted_trees[(mx, my_)] = targeted_trees.get((mx, my_), 0) + 1
                        except (ValueError, IndexError):
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

    def _decide(self, troll, trees, my_inv, all_trolls, opp_trolls, shack_dist, turn, targeted):
        tid = troll['id']
        tx, ty = troll['x'], troll['y']
        free = troll['free_carry']
        harvest_pow = troll['harvest']
        chop_pow = troll['chop']
        speed = troll['speed']
        ct = troll['carry_total']
        carry = troll['carry']
        sx, sy = self.my_shack
        on_shack = self._on_shack(tx, ty)

        if on_shack:
            troll_dist = shack_dist
        else:
            troll_dist = self.bfs(tx, ty)

        # --- PRIORITY 1: DROP if carrying items ---
        if ct > 0:
            # Already adjacent to shack — just DROP
            if self._near_shack(tx, ty):
                return f"DROP {tid}"
            # Can reach shack neighbor this turn — MOVE+DROP combo
            if speed > 0:
                best_nbr = None
                best_d = 9999
                for nx, ny in self.shack_nbrs:
                    d = self.dist(troll_dist, nx, ny)
                    if d < best_d:
                        best_d = d
                        best_nbr = (nx, ny)
                if best_nbr and best_d <= speed:
                    return f"MOVE {tid} {best_nbr[0]} {best_nbr[1]};DROP {tid}"
            # Can't reach this turn — move toward shack
            return self._move_to_shack(tid, tx, ty, troll_dist)

        # --- PRIORITY 2: HARVEST if on tree with fruits and have capacity ---
        if free > 0 and harvest_pow > 0:
            for tree in trees:
                if tree['x'] == tx and tree['y'] == ty and tree['fruits'] > 0:
                    return f"HARVEST {tid}"

        # --- PRIORITY 2b: COMBO MOVE+HARVEST for reachable trees ---
        # Use same scoring logic as _best_target for consistency
        if free > 0 and harvest_pow > 0 and speed > 0 and not on_shack:
            best_combo = None
            best_combo_score = -9999
            eff_speed = max(speed, 1)
            for tree in trees:
                if tree['fruits'] <= 0:
                    continue
                d_t = self.dist(troll_dist, tree['x'], tree['y'])
                d_s = self.dist(shack_dist, tree['x'], tree['y'])
                if d_t <= 0 or d_t > speed or d_s >= 9999:
                    continue
                harvestable = min(tree['fruits'], free, harvest_pow)
                travel_to = max(1, d_s / eff_speed)
                travel_back = max(1, d_s / eff_speed)
                total_time = 1 + travel_back + 2  # 1 turn to reach (combo), +2 for harvest+drop
                score = harvestable / max(total_time, 1)
                score += 3.0  # big bonus for instant harvest
                spread_key = (tree['x'], tree['y'])
                trolls_on = targeted.get(spread_key, 0)
                if trolls_on > 0:
                    score *= 0.7
                if score > best_combo_score:
                    best_combo_score = score
                    best_combo = tree
            if best_combo:
                return f"MOVE {tid} {best_combo['x']} {best_combo['y']};HARVEST {tid}"

        # --- PRIORITY 3: PLANT if on good spot and carrying fruit ---
        if (turn <= 80 and len(self.planted_cells) < self.max_plants
                and self.walkable[tx][ty] and self.near_water[tx][ty]
                and (tx, ty) not in self.tree_cells
                and (tx, ty) not in self.planted_cells
                and not self._near_shack(tx, ty)):
            for fi in [APPLE, PLUM, LEMON, BANANA]:
                if carry[fi] > 0 and my_inv[fi] > 3:
                    self.planted_cells.add((tx, ty))
                    return f"PLANT {tid} {ITEM_TO_TREE[fi]}"

        # --- PRIORITY 4: CHOP if on tree and worth it ---
        if chop_pow > 0 and free > 0 and turn > 180:
            for tree in trees:
                if tree['x'] == tx and tree['y'] == ty and tree['health'] > 0:
                    wood_gain = min(tree['size'], free)
                    if wood_gain > 0:
                        # Don't chop productive trees unless very late
                        if tree['fruits'] > 0 and turn < 250:
                            continue
                        return f"CHOP {tid}"

        # Original chop logic as fallback (always chop if on tree late game)
        if chop_pow > 0 and turn > 220:
            for tree in trees:
                if tree['x'] == tx and tree['y'] == ty and tree['health'] > 0:
                    wood_gain = min(tree['size'], free)
                    if wood_gain > 0:
                        remaining_fruit = tree['fruits']
                        if wood_gain * 4 > remaining_fruit:
                            return f"CHOP {tid}"

        # --- PRIORITY 5: MINE if near iron and need it ---
        n_my = sum(1 for t in all_trolls if t['player'] == 0)
        if chop_pow > 0 and free > 0 and my_inv[IRON] < max(3, n_my):
            for ix, iy in self.iron_cells:
                if abs(tx - ix) + abs(ty - iy) <= 1:
                    return f"MINE {tid}"

        # --- PRIORITY 6: Find best target ---
        target = self._best_target(troll, trees, my_inv, all_trolls, shack_dist, turn, targeted)
        if target:
            bx, by = target
            return f"MOVE {tid} {bx} {by}"

        # --- PRIORITY 8: Fallback ---
        return f"MOVE {tid} {self.width // 2} {self.height // 2}"

    def _move_to_shack(self, tid, tx, ty, troll_dist):
        sx, sy = self.my_shack
        best_nbr = None
        best_d = 9999
        for nx, ny in self.shack_nbrs:
            d = self.dist(troll_dist, nx, ny)
            if d < best_d:
                best_d = d
                best_nbr = (nx, ny)
        if best_nbr and best_d < 9999:
            return f"MOVE {tid} {best_nbr[0]} {best_nbr[1]}"
        return f"MOVE {tid} {sx} {sy}"

    def _best_target(self, troll, trees, my_inv, all_trolls, shack_dist, turn, targeted):
        tx, ty = troll['x'], troll['y']
        free = troll['free_carry']
        harvest_pow = troll['harvest']
        speed = troll['speed']
        sx, sy = self.my_shack

        on_shack = self._on_shack(tx, ty)
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

            # Current harvestable fruits
            harvestable = min(tree['fruits'], free, harvest_pow) if free > 0 and harvest_pow > 0 else 0

            # Future fruit prediction using cooldown
            future_fruits = 0
            if harvestable == 0 and free > 0 and harvest_pow > 0 and tree['size'] >= 2:
                eff_speed = max(speed, 1)
                turns_to_reach = max(1, d_t // eff_speed)
                if tree['cd'] > 0 and tree['cd'] <= turns_to_reach + 2:
                    if tree['size'] >= 4:
                        future_fruits = 1.0
                    elif tree['size'] >= 2:
                        future_fruits = 0.3
                elif tree['cd'] <= 0 and tree['fruits'] <= 0:
                    future_fruits = 0.2

            total_value = harvestable + future_fruits
            if total_value <= 0 and tree['fruits'] <= 0:
                continue

            # Round-trip efficiency
            eff_speed = max(speed, 1)
            travel_to = max(1, d_t / eff_speed)
            travel_back = max(1, d_s / eff_speed)
            total_time = travel_to + travel_back + 2

            score = total_value / max(total_time, 1)

            # Reach bonus (same as baseline)
            if d_t <= speed:
                score += 2.0

            # Spread penalty
            key = (tree_x, tree_y)
            trolls_on = targeted.get(key, 0)
            if trolls_on > 0:
                score *= 0.7

            # Territory: prefer closer to us than opponent
            opp_dist = abs(tree_x - self.opp_shack[0]) + abs(tree_y - self.opp_shack[1])
            my_dist = d_t
            if my_dist < opp_dist:
                score += 0.2

            # Water bonus
            if self.near_water[tree_x][tree_y]:
                score += 0.1

            if score > best_score:
                best_score = score
                best_pos = (tree_x, tree_y)

        # Consider iron if needed
        n_my = len([t for t in all_trolls if t['player'] == 0])
        if troll['chop'] > 0 and free > 0 and my_inv[IRON] < max(3, n_my):
            for ix, iy in self.iron_cells:
                d = d_to(ix, iy)
                if d < 9999:
                    iron_score = 3.0 / max(d / max(speed, 1), 1)
                    if iron_score > best_score:
                        best_score = iron_score
                        best_pos = (ix, iy)

        return best_pos

    def _training_cost(self, n, m, c, h, ch):
        base = n
        return (base + m * m, base + c * c, base + h * h, base + ch * ch)

    def _consider_training(self, inv, trolls, turn):
        n = len(trolls)
        if n >= 10:
            return None

        # Ensure we have chop trolls by mid-game
        chop_count = sum(1 for t in trolls if t['chop'] > 0)

        if turn <= 20:
            # Early: maximize troll count
            configs = [
                (1, 1, 1, 0),
                (2, 1, 1, 0),
                (1, 2, 1, 0),
                (1, 1, 2, 0),
                (1, 1, 1, 1),
                (2, 2, 1, 0),
                (1, 2, 2, 0),
                (2, 1, 2, 0),
            ]
        elif turn <= 80:
            # Mid: balanced, start adding chopPower
            configs = [
                (1, 1, 1, 0),
                (1, 2, 1, 0),
                (2, 1, 1, 0),
                (1, 1, 2, 0),
                (2, 2, 1, 0),
                (2, 1, 2, 0),
                (1, 2, 2, 0),
                (2, 2, 2, 0),
                (1, 2, 1, 1),
                (2, 2, 1, 1),
            ]
        else:
            # Late: include chopPower
            configs = [
                (1, 1, 1, 0),
                (1, 2, 1, 0),
                (2, 2, 1, 0),
                (1, 2, 2, 0),
                (2, 2, 2, 0),
                (2, 2, 1, 1),
                (2, 1, 2, 1),
                (1, 2, 2, 1),
                (2, 2, 2, 1),
            ]

        for config in configs:
            m, c, h, ch = config
            # Skip chopPower configs when we have no iron
            if ch > 0 and inv[IRON] < n + ch * ch:
                continue
            cost = self._training_cost(n, m, c, h, ch)
            can_afford = (inv[PLUM] >= cost[0] and inv[LEMON] >= cost[1] and
                         inv[APPLE] >= cost[2] and inv[IRON] >= cost[3])
            if can_afford:
                return f"TRAIN {m} {c} {h} {ch}"

        return None


def main():
    bot = Bot()
    turn = 0
    while True:
        turn += 1
        bot.turn(turn)


if __name__ == "__main__":
    main()