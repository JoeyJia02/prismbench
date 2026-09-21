# Changelog

## 0.1.0a1 — experimental alpha

- Installable CLI with JSON configs, offline synthetic demo and one real llama.cpp backend.
- Exact token workloads, independent model lifetimes, first-text latency with event timestamps, engine timings and explicitly scoped memory samples.
- Owned process cleanup, finite timeouts, positive-evidence OOM classification and a recorded explicit fallback sequence.
- Versioned result schema, JSON/CSV/Markdown evidence, conservative matched-workload comparisons and single-line smoke probes.
- Windows/Linux fixture CI, clean installed-wheel demo/report checks, optional real-model integration, sample configs and contributor documentation.
- Complete published RTX 4070 SUPER evidence, pinned Windows reproduction guide, and hardware reproduction issue template.

Distribution is through GitHub Releases, not PyPI. Publication checks are in [the publication audit](docs/reviews/publication-audit.md). GPU measurements cover one Windows RTX 4070 SUPER and one Qwen3 GGUF; general quantization quality loss, deliberate hardware OOM recovery, other capacities and other backends remain unvalidated.
