# Paired analysis — arm `treatment` vs `placebo`
**primary: all treatment repos (registered)** — n = 526, control 0.483, treatment 0.477, lift -0.57 pts (paired Wald 95% CI -2.4 to +1.3; bootstrap -2.5 to +1.3). Discordant pairs: treatment-only 11, control-only 14, McNemar exact p = 0.69. Flags differed on 178/526 tasks; memory retrieved on 240/526.
**sissbruecker/linkding** — n = 14, control 0.429, treatment 0.429, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/14 tasks; memory retrieved on 0/14.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 79 | 0.304 | 0.279 | -2.53 | 1 | 3 | 0.625 | 49 | 61 |
| conan-io/conan | 143 | 0.420 | 0.420 | +0.00 | 0 | 0 | 1.0 | 2 | 3 |
| deepset-ai/haystack | 68 | 0.765 | 0.735 | -2.94 | 2 | 4 | 0.6875 | 44 | 68 |
| instructlab/instructlab | 31 | 0.548 | 0.581 | +3.23 | 1 | 0 | 1.0 | 24 | 31 |
| keras-team/keras | 28 | 0.321 | 0.321 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| matplotlib/matplotlib | 79 | 0.608 | 0.608 | +0.00 | 1 | 1 | 1.0 | 3 | 4 |
| pdm-project/pdm | 15 | 0.533 | 0.600 | +6.67 | 1 | 0 | 1.0 | 9 | 15 |
| pylint-dev/pylint | 42 | 0.452 | 0.357 | -9.52 | 0 | 4 | 0.125 | 21 | 27 |
| reflex-dev/reflex | 24 | 0.458 | 0.500 | +4.17 | 1 | 0 | 1.0 | 11 | 14 |
| sissbruecker/linkding | 14 | 0.429 | 0.429 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 17 | 0.353 | 0.471 | +11.76 | 4 | 2 | 0.6875 | 15 | 17 |

Tasks dropped from both arms after a failed call: {"conan-io/conan": 1, "sphinx-doc/sphinx": 2}
