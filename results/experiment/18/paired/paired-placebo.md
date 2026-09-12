# Paired analysis — arm `placebo` vs `control`
**primary: all treatment repos (registered)** — n = 211, control 0.531, treatment 0.531, lift +0.00 pts (paired Wald 95% CI -2.3 to +2.3; bootstrap -2.4 to +2.4). Discordant pairs: treatment-only 3, control-only 3, McNemar exact p = 1.0. Flags differed on 46/211 tasks; memory retrieved on 71/211.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| conan-io/conan | 143 | 0.420 | 0.420 | +0.00 | 0 | 0 | 1.0 | 2 | 3 |
| deepset-ai/haystack | 68 | 0.765 | 0.765 | +0.00 | 3 | 3 | 1.0 | 44 | 68 |

Tasks dropped from both arms after a failed call: {"conan-io/conan": 1}
