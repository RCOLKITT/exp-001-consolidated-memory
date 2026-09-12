# Paired analysis — arm `gated` vs `control`
**primary: all treatment repos (registered)** — n = 200, control 0.465, treatment 0.460, lift -0.50 pts (paired Wald 95% CI -2.7 to +1.7; bootstrap -3.0 to +1.5). Discordant pairs: treatment-only 2, control-only 3, McNemar exact p = 1.0. Flags differed on 26/200 tasks; memory retrieved on 35/200.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 79 | 0.329 | 0.342 | +1.27 | 2 | 1 | 1.0 | 15 | 19 |
| matplotlib/matplotlib | 79 | 0.595 | 0.595 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pylint-dev/pylint | 42 | 0.476 | 0.429 | -4.76 | 0 | 2 | 0.5 | 11 | 16 |
