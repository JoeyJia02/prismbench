# Contributing

Trying the package is a contribution. Use the [short first-run guide](docs/first-run.md)
and [first-run feedback form](https://github.com/JoeyJia02/prismbench/issues/new?template=first_run.md)
for installation success, failure or confusing steps. No GPU, full evidence bundle
or pull request is required. Read [sharing results](docs/sharing-results.md) before
attaching files. The [first-user plan](docs/community-launch.md) tracks what external
feedback would establish; maintainer reruns and download counts do not prove adoption.

Start with an issue describing a reproducible user problem. Check [alternatives](docs/competitive-landscape.md) and [scope](docs/adr/0001-v01.md) before adding a backend or dependency. Small, reviewable changes are preferred.

Install Python 3.10+ and create a virtual environment. Then:

```console
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
python -m build
```

Tests use deterministic fixtures and owned child processes; the default suite never downloads a model or runs a real GPU workload. Real integration is explicitly enabled using `PRISMBENCH_SERVER` and `PRISMBENCH_MODEL` (see `tests/test_gpu.py`). On Windows set them with `$env:PRISMBENCH_SERVER=...`; on Linux use `export`. Keep model/runtime hashes, driver version and background workload notes with shared results.

Every metric must state its unit, timing boundary and scope. `null` means not measured/unknown. Keep failures and fallback attempts, preserve requested and effective configuration, and never present fixtures as real performance. Add meaningful tests for changed failure paths or numerical semantics. A backend change needs raw protocol fixtures and an opt-in real integration test; a new backend needs an independent review before release.

Do not commit models, runtime binaries, downloaded datasets, credentials or unrelated local experiments. Our tiny bundled probe texts are original project data under the MIT license. Record the license and immutable source revision of any external dataset introduced later.

Pull requests should describe the concrete problem, changed behavior, validation and limitations. Never claim CI/GPU results which were not run. Contributors retain authorship; contributions are provided under the repository's MIT license.
