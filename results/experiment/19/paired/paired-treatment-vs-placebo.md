# Paired analysis — arm `treatment` vs `placebo`
**primary: all treatment repos (registered)** — n = 200, control 0.455, treatment 0.425, lift -3.00 pts (paired Wald 95% CI -6.1 to +0.1; bootstrap -6.0 to +0.0). Discordant pairs: treatment-only 2, control-only 8, McNemar exact p = 0.1094. Flags differed on 73/200 tasks; memory retrieved on 92/200.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 79 | 0.304 | 0.279 | -2.53 | 1 | 3 | 0.625 | 49 | 61 |
| matplotlib/matplotlib | 79 | 0.608 | 0.608 | +0.00 | 1 | 1 | 1.0 | 3 | 4 |
| pylint-dev/pylint | 42 | 0.452 | 0.357 | -9.52 | 0 | 4 | 0.125 | 21 | 27 |
