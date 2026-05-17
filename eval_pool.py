#!/usr/bin/env python3
"""
Evaluate one bot against a small pool of local opponents.

This is intentionally less pure than paired mirror self-play: the goal is a
broader ladder proxy so a variant does not only optimize against its parent.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from self_play import run_match


OPPONENTS = {
    "base": "python3 /work/arena_bot_base.py",
    "config": "python3 /work/bot.py",
    "config_v001": "python3 /work/bot.py --config /work/versions/v001.json",
    "config_v002": "python3 /work/bot.py --config /work/versions/v002.json",
    "backup": "python3 /work/arena_bot_backup.py",
}


def bot_cmd(path):
    if path.startswith("python3 "):
        return path
    return f"python3 /work/{path}"


def main():
    parser = argparse.ArgumentParser(description="Evaluate a bot against a local opponent pool")
    parser.add_argument("bot", help="Bot file or command")
    parser.add_argument("--opponents", nargs="*", default=["base", "config", "backup"])
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--league", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--save")
    args = parser.parse_args()

    candidate = bot_cmd(args.bot)
    opponents = [(name, OPPONENTS.get(name, name)) for name in args.opponents]
    seeds = list(range(args.start, args.start + args.seeds))

    print("=" * 72)
    print(f"  Pool eval: {args.bot}")
    print(f"  Opponents: {', '.join(name for name, _ in opponents)}")
    print(f"  Seeds #{args.start}-{args.start + args.seeds - 1}, league {args.league}, jobs {args.jobs}")
    print("=" * 72)

    tasks = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        futures = {}
        for opp_name, opp_cmd in opponents:
            for seed in seeds:
                futures[executor.submit(run_match, candidate, opp_cmd, seed, args.league)] = (opp_name, seed, "candidate_p0")
                futures[executor.submit(run_match, opp_cmd, candidate, seed, args.league)] = (opp_name, seed, "candidate_p1")
        for future in as_completed(futures):
            opp_name, seed, order = futures[future]
            p0, p1, elapsed = future.result()
            tasks.append((opp_name, seed, order, p0, p1, elapsed))

    by_opp = {name: [] for name, _ in opponents}
    for record in tasks:
        by_opp[record[0]].append(record)

    data = {
        "bot": args.bot,
        "candidate_cmd": candidate,
        "opponents": args.opponents,
        "seeds": args.seeds,
        "start": args.start,
        "league": args.league,
        "results": [],
        "summary": {},
    }

    grand_wins = grand_losses = grand_ties = grand_crashes = 0
    grand_diff = 0
    for opp_name, _ in opponents:
        wins = losses = ties = crashes = diff_total = 0
        for _, seed, order, p0, p1, elapsed in sorted(by_opp[opp_name], key=lambda r: (r[1], r[2])):
            if p0 is None or p1 is None or p0 == -2 or p1 == -2:
                crashes += 1
                data["results"].append({"opponent": opp_name, "seed": seed, "order": order, "crash": True})
                continue
            cand_score = p0 if order == "candidate_p0" else p1
            opp_score = p1 if order == "candidate_p0" else p0
            diff = cand_score - opp_score
            diff_total += diff
            if diff > 0:
                wins += 1
            elif diff < 0:
                losses += 1
            else:
                ties += 1
            data["results"].append({
                "opponent": opp_name,
                "seed": seed,
                "order": order,
                "candidate": cand_score,
                "opponent_score": opp_score,
                "diff": diff,
                "time": elapsed,
            })

        games = wins + losses + ties
        avg_diff = diff_total / games if games else 0.0
        grand_wins += wins
        grand_losses += losses
        grand_ties += ties
        grand_crashes += crashes
        grand_diff += diff_total
        data["summary"][opp_name] = {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "crashes": crashes,
            "avg_diff": avg_diff,
        }
        print(f"  {opp_name:>11}: W {wins:>3} / L {losses:>3} / T {ties:>3} / C {crashes:>2}   avg diff {avg_diff:+.2f}")

    grand_games = grand_wins + grand_losses + grand_ties
    total_avg = grand_diff / grand_games if grand_games else 0.0
    data["summary"]["total"] = {
        "wins": grand_wins,
        "losses": grand_losses,
        "ties": grand_ties,
        "crashes": grand_crashes,
        "avg_diff": total_avg,
    }
    print("-" * 72)
    print(f"        total: W {grand_wins:>3} / L {grand_losses:>3} / T {grand_ties:>3} / C {grand_crashes:>2}   avg diff {total_avg:+.2f}")

    if args.save:
        with open(args.save, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  Results saved to {args.save}")

    if grand_crashes > grand_games:
        return 3
    if grand_wins > grand_losses:
        return 0
    if grand_losses > grand_wins:
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
