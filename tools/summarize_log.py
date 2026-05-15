#!/usr/bin/env python3
import json
import sys


def compact_entries(entries):
    return [(i, value) for i, value in enumerate(entries) if value]


def main():
    if len(sys.argv) != 2:
        print("usage: tools/summarize_log.py <referee-log.json>", file=sys.stderr)
        return 2

    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    scores = data.get("scores", {})
    print(f"scores: P0={scores.get('0')} P1={scores.get('1')}")

    seeds = [line.strip() for line in data.get("uinput", []) if line.strip()]
    if seeds:
        print("input: " + ", ".join(seeds))

    for player in ("0", "1"):
        errors = compact_entries(data.get("errors", {}).get(player, []))
        print(f"errors P{player}: {len(errors)}")
        for turn, error in errors[:10]:
            print(f"  turn {turn}: {error}")
        if len(errors) > 10:
            print(f"  ... {len(errors) - 10} more")

    referee = compact_entries(data.get("errors", {}).get("referee", []))
    print(f"referee messages: {len(referee)}")
    for turn, message in referee[:10]:
        print(f"  turn {turn}: {message}")


if __name__ == "__main__":
    raise SystemExit(main())
