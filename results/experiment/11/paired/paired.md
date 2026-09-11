# Paired analysis — arm `treatment` vs `control`
**primary: all treatment repos (registered)** — n = 48, control 0.312, treatment 0.312, lift +0.00 pts (paired Wald 95% CI -5.8 to +5.8; bootstrap -6.2 to +6.2). Discordant pairs: treatment-only 1, control-only 1, McNemar exact p = 1.0. Flags differed on 26/48 tasks; memory retrieved on 30/48.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 48 | 0.312 | 0.312 | +0.00 | 1 | 1 | 1.0 | 26 | 30 |
| matplotlib/matplotlib | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pylint-dev/pylint | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |

Tasks dropped from both arms after a failed call: {"aws-cloudformation/cfn-lint": 35, "matplotlib/matplotlib": 81, "pylint-dev/pylint": 42}
