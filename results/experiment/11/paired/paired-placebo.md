# Paired analysis — arm `placebo` vs `control`
**primary: all treatment repos (registered)** — n = 48, control 0.312, treatment 0.333, lift +2.08 pts (paired Wald 95% CI -5.0 to +9.1; bootstrap -4.2 to +8.3). Discordant pairs: treatment-only 2, control-only 1, McNemar exact p = 1.0. Flags differed on 23/48 tasks; memory retrieved on 30/48.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 48 | 0.312 | 0.333 | +2.08 | 2 | 1 | 1.0 | 23 | 30 |
| matplotlib/matplotlib | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pylint-dev/pylint | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |

Tasks dropped from both arms after a failed call: {"aws-cloudformation/cfn-lint": 35, "matplotlib/matplotlib": 81, "pylint-dev/pylint": 42}
