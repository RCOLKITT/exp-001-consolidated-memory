# Gold-location recurrence along chains

eval_file_seen3 = share of eval tasks whose gold file was a gold file >= 3 times in the build prefix (what file-level memory could at best recall).

| repo | prefix | eval n | files >=3 | dirs >=3 | eval: file seen>=1 | file seen>=3 | dir seen>=1 | dir seen>=3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| conan-io/conan | 20 | 145 | 0 | 3 | 0.248 | 0.0 | 0.621 | 0.366 |
| conan-io/conan | 30 | 135 | 1 | 6 | 0.333 | 0.03 | 0.674 | 0.467 |
| conan-io/conan | 40 | 125 | 3 | 7 | 0.416 | 0.048 | 0.712 | 0.496 |
| conan-io/conan | 50 | 115 | 7 | 12 | 0.461 | 0.061 | 0.739 | 0.6 |
| conan-io/conan | 60 | 105 | 10 | 14 | 0.486 | 0.114 | 0.743 | 0.61 |
| conan-io/conan | 80 | 85 | 14 | 16 | 0.541 | 0.141 | 0.729 | 0.588 |
| conan-io/conan | 165 | 0 | 42 | 25 | None | None | None | None |
| aws-cloudformation/cfn-lint | 20 | 89 | 2 | 3 | 0.517 | 0.169 | 0.708 | 0.404 |
| aws-cloudformation/cfn-lint | 30 | 79 | 3 | 4 | 0.557 | 0.215 | 0.797 | 0.392 |
| aws-cloudformation/cfn-lint | 40 | 69 | 4 | 6 | 0.594 | 0.217 | 0.884 | 0.464 |
| aws-cloudformation/cfn-lint | 50 | 59 | 7 | 7 | 0.593 | 0.271 | 0.881 | 0.458 |
| aws-cloudformation/cfn-lint | 60 | 49 | 14 | 12 | 0.592 | 0.388 | 0.898 | 0.673 |
| aws-cloudformation/cfn-lint | 80 | 29 | 16 | 13 | 0.759 | 0.31 | 0.931 | 0.655 |
| aws-cloudformation/cfn-lint | 109 | 0 | 30 | 26 | None | None | None | None |
| matplotlib/matplotlib | 20 | 81 | 2 | 5 | 0.469 | 0.185 | 0.938 | 0.852 |
| matplotlib/matplotlib | 30 | 71 | 4 | 5 | 0.606 | 0.296 | 0.958 | 0.873 |
| matplotlib/matplotlib | 40 | 61 | 4 | 6 | 0.623 | 0.311 | 0.984 | 0.934 |
| matplotlib/matplotlib | 50 | 51 | 9 | 7 | 0.765 | 0.49 | 0.98 | 0.961 |
| matplotlib/matplotlib | 60 | 41 | 13 | 7 | 0.756 | 0.537 | 0.976 | 0.951 |
| matplotlib/matplotlib | 80 | 21 | 17 | 9 | 0.905 | 0.429 | 1.0 | 0.952 |
| matplotlib/matplotlib | 101 | 0 | 24 | 10 | None | None | None | None |
| deepset-ai/haystack | 20 | 68 | 1 | 4 | 0.338 | 0.059 | 1.0 | 0.971 |
| deepset-ai/haystack | 30 | 58 | 3 | 6 | 0.517 | 0.069 | 1.0 | 0.983 |
| deepset-ai/haystack | 40 | 48 | 7 | 8 | 0.562 | 0.25 | 1.0 | 0.979 |
| deepset-ai/haystack | 50 | 38 | 9 | 10 | 0.553 | 0.237 | 1.0 | 1.0 |
| deepset-ai/haystack | 60 | 28 | 11 | 12 | 0.75 | 0.357 | 1.0 | 1.0 |
| deepset-ai/haystack | 80 | 8 | 17 | 16 | 0.875 | 0.375 | 1.0 | 1.0 |
| deepset-ai/haystack | 88 | 0 | 19 | 16 | None | None | None | None |
| pylint-dev/pylint | 20 | 42 | 2 | 4 | 0.619 | 0.286 | 1.0 | 0.976 |
| pylint-dev/pylint | 30 | 32 | 8 | 9 | 0.562 | 0.438 | 1.0 | 1.0 |
| pylint-dev/pylint | 40 | 22 | 9 | 9 | 0.455 | 0.318 | 1.0 | 1.0 |
| pylint-dev/pylint | 50 | 12 | 10 | 12 | 0.5 | 0.333 | 1.0 | 1.0 |
| pylint-dev/pylint | 60 | 2 | 10 | 13 | 0.5 | 0.0 | 1.0 | 1.0 |
| pylint-dev/pylint | 62 | 0 | 10 | 13 | None | None | None | None |
| pylint-dev/pylint | 62 | 0 | 10 | 13 | None | None | None | None |
| instructlab/instructlab | 20 | 32 | 6 | 6 | 0.781 | 0.625 | 0.906 | 0.906 |
| instructlab/instructlab | 30 | 22 | 10 | 6 | 0.682 | 0.682 | 0.864 | 0.864 |
| instructlab/instructlab | 40 | 12 | 14 | 7 | 0.667 | 0.5 | 0.833 | 0.833 |
| instructlab/instructlab | 50 | 2 | 18 | 12 | 0.5 | 0.0 | 0.5 | 0.5 |
| instructlab/instructlab | 52 | 0 | 18 | 12 | None | None | None | None |
| instructlab/instructlab | 52 | 0 | 18 | 12 | None | None | None | None |
| instructlab/instructlab | 52 | 0 | 18 | 12 | None | None | None | None |
| keras-team/keras | 20 | 28 | 0 | 3 | 0.357 | 0.0 | 0.643 | 0.286 |
| keras-team/keras | 30 | 18 | 0 | 4 | 0.5 | 0.0 | 0.778 | 0.333 |
| keras-team/keras | 40 | 8 | 2 | 8 | 0.75 | 0.125 | 1.0 | 0.375 |
| keras-team/keras | 48 | 0 | 6 | 16 | None | None | None | None |
| keras-team/keras | 48 | 0 | 6 | 16 | None | None | None | None |
| keras-team/keras | 48 | 0 | 6 | 16 | None | None | None | None |
| keras-team/keras | 48 | 0 | 6 | 16 | None | None | None | None |
| reflex-dev/reflex | 20 | 24 | 5 | 5 | 0.833 | 0.542 | 0.917 | 0.875 |
| reflex-dev/reflex | 30 | 14 | 7 | 5 | 0.857 | 0.643 | 0.929 | 0.857 |
| reflex-dev/reflex | 40 | 4 | 8 | 7 | 1.0 | 0.75 | 1.0 | 1.0 |
| reflex-dev/reflex | 44 | 0 | 10 | 8 | None | None | None | None |
| reflex-dev/reflex | 44 | 0 | 10 | 8 | None | None | None | None |
| reflex-dev/reflex | 44 | 0 | 10 | 8 | None | None | None | None |
| reflex-dev/reflex | 44 | 0 | 10 | 8 | None | None | None | None |
| streamlink/streamlink | 20 | 21 | 0 | 1 | 0.238 | 0.0 | 0.905 | 0.667 |
| streamlink/streamlink | 30 | 11 | 0 | 3 | 0.273 | 0.0 | 1.0 | 0.909 |
| streamlink/streamlink | 40 | 1 | 1 | 3 | 1.0 | 0.0 | 1.0 | 1.0 |
| streamlink/streamlink | 41 | 0 | 1 | 3 | None | None | None | None |
| streamlink/streamlink | 41 | 0 | 1 | 3 | None | None | None | None |
| streamlink/streamlink | 41 | 0 | 1 | 3 | None | None | None | None |
| streamlink/streamlink | 41 | 0 | 1 | 3 | None | None | None | None |
| sphinx-doc/sphinx | 20 | 19 | 3 | 4 | 0.947 | 0.947 | 1.0 | 1.0 |
| sphinx-doc/sphinx | 30 | 9 | 8 | 8 | 1.0 | 1.0 | 1.0 | 1.0 |
| sphinx-doc/sphinx | 39 | 0 | 9 | 9 | None | None | None | None |
| sphinx-doc/sphinx | 39 | 0 | 9 | 9 | None | None | None | None |
| sphinx-doc/sphinx | 39 | 0 | 9 | 9 | None | None | None | None |
| sphinx-doc/sphinx | 39 | 0 | 9 | 9 | None | None | None | None |
| sphinx-doc/sphinx | 39 | 0 | 9 | 9 | None | None | None | None |
| pdm-project/pdm | 20 | 15 | 5 | 9 | 0.867 | 0.533 | 1.0 | 1.0 |
| pdm-project/pdm | 30 | 5 | 7 | 9 | 1.0 | 0.6 | 1.0 | 1.0 |
| pdm-project/pdm | 35 | 0 | 11 | 10 | None | None | None | None |
| pdm-project/pdm | 35 | 0 | 11 | 10 | None | None | None | None |
| pdm-project/pdm | 35 | 0 | 11 | 10 | None | None | None | None |
| pdm-project/pdm | 35 | 0 | 11 | 10 | None | None | None | None |
| pdm-project/pdm | 35 | 0 | 11 | 10 | None | None | None | None |
| sissbruecker/linkding | 20 | 14 | 9 | 10 | 0.929 | 0.429 | 0.929 | 0.857 |
| sissbruecker/linkding | 30 | 4 | 13 | 11 | 1.0 | 0.75 | 1.0 | 1.0 |
| sissbruecker/linkding | 34 | 0 | 14 | 11 | None | None | None | None |
| sissbruecker/linkding | 34 | 0 | 14 | 11 | None | None | None | None |
| sissbruecker/linkding | 34 | 0 | 14 | 11 | None | None | None | None |
| sissbruecker/linkding | 34 | 0 | 14 | 11 | None | None | None | None |
| sissbruecker/linkding | 34 | 0 | 14 | 11 | None | None | None | None |
| pvlib/pvlib-python | 20 | 10 | 8 | 4 | 0.7 | 0.4 | 1.0 | 1.0 |
| pvlib/pvlib-python | 30 | 0 | 13 | 5 | None | None | None | None |
| pvlib/pvlib-python | 30 | 0 | 13 | 5 | None | None | None | None |
| pvlib/pvlib-python | 30 | 0 | 13 | 5 | None | None | None | None |
| pvlib/pvlib-python | 30 | 0 | 13 | 5 | None | None | None | None |
| pvlib/pvlib-python | 30 | 0 | 13 | 5 | None | None | None | None |
| pvlib/pvlib-python | 30 | 0 | 13 | 5 | None | None | None | None |

## Ceiling on lift (pts) = seenK x (1 - p0)

| build N | eval pool | promote at >= 2 | promote at >= 3 |
|---:|---:|---:|---:|
| 20 | 588 | 10.5 | 7.3 |
| 30 | 440 | 12.5 | 8.0 |
| 40 | 337 | 14.2 | 8.0 |
| 50 | 275 | 17.3 | 9.5 |
| 60 | 223 | 17.4 | 12.6 |
| 80 | 135 | 19.7 | 11.0 |
