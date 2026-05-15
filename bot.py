#!/usr/bin/env python3
"""
Troll Farm Bot v3 - Competitive strategy

Core strategy:
1. Train cheap trolls aggressively (growth is exponential)
2. Each troll does: go to tree → harvest → go to shack → drop → repeat
3. Coordinate: spread trolls across different trees
4. Chop trees late game for wood value (4pts)
5. Mine iron when needed for training
"""

import sys
from collections import deque

PLUM, LEMON, APPLE, BANANA, IRON, WOOD = 0, 1, 2, 3, 4, 5
TREE_TO_ITEM = {"PLUM": 0, "LEMON": 1, "APPLE": 2, "BANANA": 3}
DX = [0, 1, 0, -1]
DY = [1, 0, -1, 0]
PLANT_COOLDOWN = [8, 8, 9, 6]
PLANT_WATER_BOOST = [5, 5, 7, 2]


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

        # For opponent distance calculations
        ox, oy = self.opp_shack
        self.opp_shack_nbrs = []
        for d in range(4):
            nx, ny = ox + DX[d], oy + DY[d]
            if 0 <= nx < self.width and 0 <= ny < self.height and self.walkable[nx][ny]:
                self.opp_shack_nbrs.append((nx, ny))

    def bfs(self, sx, sy, is_shack=False, shack_nbrs=None):
        """BFS from (sx,sy). Handles shack cells specially."""
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
        """Get distance from dist map, return 9999 if unreachable."""
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

        # Precompute distance maps we'll need
        shack_dist = self.bfs(sx, sy, True, self.shack_nbrs)

        # Track which trees are targeted by which trolls this turn
        # (we can still share - just don't all pile on one)
        targeted_trees = {}  # (x,y) -> count of trolls targeting

        for troll in my_trolls:
            action = self._decide(troll, trees, my_inv, all_trolls, shack_dist, turn_num, targeted_trees)
            if action:
                actions.append(action)
                # Track harvest targets
                if action.startswith("HARVEST"):
                    # This troll is harvesting at its current location
                    pass
                elif action.startswith("MOVE"):
                    # Parse target
                    parts = action.split()
                    if len(parts) >= 4:
                        try:
                            tx, ty = int(parts[2]), int(parts[3])
                            targeted_trees[(tx, ty)] = targeted_trees.get((tx, ty), 0) + 1
                        except:
                            pass

        # Consider training a new troll
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
            # If on a tree with no fruits but close to capacity, move on
            # (don't wait for fruit growth)

        # 3. CHOP if on a tree and it's late game
        if chop > 0 and turn > 200:
            for tree in trees:
                if tree['x'] == tx and tree['y'] == ty and tree['health'] > 0:
                    wood_gain = min(tree['size'], free)
                    if wood_gain > 0:
                        # Chop if wood value exceeds fruit potential
                        remaining_fruit = tree['fruits']
                        if wood_gain * 4 > remaining_fruit:
                            return f"CHOP {tid}"

        # 4. MINE if near iron and need it
        if chop > 0 and free > 0 and my_inv[IRON] < max(3, len([t for t in all_trolls if t['player'] == 0])):
            for ix, iy in self.iron_cells:
                if abs(tx - ix) + abs(ty - iy) <= 1:
                    return f"MINE {tid}"

        # 5. If carrying items, return to shack
        if ct > 0:
            return self._move_toward(tid, tx, ty, sx, sy, shack_dist)

        # 6. Find best target to move to
        target = self._best_target(troll, trees, my_inv, all_trolls, shack_dist, turn, targeted)
        if target:
            bx, by = target
            return f"MOVE {tid} {bx} {by}"

        # 7. Fallback
        return f"MOVE {tid} {self.width // 2} {self.height // 2}"

    def _move_toward(self, tid, tx, ty, gx, gy, shack_dist):
        """Move toward a goal. Game engine handles pathfinding."""
        # If we need to reach shack area, move toward nearest shack neighbor
        sx, sy = self.my_shack
        if (gx, gy) == (sx, sy) or self._near_shack(gx, gy):
            # Find closest shack neighbor
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
        """
        Score all targets and return the best position.
        Tries to spread trolls across different trees.
        """
        tx, ty = troll['x'], troll['y']
        free = troll['free_carry']
        harvest = troll['harvest']
        speed = troll['speed']
        sx, sy = self.my_shack

        # Get distance from troll's position
        on_shack = (tx == sx and ty == sy)
        if on_shack:
            troll_dist = shack_dist  # from shack neighbors
        else:
            troll_dist = self.bfs(tx, ty)

        def d_to(x, y):
            """Distance from troll to (x,y)."""
            if on_shack:
                return self.dist(shack_dist, x, y) + 1
            return self.dist(troll_dist, x, y)

        best_score = -9999
        best_pos = None

        for tree in trees:
            tree_x, tree_y = tree['x'], tree['y']
            d_t = d_to(tree_x, tree_y)
            d_s = self.dist(shack_dist, tree_x, tree_y)  # tree to shack

            if d_t >= 9999 or d_s >= 9999:
                continue

            # Calculate harvestable fruits
            harvestable = min(tree['fruits'], free, harvest) if free > 0 and harvest > 0 else 0

            # If tree has no fruits now, estimate future value
            future_fruits = 0
            if harvestable == 0 and free > 0 and harvest > 0 and tree['size'] >= 2:
                # Tree might grow or produce fruits while we walk there
                eff_speed = max(speed, 1)
                turns_to_reach = max(1, d_t // eff_speed)
                if tree['cd'] > 0 and tree['cd'] <= turns_to_reach + 2:
                    if tree['size'] >= 4:
                        future_fruits = 1  # likely to have 1+ fruit by then
                    elif tree['size'] >= 2:
                        future_fruits = 0.3  # might grow to next size

            total_value = harvestable + future_fruits
            if total_value <= 0 and tree['fruits'] <= 0:
                continue

            # Round-trip cost
            eff_speed = max(speed, 1)
            travel_to = max(1, d_t / eff_speed)
            travel_back = max(1, d_s / eff_speed)
            total_time = travel_to + travel_back + 2  # +1 harvest, +1 drop

            # Score: value per unit time
            score = total_value / max(total_time, 1)

            # Preference adjustments
            if d_t <= speed:
                score += 2.0  # can reach this turn!

            # Prefer trees we haven't over-assigned
            key = (tree_x, tree_y)
            trolls_on = targeted.get(key, 0)
            if trolls_on > 0:
                score *= 0.7  # discourage but don't eliminate

            # Prefer trees closer to us than opponent
            # Use simpler heuristic: manhattan from opponent shack
            opp_dist = abs(tree_x - self.opp_shack[0]) + abs(tree_y - self.opp_shack[1])
            my_dist = d_t
            if my_dist < opp_dist:
                score += 0.2

            # Near-water bonus (faster growth = more future value)
            if self.near_water[tree_x][tree_y]:
                score += 0.1

            if score > best_score:
                best_score = score
                best_pos = (tree_x, tree_y)

        # Consider iron if we need it
        if troll['chop'] > 0 and free > 0 and my_inv[IRON] < 4:
            n_trolls = sum(1 for t in all_trolls if t['player'] == 0)
            for ix, iy in self.iron_cells:
                d = d_to(ix, iy)
                if d < 9999:
                    # Iron is critical for training trolls with chopPower
                    score = 3.0 / max(d / max(speed, 1), 1)
                    if score > best_score:
                        best_score = score
                        best_pos = (ix, iy)

        return best_pos

    def _training_cost(self, n, m, c, h, ch):
        base = n
        return (base + m*m, base + c*c, base + h*h, base + ch*ch)

    def _consider_training(self, inv, trolls, turn):
        n = len(trolls)
        if n >= 8:
            return None

        # Configs: (move_speed, carry_capacity, harvest_power, chop_power)
        # Ordered by preference for current game phase
        if turn <= 20:
            # Early: maximize number of trolls, go cheap
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
            # Mid: balanced growth
            configs = [
                (2, 2, 1, 0),
                (2, 1, 2, 0),
                (1, 2, 2, 0),
                (2, 2, 2, 0),
                (2, 1, 1, 0),
                (1, 1, 1, 0),
                (2, 2, 1, 1),
                (2, 1, 2, 1),
                (1, 2, 2, 1),
            ]
        else:
            # Late: include chop for wood
            configs = [
                (2, 2, 2, 1),
                (2, 2, 1, 1),
                (2, 1, 2, 1),
                (1, 2, 2, 1),
                (2, 2, 2, 0),
                (3, 2, 1, 0),
                (2, 3, 2, 0),
            ]

        for config in configs:
            m, c, h, ch = config
            cost = self._training_cost(n, m, c, h, ch)
            can_afford = (inv[PLUM] >= cost[0] and inv[LEMON] >= cost[1] and
                         inv[APPLE] >= cost[2] and inv[IRON] >= cost[3])
            if can_afford:
                # Always train if we can afford it - more trolls = more actions
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