# Backlog and acceptance criteria

## v0.1

| ID | Work | Acceptance | Status |
|---|---|---|---|
| P0-01 | Competition and scope | Primary source comparison; independent ADR review | Done |
| P0-02 | Installable CLI/config | Strict validation; offline demo; installed-wheel command | Done |
| P0-03 | llama.cpp runner | Exact workload, streaming TTFT, explicit placement, provenance | Done |
| P0-04 | Hardware and failures | Sampled metrics with scope; timeout, OOM ledger, owned cleanup | Done; hardware OOM not induced |
| P0-05 | Evidence/report | Schema-valid JSON, CSV, readable Markdown; no synthetic ranking | Done |
| P0-06 | Lightweight quality | Versioned probes; explicit limitations; comparable paired delta | Done; quantization-loss study deferred |
| P0-07 | Tests and integration | Unit tests during development; fake server; opt-in real GPU | Done: local 151 tests and all six remote CI jobs pass |
| P0-08 | Real benchmark | New package results, hashes and artifacts; repeated tested points | Done: 21 final attempts, one GPU/model |
| P0-09 | OSS maintenance | README, contribution guide, CI, roadmap, license, release checklist | Public repository, five issues, pinned onboarding and alpha release assets |
| P0-10 | Final independent audit | Functionality, claims, tests, installation, methodology, scope | Alpha publication PASS; stable support gates remain open |

## Public issues

| Priority | Work and acceptance criteria | Issue |
|---|---|---|
| High | Independent GPU/Linux reproductions with hashes, three lifetimes, failures and raw evidence | [#1](https://github.com/JoeyJia02/prismbench/issues/1) |
| High | Real hardware OOM, owned cleanup, bounded fallback and post-stop memory observations | [#2](https://github.com/JoeyJia02/prismbench/issues/2) |
| High | Licensed pinned corpus and same-model high-precision quantization reference | [#3](https://github.com/JoeyJia02/prismbench/issues/3) |
| Medium | First-time wheel installation and onboarding on external machines | [#4](https://github.com/JoeyJia02/prismbench/issues/4) |
| Medium | Measured llama.cpp runtime compatibility matrix | [#5](https://github.com/JoeyJia02/prismbench/issues/5) |

## After v0.1 (not promised)

1. Obtain independent 8/16/24 GB and Linux GPU reproductions; record runtime compatibility matrix.
2. Pinned perplexity corpus paired against higher-precision model; confidence intervals and tokenizer identity.
3. Support consuming llama-autotune profiles and llama-bench cross-checks instead of duplicating search.
4. Add transformers only when a concrete user workload needs it; vLLM/MLX follow measured demand.
5. Recovery admission gates for memory pressure; hardware OOM experiments in an isolated environment.
6. PyPI publication after fresh name/packaging checks and external installation feedback. No PyPI name is reserved by the GitHub alpha release.

No distributed scheduling, multi-GPU orchestration, website or accounts in this roadmap.
