#!/usr/bin/env python3
"""
Paired self-play runner for arena bot code variants.

Runs the same seed twice, swapping player order:
  1. challenger as player 0, base as player 1
  2. base as player 0, challenger as player 1

The paired total cancels most first-player/map-order bias and is a better
signal for deciding whether a code variant should replace the base strategy.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from self_play import ROOT, run_match


def bot_cmd(path):
    path = Path(path)
    if path.is_absolute():
        rel = path.relative_to(ROOT)
    else:
        rel = path
    return f"python3 /work/{rel.as_posix()}"


def main():
    parser = argparse.ArgumentParser(description="Run paired arena-bot self-play")
    parser.add_argument("challenger", help="Challenger bot file, e.g. arena_bot_b.py")
    parser.add_argument("--base", default="arena_bot_base.py", help="Base bot file")
    parser.add_argument("--seeds", type=int, default=20, help="Number of paired seeds")
    parser.add_argument("--start", type=int, default=1, help="Starting seed")
    parser.add_argument("--league", type=int, default=3, help="League level")
    parser.add_argument("--jobs", type=int, default=2, help="Parallel referee processes")
    parser.add_argument("--save", help="Optional JSON result file")
    args = parser.parse_args()

    challenger = Path(args.challenger)
    base = Path(args.base)
    challenger_cmd = bot_cmd(challenger)
    base_cmd = bot_cmd(base)
    challenger_name = challenger.name
    base_name = base.name

    print("=" * 72)
    print(f"  Paired self-play: {challenger_name} vs {base_name}")
    print(f"  {args.seeds} paired seeds (#{args.start} - #{args.start + args.seeds - 1}), league {args.league}")
    print(f"  Parallel jobs: {args.jobs}")
    print("=" * 72)
    print(f"  Challenger: {challenger_cmd}")
    print(f"  Base:       {base_cmd}")
    print()

    total_challenger = 0
    total_base = 0
    game_wins = game_losses = game_ties = 0
    pair_wins = pair_losses = pair_ties = 0
    crashes = 0
    total_time = 0.0
    results = []

    seeds = list(range(args.start, args.start + args.seeds))
    raw = {}
    jobs = max(1, args.jobs)
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {}
        for seed in seeds:
            futures[executor.submit(run_match, challenger_cmd, base_cmd, seed, args.league)] = (seed, "challenger_p0")
            futures[executor.submit(run_match, base_cmd, challenger_cmd, seed, args.league)] = (seed, "base_p0")

        for future in as_completed(futures):
            seed, order = futures[future]
            raw[(seed, order)] = future.result()

    for seed in seeds:
        c0, b1, elapsed1 = raw[(seed, "challenger_p0")]
        b0, c1, elapsed2 = raw[(seed, "base_p0")]
        total_time += elapsed1 + elapsed2

        if c0 is None or b1 is None or b0 is None or c1 is None or -2 in (c0, b1, b0, c1):
            crashes += 1
            print(f"  Seed {seed:>3}: CRASH/TIMEOUT")
            results.append({"seed": seed, "crash": True, "scores": [c0, b1, b0, c1]})
            continue

        challenger_total = c0 + c1
        base_total = b1 + b0
        diff = challenger_total - base_total
        total_challenger += challenger_total
        total_base += base_total

        for c_score, b_score in ((c0, b1), (c1, b0)):
            if c_score > b_score:
                game_wins += 1
            elif c_score < b_score:
                game_losses += 1
            else:
                game_ties += 1

        if diff > 0:
            pair_wins += 1
            tag = "challenger"
        elif diff < 0:
            pair_losses += 1
            tag = "base"
        else:
            pair_ties += 1
            tag = "tie"

        print(
            f"  Seed {seed:>3}: "
            f"C/P0={c0:>4} B/P1={b1:>4} | "
            f"B/P0={b0:>4} C/P1={c1:>4} | "
            f"paired diff={diff:>+4} [{tag}]"
        )
        results.append({
            "seed": seed,
            "challenger_as_p0": c0,
            "base_as_p1": b1,
            "base_as_p0": b0,
            "challenger_as_p1": c1,
            "challenger_total": challenger_total,
            "base_total": base_total,
            "diff": diff,
        })

    valid = pair_wins + pair_losses + pair_ties
    print()
    print("=" * 72)
    print("  SUMMARY")
    print("=" * 72)
    if valid:
        avg_diff = (total_challenger - total_base) / valid
        print(f"  Paired seeds:      C {pair_wins} / B {pair_losses} / ties {pair_ties}")
        print(f"  Individual games:  C {game_wins} / B {game_losses} / ties {game_ties}")
        print(f"  Avg paired score:  C={total_challenger / valid:.1f}  B={total_base / valid:.1f}")
        print(f"  Avg paired diff:   {avg_diff:+.2f}")
        print(f"  Total time:        {total_time:.1f}s")
    else:
        print("  No valid paired results.")
    if crashes:
        print(f"  Crashes/timeouts:  {crashes}")

    if args.save:
        data = {
            "challenger": challenger_name,
            "base": base_name,
            "challenger_cmd": challenger_cmd,
            "base_cmd": base_cmd,
            "seeds": args.seeds,
            "start": args.start,
            "league": args.league,
            "jobs": args.jobs,
            "summary": {
                "pair_wins": pair_wins,
                "pair_losses": pair_losses,
                "pair_ties": pair_ties,
                "game_wins": game_wins,
                "game_losses": game_losses,
                "game_ties": game_ties,
                "crashes": crashes,
                "total_challenger": total_challenger,
                "total_base": total_base,
            },
            "results": results,
        }
        Path(args.save).write_text(json.dumps(data, indent=2))
        print(f"\n  Results saved to {args.save}")

    if crashes > valid:
        return 3
    if total_challenger > total_base:
        return 0
    if total_challenger < total_base:
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
