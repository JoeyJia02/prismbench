# Changelog

## Unreleased — validation follow-up

- Add an optional Qwen3-1.7B F16/Q8_0/Q4_K_M likelihood recipe using upstream llama.cpp, a pinned corpus, strict token/window alignment and exploratory paired block intervals.
- Record four accepted PPL lifetimes, an invalid logging pilot and nine rotating deployment lifetimes on the RTX 4070 SUPER. Keep third-party corpus text/token arrays and model assets out of the public evidence.
- Add preparation, parser and failure-lifecycle tests without changing the installed backend or published alpha assets.

- Reproduced the public alpha in a fresh Python 3.14.5 environment on the original machine: three new 2K runs with complete evidence and explicit cached-asset/OS-dependency boundaries.
- Added an opt-in Windows supervisor and 41 hardware-free tests, including native Job memory-limit and sentinel isolation checks. One real CUDA allocation rejection recovered via explicit 2K fallback under an 8 GiB host Job cap; physical VRAM exhaustion remains unproven.
- Documented the missing Microsoft Visual C++ x64 runtime prerequisite. The published alpha wheel and original benchmark records are unchanged.


## 0.1.0a1 — experimental alpha

- Installable CLI with JSON configs, offline synthetic demo and one real llama.cpp backend.
- Exact token workloads, independent model lifetimes, first-text latency with event timestamps, engine timings and explicitly scoped memory samples.
- Owned process cleanup, finite timeouts, positive-evidence OOM classification and a recorded explicit fallback sequence.
- Versioned result schema, JSON/CSV/Markdown evidence, conservative matched-workload comparisons and single-line smoke probes.
- Windows/Linux fixture CI, clean installed-wheel demo/report checks, optional real-model integration, sample configs and contributor documentation.
- Complete published RTX 4070 SUPER evidence, pinned Windows reproduction guide, and hardware reproduction issue template.

Distribution is through GitHub Releases, not PyPI. Publication checks are in [the publication audit](docs/reviews/publication-audit.md). GPU measurements cover one Windows RTX 4070 SUPER and one Qwen3 GGUF; general quantization quality loss, deliberate hardware OOM recovery, other capacities and other backends remain unvalidated.
