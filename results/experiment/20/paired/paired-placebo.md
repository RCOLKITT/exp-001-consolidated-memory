# Paired analysis — arm `placebo` vs `control`
**primary: all treatment repos (registered)** — n = 115, control 0.461, treatment 0.444, lift -1.74 pts (paired Wald 95% CI -5.9 to +2.4; bootstrap -6.1 to +2.6). Discordant pairs: treatment-only 2, control-only 4, McNemar exact p = 0.6875. Flags differed on 44/115 tasks; memory retrieved on 77/115.
**sissbruecker/linkding** — n = 14, control 0.429, treatment 0.429, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/14 tasks; memory retrieved on 0/14.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| instructlab/instructlab | 31 | 0.516 | 0.548 | +3.23 | 2 | 1 | 1.0 | 17 | 31 |
| keras-team/keras | 28 | 0.321 | 0.321 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pdm-project/pdm | 15 | 0.533 | 0.533 | +0.00 | 0 | 0 | 1.0 | 6 | 15 |
| reflex-dev/reflex | 24 | 0.458 | 0.458 | +0.00 | 0 | 0 | 1.0 | 7 | 14 |
| sissbruecker/linkding | 14 | 0.429 | 0.429 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 17 | 0.529 | 0.353 | -17.65 | 0 | 3 | 0.25 | 14 | 17 |

Tasks dropped from both arms after a failed call: {"sphinx-doc/sphinx": 2}
