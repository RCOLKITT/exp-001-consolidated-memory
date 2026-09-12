# Paired analysis — arm `treatment` vs `placebo`
**primary: all treatment repos (registered)** — n = 115, control 0.444, treatment 0.487, lift +4.35 pts (paired Wald 95% CI -0.7 to +9.4; bootstrap +0.0 to +9.6). Discordant pairs: treatment-only 7, control-only 2, McNemar exact p = 0.1797. Flags differed on 59/115 tasks; memory retrieved on 77/115.
**sissbruecker/linkding** — n = 14, control 0.429, treatment 0.429, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/14 tasks; memory retrieved on 0/14.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| instructlab/instructlab | 31 | 0.548 | 0.581 | +3.23 | 1 | 0 | 1.0 | 24 | 31 |
| keras-team/keras | 28 | 0.321 | 0.321 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pdm-project/pdm | 15 | 0.533 | 0.600 | +6.67 | 1 | 0 | 1.0 | 9 | 15 |
| reflex-dev/reflex | 24 | 0.458 | 0.500 | +4.17 | 1 | 0 | 1.0 | 11 | 14 |
| sissbruecker/linkding | 14 | 0.429 | 0.429 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 17 | 0.353 | 0.471 | +11.76 | 4 | 2 | 0.6875 | 15 | 17 |

Tasks dropped from both arms after a failed call: {"sphinx-doc/sphinx": 2}
