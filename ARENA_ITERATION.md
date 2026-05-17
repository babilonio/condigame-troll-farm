# Arena Bot Iteration Log

## Stable Files

| File | Role |
|------|------|
| `arena_bot.py` | Current submission file. Pressure variant; promoted to Silver, rank 512/630. |
| `arena_bot_base.py` | Base strategy that reached Bronze, rank 204/528. Compare every challenger against this before promotion. |
| `arena_bot_silver_base.py` | Preserved Silver-promotion pressure strategy. Use this as the next anchor for Silver work. |
| `arena_bot_a.py` | Working champion copy from the Bronze base; stale relative to current Silver submission unless refreshed. |
| `arena_bot_b.py` | Working challenger copy, currently `pressure`; same idea as current `arena_bot.py`. |

## Fair Comparison Command

Use paired self-play so each seed is tested in both player orders:

```bash
python3 paired_self_play.py arena_bot_b.py --base arena_bot_base.py --seeds 20 --start 1 --league 3 --jobs 4
```

A challenger should beat `arena_bot_base.py` by paired score and paired seed wins before replacing `arena_bot.py`.

Important exception learned on May 17, 2026: mirror paired self-play alone can be misleading. `mine6` looked positive locally and fell on ladder; `pressure` looked slightly negative in mirror but better in pool eval and promoted to Silver. Use `eval_pool.py` before ladder probes:

```bash
python3 eval_pool.py arena_bot.py --opponents config config_v001 config_v002 backup --seeds 12 --start 1 --league 3 --jobs 10
```

## Ladder Milestones

| Date | Bot / Variant | Ladder Result | Notes |
|------|---------------|---------------|-------|
| 2026-05-16 | Wood 1 rewrite / base | Promoted to Bronze, rank 204/528 | Established `arena_bot_base.py` as the Bronze anchor |
| 2026-05-16 | `arena_bot_variant_mine6.py` | Bronze rank 339/529 | Local mirror score was positive but ladder got worse; rejected |
| 2026-05-17 | `arena_bot_variant_pressure.py` copied to `arena_bot.py` | Promoted to Silver, rank 512/630 | Pool eval was better than base despite slightly negative mirror self-play |

## Tested Variants

| Variant | File | Seeds | Result vs Base | Decision |
|---------|------|-------|----------------|----------|
| Bronze pressure | `arena_bot_variant_pressure.py` | Mirror: 12 paired seeds start 1, league 3. Pool: 12 seeds vs config/v001/v002/backup in both orders | Mirror avg paired diff -1.08. Pool avg diff +47.72 vs base +46.31; pool record 88W/8L vs base 84W/11L/1C. Ladder promoted to Silver 512/630 | Current submission, proven ladder improvement |
| Bronze mine threshold 6 | `arena_bot_variant_mine6.py` | 50 paired seeds, starts 1 and 21, league 3 | Total paired score: variant 13543, base 13468; average paired diff +1.50. Paired seeds: variant 1 / base 5 / ties 44. Individual games: 34 / 34 / 32. Ladder rank dropped to 339/529 | Reject for ladder despite local score |
| Bronze mine walkable spots | `arena_bot_variant_mine_spots.py` | 20 paired seeds, start 1, league 3 | Average paired diff -0.20; 0 / 1 / 19 paired seeds | Keep as bug-fix idea, not promoted |
| Bronze fruit-only economy | `arena_bot_variant_fruit_only_bronze.py` | 12 paired seeds, start 1, league 3 | Average paired diff -0.92 | Reject for now |
| Bronze resource balance | `arena_bot_variant_resource_balance.py` | 20 paired seeds, start 1, league 3 | Average paired diff -7.40 | Reject |
| Bronze stack/contest 2 | `arena_bot_variant_stack2.py` | 12 paired seeds, start 1, league 3 | Average paired diff -5.25 | Reject |
| Bronze no planting | `arena_bot_variant_no_bronze_plant.py` | 12 paired seeds, start 1, league 3 | Average paired diff -80.67 | Strong reject |
| Bronze endgame cash-in | `arena_bot_variant_endgame_cash.py` | 12 paired seeds, start 1, league 3 | Average paired diff -1.92 | Reject |
| Bronze training cap 9 | `arena_bot_variant_train9.py` | 6 paired seeds, start 1, league 3 | Average paired score tied 298.7 / 298.7; paired diff +0.00 | Keep as neutral variant |
| Bronze plant cap 2 | `arena_bot_variant_plant2.py` | 20 paired seeds, start 1, league 3 | Average paired score: variant 303.7, base 305.2; average paired diff -1.55 | Reject for now despite many small wins |
| Bronze plant cap 4 | `arena_bot_variant_plant4.py` | 10 paired seeds, start 1, league 3 | Paired total: variant 303.4 avg per order pair, base 304.3; average paired diff -0.9 | Reject for now |
| Targeted chop routing | `arena_bot_variant_chop_target.py` | 10 paired seeds, start 1, league 3 | Paired total: variant 300.8 avg per order pair, base 302.6; average paired diff -1.8 | Reject for now |

## Promotion Rule

1. Save the challenger as a named `arena_bot_variant_*.py` file.
2. Run at least 20 paired Bronze seeds against `arena_bot_base.py`.
3. If it wins, run at least 20 paired seeds against the current `arena_bot_a.py`.
4. Promote only if it wins both checks by paired score, with no crashes.
5. Copy the winner to `arena_bot.py`; update `arena_bot_base.py` only when intentionally replacing the preserved Bronze anchor with a new long-term anchor.
6. If ladder result contradicts local eval, trust the ladder and record the contradiction here.

## Next Session Notes

- Start from current `arena_bot.py` pressure variant, not `mine6`.
- `arena_bot_silver_base.py` has been saved; compare future Silver variants against it first.
- Add stronger local opponents to `eval_pool.py`; the current pool still contains mostly old/weaker bots.
- Focus next ideas on Silver-level opponent modeling and disruption rather than plant cap constants.
