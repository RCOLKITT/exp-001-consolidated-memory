# Paired analysis — arm `gated` vs `control`
**primary: all treatment repos (registered)** — n = 211, control 0.531, treatment 0.526, lift -0.47 pts (paired Wald 95% CI -2.1 to +1.1; bootstrap -2.4 to +0.9). Discordant pairs: treatment-only 1, control-only 2, McNemar exact p = 1.0. Flags differed on 13/211 tasks; memory retrieved on 14/211.

| repo | n | control | treatment | lift | trt-only | ctl-only | p | flags differed | retrieved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| conan-io/conan | 143 | 0.420 | 0.420 | +0.00 | 0 | 0 | 1.0 | 2 | 2 |
| deepset-ai/haystack | 68 | 0.765 | 0.750 | -1.47 | 1 | 2 | 1.0 | 11 | 12 |

Tasks dropped from both arms after a failed call: {"conan-io/conan": 1}
