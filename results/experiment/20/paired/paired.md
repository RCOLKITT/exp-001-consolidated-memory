# Paired analysis — arm `treatment` vs `control`
**primary: all treatment repos (registered)** — n = 115, control 0.461, treatment 0.487, lift +2.61 pts (paired Wald 95% CI -1.9 to +7.1; bootstrap -1.7 to +7.0). Discordant pairs: treatment-only 5, control-only 2, McNemar exact p = 0.4531. Flags differed on 54/115 tasks; memory retrieved on 77/115.
**sissbruecker/linkding** — n = 14, control 0.429, treatment 0.429, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/14 tasks; memory retrieved on 0/14.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| instructlab/instructlab | 31 | 0.516 | 0.581 | +6.45 | 2 | 0 | 0.5 | 19 | 31 |
| keras-team/keras | 28 | 0.321 | 0.321 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pdm-project/pdm | 15 | 0.533 | 0.600 | +6.67 | 1 | 0 | 1.0 | 11 | 15 |
| reflex-dev/reflex | 24 | 0.458 | 0.500 | +4.17 | 1 | 0 | 1.0 | 11 | 14 |
| sissbruecker/linkding | 14 | 0.429 | 0.429 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 17 | 0.529 | 0.471 | -5.88 | 1 | 2 | 1.0 | 13 | 17 |

Tasks dropped from both arms after a failed call: {"sphinx-doc/sphinx": 2}
