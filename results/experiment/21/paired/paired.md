# Paired analysis — arm `treatment` vs `control`
**primary: all treatment repos (registered)** — n = 526, control 0.490, treatment 0.477, lift -1.33 pts (paired Wald 95% CI -3.3 to +0.6; bootstrap -3.2 to +0.6). Discordant pairs: treatment-only 10, control-only 17, McNemar exact p = 0.2478. Flags differed on 181/526 tasks; memory retrieved on 240/526.
**sissbruecker/linkding** — n = 14, control 0.429, treatment 0.429, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/14 tasks; memory retrieved on 0/14.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 79 | 0.329 | 0.279 | -5.06 | 1 | 5 | 0.2188 | 53 | 61 |
| conan-io/conan | 143 | 0.420 | 0.420 | +0.00 | 0 | 0 | 1.0 | 3 | 3 |
| deepset-ai/haystack | 68 | 0.765 | 0.735 | -2.94 | 3 | 5 | 0.7266 | 47 | 68 |
| instructlab/instructlab | 31 | 0.516 | 0.581 | +6.45 | 2 | 0 | 0.5 | 19 | 31 |
| keras-team/keras | 28 | 0.321 | 0.321 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| matplotlib/matplotlib | 79 | 0.595 | 0.608 | +1.27 | 1 | 0 | 1.0 | 2 | 4 |
| pdm-project/pdm | 15 | 0.533 | 0.600 | +6.67 | 1 | 0 | 1.0 | 11 | 15 |
| pylint-dev/pylint | 42 | 0.476 | 0.357 | -11.90 | 0 | 5 | 0.0625 | 22 | 27 |
| reflex-dev/reflex | 24 | 0.458 | 0.500 | +4.17 | 1 | 0 | 1.0 | 11 | 14 |
| sissbruecker/linkding | 14 | 0.429 | 0.429 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 17 | 0.529 | 0.471 | -5.88 | 1 | 2 | 1.0 | 13 | 17 |

Tasks dropped from both arms after a failed call: {"conan-io/conan": 1, "sphinx-doc/sphinx": 2}
