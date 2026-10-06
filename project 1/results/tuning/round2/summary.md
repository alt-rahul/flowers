Ship size D = 50; trials per (bot, q): 500.

### Success rate (95% CI)

| q | Bot 2 | Bot 3 | Bot 4 (risk_weight=30,certain_first=false) | Bot 4 (risk_weight=100,certain_first=false) | Bot 4 (risk_weight=300,certain_first=false) | Bot 4 (risk_weight=1000,certain_first=false) | Clairvoyant bound |
|---|---|---|---|---|---|---|---|
| 0.05 | 0.996 (0.986-0.999) | 0.996 (0.986-0.999) | 0.996 (0.986-0.999) | 0.998 (0.989-1.000) | 0.998 (0.989-1.000) | 0.998 (0.989-1.000) | 0.998 |
| 0.1 | 0.976 (0.959-0.986) | 0.974 (0.956-0.985) | 0.976 (0.959-0.986) | 0.976 (0.959-0.986) | 0.976 (0.959-0.986) | 0.976 (0.959-0.986) | 0.976 |
| 0.15 | 0.950 (0.927-0.966) | 0.956 (0.934-0.971) | 0.964 (0.944-0.977) | 0.964 (0.944-0.977) | 0.964 (0.944-0.977) | 0.964 (0.944-0.977) | 0.964 |
| 0.2 | 0.942 (0.918-0.959) | 0.950 (0.927-0.966) | 0.956 (0.934-0.971) | 0.954 (0.932-0.969) | 0.956 (0.934-0.971) | 0.956 (0.934-0.971) | 0.960 |
| 0.3 | 0.856 (0.823-0.884) | 0.856 (0.823-0.884) | 0.884 (0.853-0.909) | 0.884 (0.853-0.909) | 0.886 (0.855-0.911) | 0.888 (0.857-0.913) | 0.892 |
| 0.4 | 0.816 (0.780-0.848) | 0.822 (0.786-0.853) | 0.838 (0.803-0.868) | 0.838 (0.803-0.868) | 0.838 (0.803-0.868) | 0.838 (0.803-0.868) | 0.842 |
| 0.5 | 0.736 (0.696-0.773) | 0.740 (0.700-0.777) | 0.760 (0.721-0.795) | 0.760 (0.721-0.795) | 0.760 (0.721-0.795) | 0.760 (0.721-0.795) | 0.764 |
| 0.6 | 0.636 (0.593-0.677) | 0.640 (0.597-0.681) | 0.660 (0.617-0.700) | 0.660 (0.617-0.700) | 0.660 (0.617-0.700) | 0.660 (0.617-0.700) | 0.660 |

### Success rate among winnable trials (clairvoyant bot could win)

| q | Bot 2 | Bot 3 | Bot 4 (risk_weight=30,certain_first=false) | Bot 4 (risk_weight=100,certain_first=false) | Bot 4 (risk_weight=300,certain_first=false) | Bot 4 (risk_weight=1000,certain_first=false) |
|---|---|---|---|---|---|---|
| 0.05 | 0.998 | 0.998 | 0.998 | 1.000 | 1.000 | 1.000 |
| 0.1 | 1.000 | 0.998 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.15 | 0.985 | 0.992 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.2 | 0.981 | 0.990 | 0.996 | 0.994 | 0.996 | 0.996 |
| 0.3 | 0.960 | 0.960 | 0.991 | 0.991 | 0.993 | 0.996 |
| 0.4 | 0.969 | 0.976 | 0.995 | 0.995 | 0.995 | 0.995 |
| 0.5 | 0.963 | 0.969 | 0.995 | 0.995 | 0.995 | 0.995 |
| 0.6 | 0.964 | 0.970 | 1.000 | 1.000 | 1.000 | 1.000 |

### Paired difference: Bot 4 (risk_weight=1000,certain_first=false) minus each other bot (same trials; +0.010 = 1 point better)

| q | vs Bot 2 | vs Bot 3 | vs Bot 4 (risk_weight=30,certain_first=false) | vs Bot 4 (risk_weight=100,certain_first=false) | vs Bot 4 (risk_weight=300,certain_first=false) |
|---|---|---|---|---|---|
| 0.05 | +0.002 ± 0.004 | +0.002 ± 0.004 | +0.002 ± 0.004 | +0.000 ± 0.000 | +0.000 ± 0.000 |
| 0.1 | +0.000 ± 0.000 | +0.002 ± 0.004 | +0.000 ± 0.000 | +0.000 ± 0.000 | +0.000 ± 0.000 |
| 0.15 | +0.014 ± 0.010 | +0.008 ± 0.008 | +0.000 ± 0.000 | +0.000 ± 0.000 | +0.000 ± 0.000 |
| 0.2 | +0.014 ± 0.012 | +0.006 ± 0.009 | +0.000 ± 0.006 | +0.002 ± 0.004 | +0.000 ± 0.000 |
| 0.3 | +0.032 ± 0.015 | +0.032 ± 0.015 | +0.004 ± 0.006 | +0.004 ± 0.006 | +0.002 ± 0.004 |
| 0.4 | +0.022 ± 0.014 | +0.016 ± 0.012 | +0.000 ± 0.000 | +0.000 ± 0.000 | +0.000 ± 0.000 |
| 0.5 | +0.024 ± 0.013 | +0.020 ± 0.012 | +0.000 ± 0.000 | +0.000 ± 0.000 | +0.000 ± 0.000 |
| 0.6 | +0.024 ± 0.013 | +0.020 ± 0.012 | +0.000 ± 0.000 | +0.000 ± 0.000 | +0.000 ± 0.000 |

### Why bots fail (all q pooled; share of failures, and how many a clairvoyant bot could have avoided)

| Bot | failures | walked into fire | fire spread onto bot | button burned first | cut off from button | avoidable |
|---|---|---|---|---|---|---|
| Bot 2 | 546 | 0% | 16% | 37% | 47% | 14% |
| Bot 3 | 533 | 0% | 6% | 44% | 50% | 11% |
| Bot 4 (risk_weight=30,certain_first=false) | 483 | 0% | 8% | 42% | 50% | 2% |
| Bot 4 (risk_weight=100,certain_first=false) | 483 | 0% | 8% | 42% | 50% | 2% |
| Bot 4 (risk_weight=300,certain_first=false) | 481 | 0% | 8% | 42% | 50% | 2% |
| Bot 4 (risk_weight=1000,certain_first=false) | 480 | 0% | 8% | 42% | 50% | 2% |

### Trial types: certain from the start, contested, or impossible

Certain = a path exists that even the fastest possible fire (q = 1) cannot catch, found with two BFSs and no simulation. Impossible = not even the clairvoyant bot wins. Contested = everything else.

| q | trials | certain win | contested | impossible |
|---|---|---|---|---|
| 0.05 | 500 | 48.0% | 51.8% | 0.2% |
| 0.1 | 500 | 51.0% | 46.6% | 2.4% |
| 0.15 | 500 | 44.8% | 51.6% | 3.6% |
| 0.2 | 500 | 51.2% | 44.8% | 4.0% |
| 0.3 | 500 | 48.4% | 40.8% | 10.8% |
| 0.4 | 500 | 52.4% | 31.8% | 15.8% |
| 0.5 | 500 | 49.2% | 27.2% | 23.6% |
| 0.6 | 500 | 46.8% | 19.2% | 34.0% |

### Success rate on contested trials only

| q | contested trials | Bot 2 | Bot 3 | Bot 4 (risk_weight=30,certain_first=false) | Bot 4 (risk_weight=100,certain_first=false) | Bot 4 (risk_weight=300,certain_first=false) | Bot 4 (risk_weight=1000,certain_first=false) |
|---|---|---|---|---|---|---|---|
| 0.05 | 259 | 0.996 | 0.996 | 0.996 | 1.000 | 1.000 | 1.000 |
| 0.1 | 233 | 1.000 | 0.996 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.15 | 258 | 0.973 | 0.984 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.2 | 224 | 0.960 | 0.978 | 0.991 | 0.987 | 0.991 | 0.991 |
| 0.3 | 204 | 0.912 | 0.912 | 0.980 | 0.980 | 0.985 | 0.990 |
| 0.4 | 159 | 0.918 | 0.937 | 0.987 | 0.987 | 0.987 | 0.987 |
| 0.5 | 136 | 0.897 | 0.912 | 0.985 | 0.985 | 0.985 | 0.985 |
| 0.6 | 96 | 0.875 | 0.896 | 1.000 | 1.000 | 1.000 | 1.000 |

### How often a bot leaves Bot 2's rule

Share of trials with at least one move that is not a step along a shortest fire-free path (Bot 2 never makes such a move).

| q | Bot 3 | Bot 4 (risk_weight=30,certain_first=false) | Bot 4 (risk_weight=100,certain_first=false) | Bot 4 (risk_weight=300,certain_first=false) | Bot 4 (risk_weight=1000,certain_first=false) |
|---|---|---|---|---|---|
| 0.05 | 3.4% | 3.2% | 3.8% | 4.4% | 5.2% |
| 0.1 | 1.0% | 3.0% | 3.6% | 4.6% | 5.2% |
| 0.15 | 6.4% | 7.2% | 8.8% | 9.8% | 11.0% |
| 0.2 | 7.2% | 7.0% | 8.0% | 9.0% | 9.8% |
| 0.3 | 9.6% | 8.8% | 9.2% | 9.8% | 9.8% |
| 0.4 | 9.0% | 8.4% | 9.0% | 9.2% | 9.2% |
| 0.5 | 14.6% | 8.4% | 8.4% | 8.4% | 8.6% |
| 0.6 | 16.8% | 11.4% | 11.4% | 11.4% | 11.4% |

Outcomes on the same trials, pooled over q:

| Bot | left Bot 2's rule? | trials | won, Bot 2 lost | Bot 2 won, lost | both won | both lost |
|---|---|---|---|---|---|---|
| Bot 3 | yes | 340 | 32 | 19 | 73 | 216 |
| Bot 3 | no | 3660 | 0 | 0 | 3362 | 298 |
| Bot 4 (risk_weight=30,certain_first=false) | yes | 287 | 55 | 2 | 116 | 114 |
| Bot 4 (risk_weight=30,certain_first=false) | no | 3713 | 10 | 0 | 3336 | 367 |
| Bot 4 (risk_weight=100,certain_first=false) | yes | 311 | 55 | 2 | 140 | 114 |
| Bot 4 (risk_weight=100,certain_first=false) | no | 3689 | 10 | 0 | 3312 | 367 |
| Bot 4 (risk_weight=300,certain_first=false) | yes | 333 | 57 | 2 | 160 | 114 |
| Bot 4 (risk_weight=300,certain_first=false) | no | 3667 | 10 | 0 | 3292 | 365 |
| Bot 4 (risk_weight=1000,certain_first=false) | yes | 351 | 57 | 2 | 178 | 114 |
| Bot 4 (risk_weight=1000,certain_first=false) | no | 3649 | 11 | 0 | 3274 | 364 |


### Thinking time (one core; time spent inside the bot's own code)

| | Bot 2 | Bot 3 | Bot 4 (risk_weight=30,certain_first=false) | Bot 4 (risk_weight=100,certain_first=false) | Bot 4 (risk_weight=300,certain_first=false) | Bot 4 (risk_weight=1000,certain_first=false) |
|---|---|---|---|---|---|---|
| ms per trial | 0.9 | 1.6 | 130.8 | 129.4 | 133.5 | 138.3 |
| µs per move | 24 | 40 | 3301 | 3262 | 3361 | 3476 |
