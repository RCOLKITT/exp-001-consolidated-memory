# Paired analysis — arm `gated` vs `control`
**primary: all treatment repos (registered)** — n = 48, control 0.312, treatment 0.333, lift +2.08 pts (paired Wald 95% CI -2.0 to +6.1; bootstrap +0.0 to +6.2). Discordant pairs: treatment-only 1, control-only 0, McNemar exact p = 1.0. Flags differed on 8/48 tasks; memory retrieved on 9/48.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 48 | 0.312 | 0.333 | +2.08 | 1 | 0 | 1.0 | 8 | 9 |
| matplotlib/matplotlib | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pylint-dev/pylint | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |

Tasks dropped from both arms after a failed call: {"aws-cloudformation/cfn-lint": 35, "matplotlib/matplotlib": 81, "pylint-dev/pylint": 42}
