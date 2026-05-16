#!/usr/bin/env python3
"""
Self-play tournament runner for Troll Farm bot.

Runs two bot versions against each other across multiple seeds and reports
detailed win/loss/tie statistics.

Usage:
  # Version-based (uses config files from versions/ directory):
  python3 self_play.py v001 v002 --seeds 30

  # Custom commands:
  python3 self_play.py --bot1 "python3 /work/bot.py" --bot2 "python3 /work/bot.py --config /work/versions/v002.json" --seeds 30

  # Quick test:
  python3 self_play.py v001 v002 --seeds 5 --start 1
"""

import subprocess
import argparse
import os
import sys
import time
import json
from pathlib import Path

ROOT = Path(__file__).parent.resolve()


def parse_scores(output):
    """Parse match output to extract P0 and P1 scores.

    Output format from the game engine (after filtering warnings):
    Line 1: P0 score (integer)
    Line 2: P1 score (integer)
    Line 3: seed=N
    """
    p0 = p1 = None
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith('WARNING') or line.startswith('seed=') or line.startswith('==='):
            continue
        try:
            val = int(line)
            if p0 is None:
                p0 = val
            elif p1 is None:
                p1 = val
            else:
                break
        except ValueError:
            continue
    return p0, p1


def version_cmd(version):
    """Build bot command for a named version."""
    cfg_path = ROOT / 'versions' / f'{version}.json'
    if not cfg_path.exists():
        print(f"Error: versions/{version}.json not found", file=sys.stderr)
        sys.exit(1)
    return f'python3 /work/bot.py --config /work/versions/{version}.json'


def run_match(bot1_cmd, bot2_cmd, seed, league=3, timeout=120):
    """Run a single match and return (p0_score, p1_score, elapsed_seconds)."""
    cmd = ['./run.sh', bot1_cmd, bot2_cmd, str(seed), str(league)]
    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(ROOT)
        )
        elapsed = time.time() - start
        p0, p1 = parse_scores(result.stdout + '\n' + result.stderr)
        return p0, p1, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return None, None, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ERROR seed={seed}: {e}", file=sys.stderr)
        return None, None, elapsed


def main():
    parser = argparse.ArgumentParser(
        description='Self-play tournament runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('version1', nargs='?', help='Version name (e.g. v001)')
    parser.add_argument('version2', nargs='?', help='Version name (e.g. v002)')
    parser.add_argument('--bot1', help='Bot 1 command override')
    parser.add_argument('--bot2', help='Bot 2 command override')
    parser.add_argument('--seeds', type=int, default=30, help='Number of seeds to run')
    parser.add_argument('--start', type=int, default=1, help='Starting seed number')
    parser.add_argument('--league', type=int, default=3, help='League level (1-4)')
    parser.add_argument('--save', help='Save results to JSON file')
    args = parser.parse_args()

    # Determine bot commands
    if args.bot1 and args.bot2:
        bot1_cmd = args.bot1
        bot2_cmd = args.bot2
        name1 = 'bot1'
        name2 = 'bot2'
    elif args.version1 and args.version2:
        bot1_cmd = version_cmd(args.version1)
        bot2_cmd = version_cmd(args.version2)
        name1 = args.version1
        name2 = args.version2
    else:
        parser.print_help()
        sys.exit(1)

    n_seeds = args.seeds
    start_seed = args.start

    print(f"{'='*60}")
    print(f"  {name1} vs {name2}")
    print(f"  {n_seeds} seeds (#{start_seed} - #{start_seed + n_seeds - 1})")
    print(f"  League {args.league}")
    print(f"{'='*60}")
    print(f"  P1: {bot1_cmd}")
    print(f"  P2: {bot2_cmd}")
    print()

    results = []
    wins = losses = ties = crashes = 0
    total_p0 = total_p1 = 0
    total_time = 0

    for i in range(n_seeds):
        seed = start_seed + i
        p0, p1, elapsed = run_match(bot1_cmd, bot2_cmd, seed, args.league)

        total_time += elapsed

        if p0 is None or p1 is None:
            crashes += 1
            print(f"  Seed {seed:>3}: {'CRASH/TIMEOUT':>20}  ({elapsed:.1f}s)")
            results.append({'seed': seed, 'p0': None, 'p1': None, 'time': elapsed})
            continue

        total_p0 += p0
        total_p1 += p1

        if p0 == -2 or p1 == -2:
            crashes += 1
            print(f"  Seed {seed:>3}: P0={p0:>4} P1={p1:>4}  CRASH  ({elapsed:.1f}s)")
            results.append({'seed': seed, 'p0': p0, 'p1': p1, 'time': elapsed})
            continue

        diff = p0 - p1
        if p0 > p1:
            wins += 1
            tag = f"{name1} wins"
        elif p1 > p0:
            losses += 1
            tag = f"{name2} wins"
        else:
            ties += 1
            tag = "TIE"

        print(f"  Seed {seed:>3}: {name1}={p0:>4} {name2}={p1:>4} diff={diff:>+4} [{tag}]  ({elapsed:.1f}s)")
        results.append({'seed': seed, 'p0': p0, 'p1': p1, 'diff': diff, 'time': elapsed})

    # Summary
    n_valid = wins + losses + ties
    print()
    print(f"{'='*60}")
    print(f"  SUMMARY: {name1} vs {name2}")
    print(f"{'='*60}")

    if n_valid > 0:
        avg_p0 = total_p0 / n_valid
        avg_p1 = total_p1 / n_valid
        win_pct = wins / n_valid * 100
        loss_pct = losses / n_valid * 100
        tie_pct = ties / n_valid * 100

        print(f"  {name1} wins: {wins}/{n_valid} ({win_pct:.1f}%)")
        print(f"  {name2} wins: {losses}/{n_valid} ({loss_pct:.1f}%)")
        print(f"  Ties:         {ties}/{n_valid} ({tie_pct:.1f}%)")
        print(f"  Avg score:    {name1}={avg_p0:.1f}  {name2}={avg_p1:.1f}")
        print(f"  Avg diff:     {avg_p0 - avg_p1:+.1f}")
        print(f"  Total time:   {total_time:.1f}s ({total_time/n_seeds:.1f}s/seed)")

        if wins > losses:
            print(f"\n  >>> {name1} WINS THE MATCH <<<")
        elif losses > wins:
            print(f"\n  >>> {name2} WINS THE MATCH <<<")
        else:
            print(f"\n  >>> TIE <<<")
    else:
        print(f"  No valid results! ({crashes} crashes)")

    if crashes > 0:
        print(f"  Crashes/timeouts: {crashes}")

    # Save results
    if args.save:
        save_data = {
            'name1': name1, 'name2': name2,
            'bot1_cmd': bot1_cmd, 'bot2_cmd': bot2_cmd,
            'seeds': n_seeds, 'start_seed': start_seed, 'league': args.league,
            'summary': {
                'wins': wins, 'losses': losses, 'ties': ties, 'crashes': crashes,
                'avg_p0': total_p0 / max(n_valid, 1), 'avg_p1': total_p1 / max(n_valid, 1),
            },
            'results': results
        }
        with open(args.save, 'w') as f:
            json.dump(save_data, f, indent=2)
        print(f"\n  Results saved to {args.save}")

    # Exit code: 0=bot1 wins, 1=bot2 wins, 2=tie, 3=crashes
    if crashes > n_valid:
        return 3
    if wins > losses:
        return 0
    elif losses > wins:
        return 1
    else:
        return 2


if __name__ == '__main__':
    sys.exit(main())