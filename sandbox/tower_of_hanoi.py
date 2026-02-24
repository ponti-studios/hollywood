"""
# Tower of Hanoi

You have three rods (A, B, and C) and a stack of disks of different sizes.

All disks start on rod A, stacked in decreasing size from bottom to top.

Goal: Move all disks from rod A to rod C, following these rules:
    1.	You can only move one disk at a time.
    2.	A disk can only be placed on an empty rod or on top of a larger disk.
    3.	You must use rod B as an auxiliary (helper) rod during the moves.

The objective is to move all disks from rod A to rod C in the minimum number of moves.
"""

rod_a = [1, 2, 3, 4, 5]
rod_b = []
rod_c = []
rods = [rod_a, rod_b, rod_c]


def move_disks(n, source, target, auxiliary):
    if n == 1:
        print(f"Move disk 1 from {source} to {target}")
    else:
        # Step 1: Move n-1 disks from source to auxiliary
        move_disks(n - 1, source, auxiliary, target)

        # Step 2: Move the nth disk from source to target
        print(f"Move disk {n} from {source} to {target}")

        # Step 3: Move n-1 disks from auxiliary to target
        move_disks(n - 1, auxiliary, target, source)


def tower_of_hanoi():
    return move_disks(5, "A", "B", "C")


tower_of_hanoi()
