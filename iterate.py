#!/usr/bin/env python3
"""
Iterative self-play improvement cycle manager.

Manages champion vs challenger matchups. When the challenger wins, it becomes
the new champion. Creates new version configs for the next iteration.

Usage:
  python3 iterate.py init                    # Create v001 config (if not exists)
  python3 iterate.py status                  # Show current champion/challenger
  python3 iterate.py run --seeds 30          # Run champion vs challenger
  python3 iterate.py promote [version]       # Manually promote a version to champion
  python3 iterate.py new-challenger          # Create new challenger based on champion
  python3 iterate.py diff                    # Show diff between champion and challenger

Workflow:
  1. Initialize:  python3 iterate.py init
  2. Create challenger:  python3 iterate.py new-challenger
  3. Edit:  Modify the new config in versions/vXXX.json
  4. Test:  python3 iterate.py run --seeds 30
  5. If challenger wins:  python3 iterate.py promote <version>
  6. Repeat from step 2
"""

import argparse
import json
import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

VERSIONS_DIR = Path(__file__).parent / 'versions'
HISTORY_FILE = VERSIONS_DIR / 'history.json'
CHAMPION_FILE = VERSIONS_DIR / 'champion.txt'


def get_next_version():
    """Get the next available version number."""
    VERSIONS_DIR.mkdir(exist_ok=True)
    existing = []
    for f in VERSIONS_DIR.glob('v*.json'):
        try:
            num = int(f.stem[1:])
            existing.append(num)
        except ValueError:
            pass
    return max(existing) + 1 if existing else 1


def get_champion():
    """Read current champion version name."""
    if CHAMPION_FILE.exists():
        return CHAMPION_FILE.read_text().strip()
    return None


def set_champion(version):
    """Set current champion version."""
    CHAMPION_FILE.write_text(version)


def get_challenger():
    """Get the latest version that isn't the champion."""
    champion = get_champion()
    existing = []
    for f in VERSIONS_DIR.glob('v*.json'):
        existing.append(f.stem)
    if not existing:
        return None
    existing.sort(key=lambda x: int(x[1:]))
    for v in reversed(existing):
        if v != champion:
            return v
    return None


def list_versions():
    """List all version configs."""
    versions = []
    for f in sorted(VERSIONS_DIR.glob('v*.json')):
        try:
            with open(f) as fh:
                cfg = json.load(fh)
            versions.append((f.stem, cfg.get('name', '?'), cfg.get('description', '')))
        except:
            versions.append((f.stem, '?', ''))
    return versions


def load_history():
    """Load match history."""
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return []


def save_history(history):
    """Save match history."""
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def cmd_init(args):
    """Create initial version config if not exists."""
    VERSIONS_DIR.mkdir(exist_ok=True)

    v1 = VERSIONS_DIR / 'v001.json'
    if v1.exists():
        print(f"v001.json already exists.")
    else:
        # Create from default config
        from bot import DEFAULT_CONFIG
        DEFAULT_CONFIG['name'] = 'v001-baseline'
        DEFAULT_CONFIG['description'] = 'Initial baseline config'
        v1.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        print(f"Created v001.json with default config")

    if not get_champion():
        set_champion('v001')
        print("Champion set to v001")
    else:
        print(f"Current champion: {get_champion()}")


def cmd_status(args):
    """Show current status."""
    champion = get_champion()
    challenger = get_challenger()
    history = load_history()

    print(f"{'='*50}")
    print(f"  Self-Play Iteration Status")
    print(f"{'='*50}")

    if champion:
        print(f"  Champion:   {champion}")
    else:
        print(f"  Champion:   (none)")

    if challenger:
        print(f"  Challenger: {challenger}")
    else:
        print(f"  Challenger: (none)")

    print()
    print(f"  Versions:")
    for vname, vtitle, vdesc in list_versions():
        marker = " [CHAMPION]" if vname == champion else (" [challenger]" if vname == challenger else "")
        print(f"    {vname}: {vtitle}{marker}")
        if vdesc:
            print(f"         {vdesc}")

    if history:
        print(f"\n  Match history: {len(history)} matches")
        last = history[-1]
        print(f"    Last match: {last['p1']} vs {last['p2']} "
              f"→ {last['p1']}={last.get('p1_wins', '?')} wins, "
              f"{last['p2']}={last.get('p2_wins', '?')} wins, "
              f"ties={last.get('ties', '?')}")
        winner = last.get('winner', '?')
        print(f"    Winner: {winner}")


def cmd_run(args):
    """Run champion vs challenger match."""
    champion = get_champion()
    if not champion:
        print("No champion set. Run 'init' first.")
        sys.exit(1)

    challenger = args.challenger or get_challenger()
    if not challenger:
        print("No challenger found. Run 'new-challenger' first.")
        sys.exit(1)

    print(f"Running champion ({champion}) vs challenger ({challenger})...")

    self_play_cmd = [
        sys.executable, str(Path(__file__).parent / 'self_play.py'),
        champion, challenger,
        '--seeds', str(args.seeds),
        '--start', str(args.start),
        '--league', str(args.league),
    ]

    if args.save:
        self_play_cmd.extend(['--save', args.save])

    result = subprocess.run(self_play_cmd)
    exit_code = result.returncode

    # Record in history
    history = load_history()
    record = {
        'timestamp': datetime.now().isoformat(),
        'p1': champion,
        'p2': challenger,
        'seeds': args.seeds,
        'winner': champion if exit_code == 0 else (challenger if exit_code == 1 else 'tie'),
    }
    history.append(record)
    save_history(history)

    if exit_code == 0:
        print(f"\nChampion ({champion}) defended!")
    elif exit_code == 1:
        print(f"\nChallenger ({challenger}) won! Promote with: python3 iterate.py promote {challenger}")
    elif exit_code == 2:
        print(f"\nTie match.")
    else:
        print(f"\nMatch had errors (too many crashes).")

    return exit_code


def cmd_promote(args):
    """Promote a version to champion."""
    version = args.version or get_challenger()
    if not version:
        print("No version specified and no challenger found.")
        sys.exit(1)

    cfg_path = VERSIONS_DIR / f'{version}.json'
    if not cfg_path.exists():
        print(f"Error: versions/{version}.json not found")
        sys.exit(1)

    old_champion = get_champion()
    set_champion(version)
    print(f"Promoted {version} to champion (was {old_champion})")

    if args.new_challenger:
        cmd_new_challenger(args)


def cmd_new_challenger(args):
    """Create a new challenger version based on champion."""
    champion = get_champion()
    if not champion:
        print("No champion set. Run 'init' first.")
        sys.exit(1)

    src_path = VERSIONS_DIR / f'{champion}.json'
    if not src_path.exists():
        print(f"Error: champion config versions/{champion}.json not found")
        sys.exit(1)

    next_num = get_next_version()
    new_name = f'v{next_num:03d}'
    dst_path = VERSIONS_DIR / f'{new_name}.json'

    with open(src_path) as f:
        cfg = json.load(f)

    # Update name to indicate it's a new version
    cfg['name'] = f'{new_name}-from-{champion}'
    cfg['description'] = f'Copy of {champion} — modify this to create challenger'

    with open(dst_path, 'w') as f:
        json.dump(cfg, f, indent=2)

    print(f"Created versions/{new_name}.json (based on {champion})")
    print(f"Edit this file to create your challenger strategy.")
    print(f"Then test with: python3 self_play.py {champion} {new_name} --seeds 30")
    print(f"Or:             python3 iterate.py run --challenger {new_name}")


def cmd_diff(args):
    """Show differences between champion and challenger configs."""
    champion = get_champion()
    challenger = get_challenger()
    if not champion or not challenger:
        print("Need both champion and challenger to diff.")
        sys.exit(1)

    v1_path = VERSIONS_DIR / f'{champion}.json'
    v2_path = VERSIONS_DIR / f'{challenger}.json'

    with open(v1_path) as f:
        cfg1 = json.load(f)
    with open(v2_path) as f:
        cfg2 = json.load(f)

    print(f"Diff: {champion} (champion) vs {challenger} (challenger)")
    print(f"{'='*50}")

    def diff_dicts(d1, d2, prefix=''):
        for key in sorted(set(list(d1.keys()) + list(d2.keys()))):
            v1 = d1.get(key)
            v2 = d2.get(key)
            full_key = f"{prefix}.{key}" if prefix else key
            if v1 == v2:
                continue
            if isinstance(v1, dict) and isinstance(v2, dict):
                diff_dicts(v1, v2, full_key)
            elif isinstance(v1, list) and isinstance(v2, list):
                if v1 != v2:
                    # Show list diff for training configs
                    if full_key.endswith('configs'):
                        print(f"  {full_key}:")
                        for i, (a, b) in enumerate(zip(v1, v2)):
                            if a != b:
                                print(f"    [{i}]: {a} → {b}")
                        if len(v1) != len(v2):
                            print(f"    Length: {len(v1)} → {len(v2)}")
                    else:
                        print(f"  {full_key}: {v1} → {v2}")
            else:
                v1_str = str(v1) if v1 is not None else "(missing)"
                v2_str = str(v2) if v2 is not None else "(missing)"
                print(f"  {full_key}: {v1_str} → {v2_str}")

    diff_dicts(cfg1, cfg2)


def cmd_reset(args):
    """Clear champion and history."""
    if CHAMPION_FILE.exists():
        CHAMPION_FILE.unlink()
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
    print("Cleared champion and history.")


def main():
    parser = argparse.ArgumentParser(
        description='Iterative self-play improvement cycle',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest='command', help='Command to run')

    # init
    sub.add_parser('init', help='Create initial version config')

    # status
    sub.add_parser('status', help='Show current champion/challenger')

    # run
    p_run = sub.add_parser('run', help='Run champion vs challenger')
    p_run.add_argument('--seeds', type=int, default=30, help='Number of seeds')
    p_run.add_argument('--start', type=int, default=1, help='Starting seed')
    p_run.add_argument('--league', type=int, default=3, help='League level')
    p_run.add_argument('--challenger', help='Override challenger version')
    p_run.add_argument('--save', help='Save results to JSON file')

    # promote
    p_promote = sub.add_parser('promote', help='Promote version to champion')
    p_promote.add_argument('version', nargs='?', help='Version to promote (default: challenger)')
    p_promote.add_argument('--new-challenger', action='store_true',
                           help='Create new challenger after promoting')

    # new-challenger
    sub.add_parser('new-challenger', help='Create new challenger config from champion')

    # diff
    sub.add_parser('diff', help='Show diff between champion and challenger')

    # reset
    sub.add_parser('reset', help='Clear champion and history')

    args = parser.parse_args()

    if args.command == 'init':
        cmd_init(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'promote':
        cmd_promote(args)
    elif args.command == 'new-challenger':
        cmd_new_challenger(args)
    elif args.command == 'diff':
        cmd_diff(args)
    elif args.command == 'reset':
        cmd_reset(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()