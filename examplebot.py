import sys
import math

# Auto-generated code below aims at helping you parse
# the standard input according to the problem statement.

width, height = [int(i) for i in input().split()]
for i in range(height):
    line = input()

# game loop
while True:
    for i in range(2):
        plum, lemon, apple, banana, iron, wood = [int(j) for j in input().split()]
    trees_count = int(input())
    for i in range(trees_count):
        inputs = input().split()
        _type = inputs[0]
        x = int(inputs[1])
        y = int(inputs[2])
        size = int(inputs[3])
        health = int(inputs[4])
        fruits = int(inputs[5])
        cooldown = int(inputs[6])
    trolls_count = int(input())
    for i in range(trolls_count):
        _id, player, x, y, movement_speed, carry_capacity, harvest_power, chop_power, carry_plum, carry_lemon, carry_apple, carry_banana, carry_iron, carry_wood = [int(j) for j in input().split()]

    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)


    # valid actions:
    # MOVE <id> <x> <y>
    # HARVEST <id> - when you are on the same cell as a tree
    # DROP <id> - when you are next to your shack and carry items
    print("MOVE 0 7 7")
