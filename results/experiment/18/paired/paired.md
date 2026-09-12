# Paired analysis — arm `treatment` vs `control`
**primary: all treatment repos (registered)** — n = 211, control 0.531, treatment 0.521, lift -0.95 pts (paired Wald 95% CI -3.6 to +1.7; bootstrap -3.8 to +1.4). Discordant pairs: treatment-only 3, control-only 5, McNemar exact p = 0.7266. Flags differed on 50/211 tasks; memory retrieved on 71/211.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| conan-io/conan | 143 | 0.420 | 0.420 | +0.00 | 0 | 0 | 1.0 | 3 | 3 |
| deepset-ai/haystack | 68 | 0.765 | 0.735 | -2.94 | 3 | 5 | 0.7266 | 47 | 68 |

Tasks dropped from both arms after a failed call: {"conan-io/conan": 1}
