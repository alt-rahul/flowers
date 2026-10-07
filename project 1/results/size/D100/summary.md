Ship size D = 100; trials per (bot, q): 400.

### Success rate (95% CI)

| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|
| 0.1 | 0.948 (0.921-0.965) | 0.973 (0.951-0.985) | 0.983 (0.964-0.991) | 0.978 (0.958-0.988) |
| 0.2 | 0.885 (0.850-0.913) | 0.920 (0.889-0.943) | 0.935 (0.906-0.955) | 0.932 (0.904-0.953) |
| 0.3 | 0.835 (0.795-0.868) | 0.873 (0.836-0.902) | 0.877 (0.842-0.906) | 0.897 (0.864-0.924) |
| 0.4 | 0.775 (0.732-0.813) | 0.787 (0.745-0.825) | 0.787 (0.745-0.825) | 0.800 (0.758-0.836) |
| 0.5 | 0.738 (0.692-0.778) | 0.743 (0.697-0.783) | 0.748 (0.703-0.788) | 0.760 (0.716-0.799) |
| 0.6 | 0.698 (0.651-0.740) | 0.703 (0.656-0.745) | 0.708 (0.661-0.750) | 0.713 (0.666-0.755) |
| 0.8 | 0.590 (0.541-0.637) | 0.590 (0.541-0.637) | 0.590 (0.541-0.637) | 0.595 (0.546-0.642) |

### Paired difference: Bot 4 minus each other bot (same trials; +0.010 = 1 point better)

| q | vs Bot 1 | vs Bot 2 | vs Bot 3 |
|---|---|---|---|
| 0.1 | +0.030 ± 0.017 | +0.005 ± 0.007 | -0.005 ± 0.007 |
| 0.2 | +0.048 ± 0.021 | +0.013 ± 0.011 | -0.003 ± 0.005 |
| 0.3 | +0.062 ± 0.024 | +0.025 ± 0.018 | +0.020 ± 0.015 |
| 0.4 | +0.025 ± 0.015 | +0.013 ± 0.011 | +0.013 ± 0.013 |
| 0.5 | +0.022 ± 0.015 | +0.018 ± 0.013 | +0.013 ± 0.013 |
| 0.6 | +0.015 ± 0.012 | +0.010 ± 0.010 | +0.005 ± 0.010 |
| 0.8 | +0.005 ± 0.007 | +0.005 ± 0.007 | +0.005 ± 0.007 |

### Why bots fail (all q pooled; share of each bot's failures)

| Bot | failures | walked into fire | fire spread onto bot | button burned first | cut off from button |
|---|---|---|---|---|---|
| Bot 1 | 613 | 40% | 22% | 38% | 0% |
| Bot 2 | 565 | 0% | 15% | 41% | 44% |
| Bot 3 | 549 | 0% | 6% | 46% | 48% |
| Bot 4 | 530 | 0% | 7% | 50% | 43% |

### Certain wins from the start

A trial is a certain win if some path to the button stays ahead of even the fastest possible fire (q = 1), found with two BFSs and no simulation. The bot columns count how many of those trials each bot actually won.

| q | trials | certain win | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|---|---|
| 0.1 | 400 | 46.0% | 184/184 | 184/184 | 184/184 | 184/184 |
| 0.2 | 400 | 52.0% | 208/208 | 208/208 | 208/208 | 208/208 |
| 0.3 | 400 | 52.5% | 210/210 | 210/210 | 210/210 | 210/210 |
| 0.4 | 400 | 48.2% | 193/193 | 193/193 | 193/193 | 193/193 |
| 0.5 | 400 | 47.0% | 188/188 | 188/188 | 188/188 | 188/188 |
| 0.6 | 400 | 51.5% | 206/206 | 206/206 | 206/206 | 206/206 |
| 0.8 | 400 | 52.2% | 209/209 | 209/209 | 209/209 | 209/209 |

### How often a bot leaves Bot 2's rule

Share of trials with at least one move that is not a step along a shortest fire-free path (Bot 2 never makes such a move).

| q | Bot 3 | Bot 4 |
|---|---|---|
| 0.1 | 2.0% | 2.0% |
| 0.2 | 4.8% | 5.8% |
| 0.3 | 7.8% | 9.2% |
| 0.4 | 10.5% | 13.0% |
| 0.5 | 10.5% | 15.0% |
| 0.6 | 11.5% | 19.0% |
| 0.8 | 13.2% | 23.2% |

Outcomes on the same trials, pooled over q:

| Bot | left Bot 2's rule? | trials | won, Bot 2 lost | Bot 2 won, lost | both won | both lost |
|---|---|---|---|---|---|---|
| Bot 3 | yes | 241 | 20 | 4 | 23 | 194 |
| Bot 3 | no | 2559 | 0 | 0 | 2208 | 351 |
| Bot 4 | yes | 349 | 35 | 2 | 28 | 284 |
| Bot 4 | no | 2451 | 2 | 0 | 2205 | 244 |


### Thinking time (one core; time spent inside the bot's own code)

| | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|
| ms per trial | 3.7 | 125.3 | 138.2 | 1455.5 |
| µs per move | 55 | 1753 | 1906 | 19968 |
