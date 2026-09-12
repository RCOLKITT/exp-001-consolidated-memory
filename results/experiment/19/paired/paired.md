# Paired analysis — arm `treatment` vs `control`
**primary: all treatment repos (registered)** — n = 200, control 0.465, treatment 0.425, lift -4.00 pts (paired Wald 95% CI -7.3 to -0.7; bootstrap -7.5 to -1.0). Discordant pairs: treatment-only 2, control-only 10, McNemar exact p = 0.0386. Flags differed on 77/200 tasks; memory retrieved on 92/200.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 79 | 0.329 | 0.279 | -5.06 | 1 | 5 | 0.2188 | 53 | 61 |
| matplotlib/matplotlib | 79 | 0.595 | 0.608 | +1.27 | 1 | 0 | 1.0 | 2 | 4 |
| pylint-dev/pylint | 42 | 0.476 | 0.357 | -11.90 | 0 | 5 | 0.0625 | 22 | 27 |
