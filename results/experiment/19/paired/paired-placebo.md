# Paired analysis — arm `placebo` vs `control`
**primary: all treatment repos (registered)** — n = 200, control 0.465, treatment 0.455, lift -1.00 pts (paired Wald 95% CI -3.8 to +1.8; bootstrap -4.0 to +2.0). Discordant pairs: treatment-only 3, control-only 5, McNemar exact p = 0.7266. Flags differed on 62/200 tasks; memory retrieved on 92/200.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 79 | 0.329 | 0.304 | -2.53 | 2 | 4 | 0.6875 | 44 | 61 |
| matplotlib/matplotlib | 79 | 0.595 | 0.608 | +1.27 | 1 | 0 | 1.0 | 2 | 4 |
| pylint-dev/pylint | 42 | 0.476 | 0.452 | -2.38 | 0 | 1 | 1.0 | 16 | 27 |
