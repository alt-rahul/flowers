Ship size D = 100; trials per (bot, q): 400.

### Success rate (95% CI)

| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 | Clairvoyant bound |
|---|---|---|---|---|---|
| 0.1 | 0.948 (0.921-0.965) | 0.973 (0.951-0.985) | 0.983 (0.964-0.991) | 0.983 (0.964-0.991) | 0.983 |
| 0.2 | 0.885 (0.850-0.913) | 0.920 (0.889-0.943) | 0.935 (0.906-0.955) | 0.938 (0.909-0.957) | 0.938 |
| 0.3 | 0.835 (0.795-0.868) | 0.873 (0.836-0.902) | 0.877 (0.842-0.906) | 0.905 (0.872-0.930) | 0.905 |
| 0.4 | 0.775 (0.732-0.813) | 0.787 (0.745-0.825) | 0.787 (0.745-0.825) | 0.802 (0.761-0.839) | 0.810 |
| 0.5 | 0.738 (0.692-0.778) | 0.743 (0.697-0.783) | 0.748 (0.703-0.788) | 0.770 (0.726-0.809) | 0.772 |
| 0.6 | 0.698 (0.651-0.740) | 0.703 (0.656-0.745) | 0.708 (0.661-0.750) | 0.713 (0.666-0.755) | 0.715 |
| 0.8 | 0.590 (0.541-0.637) | 0.590 (0.541-0.637) | 0.590 (0.541-0.637) | 0.595 (0.546-0.642) | 0.595 |

### Success rate among winnable trials (clairvoyant bot could win)

| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|
| 0.1 | 0.964 | 0.990 | 1.000 | 1.000 |
| 0.2 | 0.944 | 0.981 | 0.997 | 1.000 |
| 0.3 | 0.923 | 0.964 | 0.970 | 1.000 |
| 0.4 | 0.957 | 0.972 | 0.972 | 0.991 |
| 0.5 | 0.955 | 0.961 | 0.968 | 0.997 |
| 0.6 | 0.976 | 0.983 | 0.990 | 0.997 |
| 0.8 | 0.992 | 0.992 | 0.992 | 1.000 |

### Paired difference: Bot 4 minus each other bot (same trials; +0.010 = 1 point better)

| q | vs Bot 1 | vs Bot 2 | vs Bot 3 |
|---|---|---|---|
| 0.1 | +0.035 ± 0.018 | +0.010 ± 0.010 | +0.000 ± 0.000 |
| 0.2 | +0.052 ± 0.022 | +0.018 ± 0.013 | +0.003 ± 0.005 |
| 0.3 | +0.070 ± 0.025 | +0.033 ± 0.017 | +0.028 ± 0.016 |
| 0.4 | +0.028 ± 0.019 | +0.015 ± 0.015 | +0.015 ± 0.014 |
| 0.5 | +0.033 ± 0.017 | +0.028 ± 0.016 | +0.022 ± 0.015 |
| 0.6 | +0.015 ± 0.012 | +0.010 ± 0.010 | +0.005 ± 0.010 |
| 0.8 | +0.005 ± 0.007 | +0.005 ± 0.007 | +0.005 ± 0.007 |

### Why bots fail (all q pooled; share of failures, and how many a clairvoyant bot could have avoided)

| Bot | failures | walked into fire | fire spread onto bot | button burned first | cut off from button | avoidable |
|---|---|---|---|---|---|---|
| Bot 1 | 613 | 40% | 22% | 38% | 0% | 16% |
| Bot 2 | 565 | 0% | 15% | 41% | 44% | 9% |
| Bot 3 | 549 | 0% | 6% | 46% | 48% | 7% |
| Bot 4 | 518 | 0% | 8% | 48% | 44% | 1% |

### Trial types: certain from the start, contested, or impossible

Certain = a path exists that even the fastest possible fire (q = 1) cannot catch, found with two BFSs and no simulation. Impossible = not even the clairvoyant bot wins. Contested = everything else.

| q | trials | certain win | contested | impossible |
|---|---|---|---|---|
| 0.1 | 400 | 46.0% | 52.2% | 1.8% |
| 0.2 | 400 | 52.0% | 41.8% | 6.2% |
| 0.3 | 400 | 52.5% | 38.0% | 9.5% |
| 0.4 | 400 | 48.2% | 32.8% | 19.0% |
| 0.5 | 400 | 47.0% | 30.2% | 22.8% |
| 0.6 | 400 | 51.5% | 20.0% | 28.5% |
| 0.8 | 400 | 52.2% | 7.2% | 40.5% |

### Success rate on contested trials only

| q | contested trials | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|---|
| 0.1 | 209 | 0.933 | 0.981 | 1.000 | 1.000 |
| 0.2 | 167 | 0.874 | 0.958 | 0.994 | 1.000 |
| 0.3 | 152 | 0.816 | 0.914 | 0.928 | 1.000 |
| 0.4 | 131 | 0.893 | 0.931 | 0.931 | 0.977 |
| 0.5 | 121 | 0.884 | 0.901 | 0.917 | 0.992 |
| 0.6 | 80 | 0.912 | 0.938 | 0.963 | 0.988 |
| 0.8 | 29 | 0.931 | 0.931 | 0.931 | 1.000 |

### How often a bot leaves Bot 2's rule

Share of trials with at least one move that is not a step along a shortest fire-free path (Bot 2 never makes such a move).

| q | Bot 3 | Bot 4 |
|---|---|---|
| 0.1 | 2.0% | 5.8% |
| 0.2 | 4.8% | 8.0% |
| 0.3 | 7.8% | 11.8% |
| 0.4 | 10.5% | 10.2% |
| 0.5 | 10.5% | 13.2% |
| 0.6 | 11.5% | 14.8% |
| 0.8 | 13.2% | 18.0% |

Outcomes on the same trials, pooled over q:

| Bot | left Bot 2's rule? | trials | won, Bot 2 lost | Bot 2 won, lost | both won | both lost |
|---|---|---|---|---|---|---|
| Bot 3 | yes | 241 | 20 | 4 | 23 | 194 |
| Bot 3 | no | 2559 | 0 | 0 | 2208 | 351 |
| Bot 4 | yes | 327 | 45 | 2 | 78 | 202 |
| Bot 4 | no | 2473 | 4 | 0 | 2155 | 314 |


### Thinking time (one core; time spent inside the bot's own code)

| | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|
| ms per trial | 1.8 | 3.5 | 6.5 | 1537.1 |
| µs per move | 26 | 49 | 89 | 21168 |
