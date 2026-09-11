# Paired analysis
**primary: all treatment repos (registered)** — n = 371, control 0.644, treatment 0.655, lift +1.08 pts (paired Wald 95% CI -2.0 to +4.2; bootstrap -1.9 to +4.3). Discordant pairs: treatment-only 19, control-only 15, McNemar exact p = 0.6076. Flags differed on 283/371 tasks; memory retrieved on 371/371.
**secondary: repos that passed Gate 3** — n = 220, control 0.677, treatment 0.673, lift -0.45 pts (paired Wald 95% CI -3.7 to +2.8; bootstrap -3.6 to +2.7). Discordant pairs: treatment-only 6, control-only 7, McNemar exact p = 1.0. Flags differed on 162/220 tasks; memory retrieved on 220/220.
**sissbruecker/linkding** — n = 14, control 0.714, treatment 0.714, lift +0.00 pts (paired Wald 95% CI +0.0 to +0.0; bootstrap +0.0 to +0.0). Discordant pairs: treatment-only 0, control-only 0, McNemar exact p = 1.0. Flags differed on 0/14 tasks; memory retrieved on 0/14.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 58 | 0.362 | 0.328 | -3.45 | 2 | 4 | 0.6875 | 49 | 58 |
| conan-io/conan | 114 | 0.561 | 0.597 | +3.51 | 11 | 7 | 0.4807 | 91 | 114 |
| deepset-ai/haystack | 38 | 0.974 | 0.974 | +0.00 | 0 | 0 | 1.0 | 25 | 38 |
| instructlab/instructlab | 22 | 0.682 | 0.682 | +0.00 | 0 | 0 | 1.0 | 14 | 22 |
| keras-team/keras | 18 | 0.667 | 0.722 | +5.56 | 1 | 0 | 1.0 | 16 | 18 |
| matplotlib/matplotlib | 51 | 0.843 | 0.843 | +0.00 | 0 | 0 | 1.0 | 34 | 51 |
| pdm-project/pdm | 15 | 0.600 | 0.533 | -6.67 | 1 | 2 | 1.0 | 11 | 15 |
| pylint-dev/pylint | 22 | 0.636 | 0.773 | +13.64 | 3 | 0 | 0.25 | 19 | 22 |
| reflex-dev/reflex | 14 | 0.714 | 0.643 | -7.14 | 0 | 1 | 1.0 | 10 | 14 |
| sissbruecker/linkding | 14 | 0.714 | 0.714 | +0.00 | 0 | 0 | 1.0 | 0 | 0 |
| sphinx-doc/sphinx | 19 | 0.737 | 0.737 | +0.00 | 1 | 1 | 1.0 | 14 | 19 |

Tasks dropped from both arms after a failed call: {"aws-cloudformation/cfn-lint": 1}
