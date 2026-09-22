# Backlog and acceptance criteria

## v0.1

| ID | Work | Acceptance | Status |
|---|---|---|---|
| P0-01 | Competition and scope | Primary source comparison; independent ADR review | Done |
| P0-02 | Installable CLI/config | Strict validation; offline demo; installed-wheel command | Done |
| P0-03 | llama.cpp runner | Exact workload, streaming TTFT, explicit placement, provenance | Done |
| P0-04 | Hardware and failures | Sampled metrics with scope; timeout, OOM ledger, owned cleanup | Done; bounded CUDA failure/fallback observed, ordinary VRAM pressure remains unvalidated |
| P0-05 | Evidence/report | Schema-valid JSON, CSV, readable Markdown; no synthetic ranking | Done |
| P0-06 | Lightweight quality | Versioned probes; explicit limitations; comparable paired delta | Done; optional F16/Q8/Q4 corpus-prediction pilot measured separately |
| P0-07 | Tests and integration | Unit tests during development; fake server; opt-in real GPU | CPU fixtures, native owned-process tests and installed-wheel CI; six-job CI required for each merge |
| P0-08 | Real benchmark | New package results, hashes and artifacts; repeated tested points | Original 21 attempts plus separate 3-run reproduction and guarded OOM/fallback chain; one GPU/model |
| P0-09 | OSS maintenance | README, contribution guide, CI, roadmap, license, release checklist | Public repository, five issues, pinned onboarding and alpha release assets |
| P0-10 | Final independent audit | Functionality, claims, tests, installation, methodology, scope | Alpha publication PASS; stable support gates remain open |

## Public issues

| Priority | Work and acceptance criteria | Issue |
|---|---|---|
| High | Independent GPU/Linux reproductions with hashes, three lifetimes, failures and raw evidence | [#1](https://github.com/JoeyJia02/prismbench/issues/1) |
| High | Real hardware OOM, owned cleanup, bounded fallback and post-stop memory observations | [#2](https://github.com/JoeyJia02/prismbench/issues/2) |
| Delivered pilot | Licensed pinned corpus and same-model high-precision quantization reference | [#3](https://github.com/JoeyJia02/prismbench/issues/3), [measured F16/Q8/Q4 study](validation-quantization-20260922.md) |
| Medium | First-time wheel installation and onboarding on external machines | [#4](https://github.com/JoeyJia02/prismbench/issues/4) |
| Medium | Measured llama.cpp runtime compatibility matrix | [#5](https://github.com/JoeyJia02/prismbench/issues/5) |

The [2026-09-22 evidence](validation-20260922.md) partially addresses #2 and #4. It does not close them: the CUDA experiment used a host-memory cap, no memory-settling gate precedes the CLI retry, and installation was repeated on the maintainer's existing OS and GPU.

The separate [quantization pilot](validation-quantization-20260922.md) adds four accepted likelihood lifetimes and nine deployment lifetimes on one smaller model, retaining an invalid logging pilot. It completes the scoped reference study in #3; general task accuracy, other languages/models and a larger representative corpus remain untested.

## First external users

The [first-user plan](community-launch.md) and [English/Chinese launch drafts](launch-posts.md)
are ready for maintainer review. Start with the [short first-run guide](first-run.md)
and optional [first-run feedback](https://github.com/JoeyJia02/prismbench/issues/new?template=first_run.md);
full hardware evidence is a later step. [Sharing guidance](sharing-results.md)
explains local paths, identifiers, reconstructible token IDs and redaction limits.

Track real outcomes in existing issues #4 (installation) and #1 (hardware), not a
second reporting system. Initial targets after an invitation is actually posted:
three independent installations, two external real reports and one user returning
for their own comparison. These are goals, not observed adoption. The drafts have
not been posted to external communities, and maintainer reruns do not close either
issue. No new backend, telemetry service, website or release version is needed
for this first-user pilot.

## After v0.1 (not promised)

1. Obtain independent 8/16/24 GB and Linux GPU reproductions; record runtime compatibility matrix.
2. Extend the completed paired-perplexity prefix pilot to more representative text and task-level checks; preserve source identity and uncertainty limits.
3. Support consuming llama-autotune profiles and llama-bench cross-checks instead of duplicating search.
4. Add transformers only when a concrete user workload needs it; vLLM/MLX follow measured demand.
5. Memory recovery admission gates before retry; distinguish the completed guarded CUDA-allocation experiment from ordinary VRAM-pressure validation.
6. PyPI publication after fresh name/packaging checks and external installation feedback. No PyPI name is reserved by the GitHub alpha release.

No distributed scheduling, multi-GPU orchestration, website or accounts in this roadmap.
