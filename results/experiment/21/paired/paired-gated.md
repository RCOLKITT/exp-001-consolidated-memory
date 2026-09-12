# Paired analysis — arm `gated` vs `control`
**primary: all treatment repos (registered)** — n = 526, control 0.490, treatment 0.489, lift -0.19 pts (paired Wald 95% CI -1.3 to +0.9; bootstrap -1.3 to +0.9). Discordant pairs: treatment-only 4, control-only 5, McNemar exact p = 1.0. Flags differed on 49/526 tasks; memory retrieved on 62/526.
**sissbruecker/linkding** — n = 14, control 0.429, treatment 0.429, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/14 tasks; memory retrieved on 0/14.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 79 | 0.329 | 0.342 | +1.27 | 2 | 1 | 1.0 | 15 | 19 |
| conan-io/conan | 143 | 0.420 | 0.420 | +0.00 | 0 | 0 | 1.0 | 2 | 2 |
| deepset-ai/haystack | 68 | 0.765 | 0.750 | -1.47 | 1 | 2 | 1.0 | 11 | 12 |
| instructlab/instructlab | 31 | 0.516 | 0.516 | +0.00 | 0 | 0 | 1.0 | 1 | 2 |
| keras-team/keras | 28 | 0.321 | 0.321 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| matplotlib/matplotlib | 79 | 0.595 | 0.595 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| pdm-project/pdm | 15 | 0.533 | 0.533 | +0.00 | 0 | 0 | 1.0 | 4 | 5 |
| pylint-dev/pylint | 42 | 0.476 | 0.429 | -4.76 | 0 | 2 | 0.5 | 11 | 16 |
| reflex-dev/reflex | 24 | 0.458 | 0.458 | +0.00 | 0 | 0 | 1.0 | 2 | 2 |
| sissbruecker/linkding | 14 | 0.429 | 0.429 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 17 | 0.529 | 0.588 | +5.88 | 1 | 0 | 1.0 | 3 | 4 |

Tasks dropped from both arms after a failed call: {"conan-io/conan": 1, "sphinx-doc/sphinx": 2}
