# Paired analysis — arm `placebo` vs `control`
**primary: all treatment repos (registered)** — n = 526, control 0.490, treatment 0.483, lift -0.76 pts (paired Wald 95% CI -2.4 to +0.9; bootstrap -2.5 to +0.9). Discordant pairs: treatment-only 8, control-only 12, McNemar exact p = 0.5034. Flags differed on 152/526 tasks; memory retrieved on 240/526.
**sissbruecker/linkding** — n = 14, control 0.429, treatment 0.429, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/14 tasks; memory retrieved on 0/14.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 79 | 0.329 | 0.304 | -2.53 | 2 | 4 | 0.6875 | 44 | 61 |
| conan-io/conan | 143 | 0.420 | 0.420 | +0.00 | 0 | 0 | 1.0 | 2 | 3 |
| deepset-ai/haystack | 68 | 0.765 | 0.765 | +0.00 | 3 | 3 | 1.0 | 44 | 68 |
| instructlab/instructlab | 31 | 0.516 | 0.548 | +3.23 | 2 | 1 | 1.0 | 17 | 31 |
| keras-team/keras | 28 | 0.321 | 0.321 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| matplotlib/matplotlib | 79 | 0.595 | 0.608 | +1.27 | 1 | 0 | 1.0 | 2 | 4 |
| pdm-project/pdm | 15 | 0.533 | 0.533 | +0.00 | 0 | 0 | 1.0 | 6 | 15 |
| pylint-dev/pylint | 42 | 0.476 | 0.452 | -2.38 | 0 | 1 | 1.0 | 16 | 27 |
| reflex-dev/reflex | 24 | 0.458 | 0.458 | +0.00 | 0 | 0 | 1.0 | 7 | 14 |
| sissbruecker/linkding | 14 | 0.429 | 0.429 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 17 | 0.529 | 0.353 | -17.65 | 0 | 3 | 0.25 | 14 | 17 |

Tasks dropped from both arms after a failed call: {"conan-io/conan": 1, "sphinx-doc/sphinx": 2}
