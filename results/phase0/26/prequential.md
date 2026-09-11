# Prequential recurrence (warm-up 20, chains >= 21, Python-source gold only)

seenK = share of eval tasks with a gold key already gold >= K times earlier in the chain.

| repo | chain | eval | file seen2 | class seen2 | function seen2 | function seen1 | function seen3 | scorable |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| conan-io/conan | 165 | 145 | 0.476 | 0.317 | 0.241 | 0.579 | 0.11 | 145 |
| aws-cloudformation/cfn-lint | 109 | 89 | 0.449 | 0.404 | 0.36 | 0.607 | 0.225 | 79 |
| matplotlib/matplotlib | 101 | 81 | 0.556 | 0.407 | 0.148 | 0.42 | 0.086 | 79 |
| deepset-ai/haystack | 88 | 68 | 0.515 | 0.5 | 0.426 | 0.691 | 0.206 | 68 |
| pylint-dev/pylint | 62 | 42 | 0.429 | 0.381 | 0.143 | 0.524 | 0.024 | 42 |
| instructlab/instructlab | 52 | 32 | 0.781 | 0.719 | 0.719 | 0.875 | 0.656 | 31 |
| keras-team/keras | 48 | 28 | 0.179 | 0.179 | 0.071 | 0.25 | 0.036 | 28 |
| reflex-dev/reflex | 44 | 24 | 0.792 | 0.583 | 0.417 | 0.583 | 0.292 | 24 |
| streamlink/streamlink | 41 | 21 | 0.048 | 0.0 | 0.0 | 0.095 | 0.0 | 21 |
| sphinx-doc/sphinx | 39 | 19 | 0.474 | 0.316 | 0.263 | 0.632 | 0.105 | 19 |
| pdm-project/pdm | 35 | 15 | 0.733 | 0.733 | 0.6 | 0.733 | 0.267 | 15 |
| sissbruecker/linkding | 34 | 14 | 0.786 | 0.714 | 0.714 | 0.857 | 0.5 | 14 |
| pvlib/pvlib-python | 30 | 10 | 0.5 | 0.1 | 0.1 | 0.4 | 0.0 | 10 |
| pydata/xarray | 29 | 9 | 0.333 | 0.222 | 0.111 | 0.333 | 0.0 | 8 |
| beeware/briefcase | 28 | 8 | 0.375 | 0.25 | 0.125 | 0.875 | 0.0 | 8 |
| kedro-org/kedro | 28 | 8 | 0.5 | 0.25 | 0.25 | 0.75 | 0.125 | 8 |
| bridgecrewio/checkov | 25 | 5 | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 4 |
| jlowin/fastmcp | 25 | 5 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 5 |
| koxudaxi/datamodel-code-generator | 24 | 4 | 0.5 | 0.5 | 0.25 | 0.5 | 0.0 | 3 |
| Kozea/WeasyPrint | 22 | 2 | 0.5 | 0.5 | 0.5 | 1.0 | 0.5 | 2 |
| geopandas/geopandas | 22 | 2 | 0.5 | 0.5 | 0.0 | 0.0 | 0.0 | 2 |
| joke2k/faker | 21 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1 |
| patroni/patroni | 21 | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 |
| stanfordnlp/dspy | 21 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1 |

| level | repos | eval pool | scorable | seen1 | seen2 | seen3 |
|---|---:|---:|---:|---:|---:|---:|
| file | 24 | 634 | 618 | 0.722 | 0.487 | 0.325 |
| class | 24 | 634 | 618 | 0.642 | 0.39 | 0.248 |
| function | 24 | 634 | 618 | 0.558 | 0.287 | 0.164 |
