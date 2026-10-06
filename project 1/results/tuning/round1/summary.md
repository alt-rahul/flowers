Ship size D = 50; trials per (bot, q): 500.

### Success rate (95% CI)

| q | Bot 2 | Bot 3 | Bot 4 (risk_weight=1,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=3,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=10,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=30,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=100,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=3,certain_first=false) | Bot 4 (risk_weight=10,certain_first=false) | Bot 4 (risk_weight=30,certain_first=false) | Bot 4 (risk_weight=100,certain_first=false) | Clairvoyant bound |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.2 | 0.942 (0.918-0.959) | 0.950 (0.927-0.966) | 0.954 (0.932-0.969) | 0.954 (0.932-0.969) | 0.952 (0.930-0.968) | 0.954 (0.932-0.969) | 0.954 (0.932-0.969) | 0.954 (0.932-0.969) | 0.952 (0.930-0.968) | 0.956 (0.934-0.971) | 0.954 (0.932-0.969) | 0.960 |
| 0.3 | 0.856 (0.823-0.884) | 0.856 (0.823-0.884) | 0.876 (0.844-0.902) | 0.880 (0.849-0.906) | 0.880 (0.849-0.906) | 0.880 (0.849-0.906) | 0.880 (0.849-0.906) | 0.882 (0.851-0.907) | 0.884 (0.853-0.909) | 0.884 (0.853-0.909) | 0.884 (0.853-0.909) | 0.892 |
| 0.4 | 0.816 (0.780-0.848) | 0.822 (0.786-0.853) | 0.830 (0.795-0.860) | 0.832 (0.797-0.862) | 0.832 (0.797-0.862) | 0.834 (0.799-0.864) | 0.834 (0.799-0.864) | 0.832 (0.797-0.862) | 0.836 (0.801-0.866) | 0.838 (0.803-0.868) | 0.838 (0.803-0.868) | 0.842 |
| 0.5 | 0.736 (0.696-0.773) | 0.740 (0.700-0.777) | 0.750 (0.710-0.786) | 0.752 (0.712-0.788) | 0.756 (0.716-0.792) | 0.756 (0.716-0.792) | 0.756 (0.716-0.792) | 0.756 (0.716-0.792) | 0.758 (0.719-0.793) | 0.760 (0.721-0.795) | 0.760 (0.721-0.795) | 0.764 |

### Success rate among winnable trials (clairvoyant bot could win)

| q | Bot 2 | Bot 3 | Bot 4 (risk_weight=1,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=3,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=10,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=30,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=100,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=3,certain_first=false) | Bot 4 (risk_weight=10,certain_first=false) | Bot 4 (risk_weight=30,certain_first=false) | Bot 4 (risk_weight=100,certain_first=false) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.2 | 0.981 | 0.990 | 0.994 | 0.994 | 0.992 | 0.994 | 0.994 | 0.994 | 0.992 | 0.996 | 0.994 |
| 0.3 | 0.960 | 0.960 | 0.982 | 0.987 | 0.987 | 0.987 | 0.987 | 0.989 | 0.991 | 0.991 | 0.991 |
| 0.4 | 0.969 | 0.976 | 0.986 | 0.988 | 0.988 | 0.990 | 0.990 | 0.988 | 0.993 | 0.995 | 0.995 |
| 0.5 | 0.963 | 0.969 | 0.982 | 0.984 | 0.990 | 0.990 | 0.990 | 0.990 | 0.992 | 0.995 | 0.995 |

### Paired difference: Bot 4 (risk_weight=30,certain_first=false) minus each other bot (same trials; +0.010 = 1 point better)

| q | vs Bot 2 | vs Bot 3 | vs Bot 4 (risk_weight=1,forecast=meanfield,certain_first=false) | vs Bot 4 (risk_weight=3,forecast=meanfield,certain_first=false) | vs Bot 4 (risk_weight=10,forecast=meanfield,certain_first=false) | vs Bot 4 (risk_weight=30,forecast=meanfield,certain_first=false) | vs Bot 4 (risk_weight=100,forecast=meanfield,certain_first=false) | vs Bot 4 (risk_weight=3,certain_first=false) | vs Bot 4 (risk_weight=10,certain_first=false) | vs Bot 4 (risk_weight=100,certain_first=false) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.2 | +0.014 ± 0.012 | +0.006 ± 0.007 | +0.002 ± 0.007 | +0.002 ± 0.007 | +0.004 ± 0.008 | +0.002 ± 0.007 | +0.002 ± 0.007 | +0.002 ± 0.007 | +0.004 ± 0.006 | +0.002 ± 0.004 |
| 0.3 | +0.028 ± 0.014 | +0.028 ± 0.014 | +0.008 ± 0.008 | +0.004 ± 0.006 | +0.004 ± 0.006 | +0.004 ± 0.006 | +0.004 ± 0.006 | +0.002 ± 0.004 | +0.000 ± 0.000 | +0.000 ± 0.000 |
| 0.4 | +0.022 ± 0.014 | +0.016 ± 0.012 | +0.008 ± 0.008 | +0.006 ± 0.007 | +0.006 ± 0.007 | +0.004 ± 0.006 | +0.004 ± 0.006 | +0.006 ± 0.007 | +0.002 ± 0.004 | +0.000 ± 0.000 |
| 0.5 | +0.024 ± 0.013 | +0.020 ± 0.012 | +0.010 ± 0.009 | +0.008 ± 0.008 | +0.004 ± 0.006 | +0.004 ± 0.006 | +0.004 ± 0.006 | +0.004 ± 0.006 | +0.002 ± 0.004 | +0.000 ± 0.000 |

### Why bots fail (all q pooled; share of failures, and how many a clairvoyant bot could have avoided)

| Bot | failures | walked into fire | fire spread onto bot | button burned first | cut off from button | avoidable |
|---|---|---|---|---|---|---|
| Bot 2 | 325 | 0% | 18% | 36% | 46% | 17% |
| Bot 3 | 316 | 0% | 7% | 45% | 48% | 14% |
| Bot 4 (risk_weight=1,forecast=meanfield,certain_first=false) | 295 | 0% | 13% | 39% | 48% | 8% |
| Bot 4 (risk_weight=3,forecast=meanfield,certain_first=false) | 291 | 0% | 11% | 40% | 49% | 7% |
| Bot 4 (risk_weight=10,forecast=meanfield,certain_first=false) | 290 | 0% | 10% | 40% | 50% | 7% |
| Bot 4 (risk_weight=30,forecast=meanfield,certain_first=false) | 288 | 0% | 9% | 41% | 50% | 6% |
| Bot 4 (risk_weight=100,forecast=meanfield,certain_first=false) | 288 | 0% | 9% | 41% | 50% | 6% |
| Bot 4 (risk_weight=3,certain_first=false) | 288 | 0% | 10% | 41% | 49% | 6% |
| Bot 4 (risk_weight=10,certain_first=false) | 285 | 0% | 9% | 41% | 50% | 5% |
| Bot 4 (risk_weight=30,certain_first=false) | 281 | 0% | 9% | 42% | 49% | 4% |
| Bot 4 (risk_weight=100,certain_first=false) | 282 | 0% | 9% | 41% | 49% | 4% |

### Thinking time (one core; time spent inside the bot's own code)

| | Bot 2 | Bot 3 | Bot 4 (risk_weight=1,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=3,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=10,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=30,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=100,forecast=meanfield,certain_first=false) | Bot 4 (risk_weight=3,certain_first=false) | Bot 4 (risk_weight=10,certain_first=false) | Bot 4 (risk_weight=30,certain_first=false) | Bot 4 (risk_weight=100,certain_first=false) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ms per trial | 0.7 | 1.2 | 55.5 | 59.6 | 62.6 | 65.1 | 67.7 | 189.7 | 193.8 | 203.4 | 210.1 |
| µs per move | 17 | 32 | 1438 | 1542 | 1615 | 1675 | 1739 | 4899 | 4991 | 5223 | 5389 |
