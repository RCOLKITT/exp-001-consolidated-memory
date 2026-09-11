# Paired analysis — arm `treatment` vs `placebo`
**primary: all treatment repos (registered)** — n = 48, control 0.333, treatment 0.312, lift -2.08 pts (paired Wald 95% CI -6.1 to +2.0; bootstrap -6.2 to +0.0). Discordant pairs: treatment-only 0, control-only 1, McNemar exact p = 1.0. Flags differed on 22/48 tasks; memory retrieved on 30/48.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 48 | 0.333 | 0.312 | -2.08 | 0 | 1 | 1.0 | 22 | 30 |
| matplotlib/matplotlib | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pylint-dev/pylint | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |

Tasks dropped from both arms after a failed call: {"aws-cloudformation/cfn-lint": 35, "matplotlib/matplotlib": 81, "pylint-dev/pylint": 42}
