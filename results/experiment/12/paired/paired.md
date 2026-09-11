# Paired analysis — arm `treatment` vs `control`
**primary: all treatment repos (registered)** — n = 62, control 0.435, treatment 0.468, lift +3.23 pts (paired Wald 95% CI -1.2 to +7.6; bootstrap +0.0 to +8.1). Discordant pairs: treatment-only 2, control-only 0, McNemar exact p = 0.5. Flags differed on 18/62 tasks; memory retrieved on 30/62.
**sissbruecker/linkding** — n = 0, control 0.000, treatment 0.000, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/0 tasks; memory retrieved on 0/0.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| instructlab/instructlab | 30 | 0.533 | 0.600 | +6.67 | 2 | 0 | 0.5 | 18 | 30 |
| keras-team/keras | 27 | 0.296 | 0.296 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pdm-project/pdm | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| reflex-dev/reflex | 5 | 0.600 | 0.600 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sissbruecker/linkding | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 0 | 0.000 | 0.000 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |

Tasks dropped from both arms after a failed call: {"instructlab/instructlab": 1, "keras-team/keras": 1, "pdm-project/pdm": 15, "reflex-dev/reflex": 19, "sissbruecker/linkding": 14, "sphinx-doc/sphinx": 19}
